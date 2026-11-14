import asyncio
import logging
import discord
from discord.ext import commands

####  Config
from pi_yo_6.dictionary_view import DictionaryView
from pi_yo_6.embeds import EmBase
from pi_yo_6.load_config import GuildConfig, UserConfig
from pi_yo_6.message_unit import MessageUnit
from pi_yo_6.synthetic_voice import SyntheticEngines
from pi_yo_6.utils import VoiceUnit
from pi_yo_6.voice import ChatReader
from pi_yo_6.voice_client import MultiAudioVoiceClient
from pi_yo_6.voice_list import VoiceListContainer

_log = logging.getLogger(__name__)


####  起動準備 And 初期設定


class MyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.g_opts: dict[int, 'DataInfo'] = {}

    @discord.app_commands.command(name="auto_join", description="自動接続 要権限")
    @discord.app_commands.guild_only()
    @discord.app_commands.default_permissions(administrator=True)
    async def auto_join(self, ctx: discord.Interaction, action: bool) -> None:
        if not ctx.guild:
            return
        gc = GuildConfig.get(ctx.guild.id)
        gc.data.auto_join = action
        gc.write()
        embed = discord.Embed(
            title=f'auto_join を {action} に変更しました', colour=EmBase.main_color()
        )
        await ctx.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="announce", description="VC入退室アナウンスの切り替え 要権限")
    @discord.app_commands.guild_only()
    @discord.app_commands.default_permissions(administrator=True)
    async def announce(self, ctx: discord.Interaction, action: bool) -> None:
        if not ctx.guild:
            return
        gc = GuildConfig.get(ctx.guild.id)
        gc.data.announce_join_leave = action
        gc.write()
        embed = discord.Embed(
            title=f'VC入退室アナウンスを {action} に変更しました', colour=EmBase.main_color()
        )
        await ctx.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="overlap", description="複数人同時読み上げの切り替え 要権限")
    @discord.app_commands.guild_only()
    @discord.app_commands.default_permissions(administrator=True)
    @discord.app_commands.describe(action="有効にするかどうか", max_tracks="最大同時読み上げ数 (2~3)")
    async def overlap(
        self, ctx: discord.Interaction, action: bool, max_tracks: int = 3
    ) -> None:
        if not ctx.guild:
            return
        gc = GuildConfig.get(ctx.guild.id)
        gc.data.overlap_mode = action
        gc.data.max_tracks = max(2, min(3, max_tracks))
        gc.write()
        if info := self.g_opts.get(ctx.guild.id):
            info.voice._sync_track_pool()
        desc = f"最大同時読み上げ数: {gc.data.max_tracks}" if action else "順次読み上げモードに戻しました"
        embed = discord.Embed(
            title=f'複数人同時読み上げを {"有効" if action else "無効"} に変更しました',
            description=desc,
            colour=EmBase.main_color(),
        )
        await ctx.response.send_message(embed=embed, ephemeral=True)

    ####  基本的コマンド
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        _log.info('Logged in')
        _log.info(self.bot.user.name if self.bot.user else "error")
        _log.info(self.bot.user.id if self.bot.user else -1)
        _log.info('--------------------------')

        activity = discord.Activity(name='華麗なる美声', type=discord.ActivityType.listening)
        asyncio.create_task(self.bot.change_presence(activity=activity))
        asyncio.create_task(self.bot.tree.sync())

    @commands.command()
    async def join(self, ctx: commands.Context) -> None:
        if not ctx.guild or self.g_opts.get(ctx.guild.id):
            return
        try:
            if (
                isinstance(ctx.author, discord.Member)
                and ctx.author.voice
                and ctx.author.voice.channel
            ):
                await ctx.author.voice.channel.connect(self_deaf=True)
                _log.info(f'{ctx.guild.name} : #join')
                self.g_opts[ctx.guild.id] = DataInfo(
                    ctx.guild, self, initial_channel_id=ctx.channel.id
                )
        except Exception:
            _log.exception(f"func:join  guild:{ctx.guild.name}")

    @commands.command()
    async def bye(self, ctx: commands.Context) -> None:
        if ctx.guild and (info := self.g_opts.get(ctx.guild.id)):
            await info.bye()

    # ---------------------------------

    @commands.command()
    async def register(self, ctx: commands.Context, arg1: str, arg2: str) -> None:
        if not ctx.guild:
            return
        gc = GuildConfig.get(ctx.guild.id)
        gc.data.dic.put(arg1, arg2)
        gc.write()
        _log.info(f'{ctx.guild.name} : #register : "{arg1}" -> "{arg2}"')
        embed = discord.Embed(
            title='辞書登録完了',
            description=f'`{arg1}` → `{arg2}`',
            colour=EmBase.main_color(),
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def delete(self, ctx: commands.Context, arg1: str) -> None:
        if not ctx.guild:
            return
        gc = GuildConfig.get(ctx.guild.id)
        if gc.data.dic.get(arg1):
            gc.data.dic.remove(arg1)
            gc.write()
            _log.info(f'{ctx.guild.name} : #delete : "{arg1}" を削除')
            embed = discord.Embed(
                title='辞書削除完了',
                description=f'`{arg1}` を削除しました',
                colour=EmBase.main_color(),
            )
            await ctx.send(embed=embed)

    @commands.command(aliases=['dictionary', 'dics'])
    async def dic(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            return
        gc = GuildConfig.get(ctx.guild.id)
        view = DictionaryView(guild_id=ctx.guild.id, dic=gc.data.dic)
        embed = view.create_embed(ctx.guild.name)
        await ctx.send(embed=embed, view=view)

    @commands.command(aliases=['s'])
    async def shutup(self, ctx: commands.Context) -> None:
        if ctx.guild and ctx.guild.voice_client and (data := self.g_opts.get(ctx.guild.id)):
            data.voice.stop_all()

    @commands.command(aliases=['vl'])
    async def voice_list(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            return
        await SyntheticEngines.current.reload_unloaded_engines()
        uc = UserConfig.get(ctx.author.id)
        view = discord.ui.LayoutView(timeout=None)
        view.add_item(VoiceListContainer(g_opts=self.g_opts, voice=uc.data.voice))
        await ctx.send(view=view)

    @commands.command(aliases=['reload_engine', 'reload_engines'])
    async def reload(self, ctx: commands.Context) -> None:
        """後から起動したVOICEVOX / Coeiroinkエンジンの再接続を試行"""
        msg = await ctx.send("音声エンジンを再探索中...")
        reloaded = await SyntheticEngines.current.reload_unloaded_engines()
        if reloaded:
            await msg.edit(content=f"新しいエンジンを読み込みました: {', '.join(reloaded)}")
        else:
            await msg.edit(content="追加で接続された音声エンジンはありませんでした。")

    @commands.command(aliases=['ch'])
    async def channel(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            return
        info = self.g_opts.get(ctx.guild.id)
        if not info:
            await ctx.send("Botがボイスチャンネルに接続していません。")
            return
        ch_id = ctx.channel.id
        if ch_id in info.target_channels:
            info.target_channels.remove(ch_id)
            await ctx.send(f"このチャンネル（{ctx.channel.mention}）を読み上げ対象から解除しました。")
        else:
            info.target_channels.add(ch_id)
            await ctx.send(f"このチャンネル（{ctx.channel.mention}）を読み上げ対象に追加しました！")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        info = self.g_opts.get(member.guild.id)
        if not info:
            return

        # Bot自身の強制切断検知
        if self.bot.user and member.id == self.bot.user.id:
            if after.channel is None:
                await info.bye('強制切断')
            return

        # VC入退室アナウンス
        gc = GuildConfig.get(member.guild.id)
        if gc.data.announce_join_leave and info.vc.channel and not member.bot:
            vc_channel = info.vc.channel
            announce_text: str | None = None
            if before.channel != vc_channel and after.channel == vc_channel:
                announce_text = f"{member.display_name}さんが入室しました"
            elif before.channel == vc_channel and after.channel != vc_channel:
                announce_text = f"{member.display_name}さんが退室しました"

            if announce_text:
                uc = UserConfig.get(member.id)
                voice = (
                    uc.data.voice.model_copy()
                    if SyntheticEngines.current.is_available(uc.data.voice)
                    else info.voice.random_voice()
                )
                msg_unit = MessageUnit(announce_text)
                msg_unit.voice = voice
                await msg_unit.normalize_text(guild=member.guild)
                await info.voice.play_message(msg_unit)

        # ボイスチャンネルにBot以外のメンバーがいなくなったか確認
        vc_channel = info.vc.channel
        if vc_channel and before.channel == vc_channel and after.channel != vc_channel:
            if not any(not m.bot for m in vc_channel.members):
                await asyncio.sleep(5.0)
                # 5秒後もまだ誰もいなければ切断
                if member.guild.id in self.g_opts and info.vc.channel:
                    if not any(not m.bot for m in info.vc.channel.members):
                        await info.bye('誰もいなくなったため 切断')

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        if not msg.guild or not msg.author:
            return
        if isinstance(msg.channel, (discord.DMChannel, discord.PartialMessageable)):
            return
        if isinstance(msg.author, discord.User):
            return

        # 読み上げ
        # 発言者がBotの場合はPass
        if msg.author.bot:
            return

        _log.info(f'#message.server  : {msg.guild.name} ({msg.channel.name})')
        _log.info(f'{msg.author.name} ({msg.author.display_name}) : {msg.content}')

        if msg.guild.id not in self.g_opts:
            gc = GuildConfig.get(msg.guild.id)
            if (
                gc.data.auto_join
                and msg.author.voice
                and msg.author.voice.channel
                and not msg.guild.voice_client
                and (msg.author.voice.mute or msg.author.voice.self_mute)
            ):
                await self.join(await self.bot.get_context(msg))

        if info := self.g_opts.get(msg.guild.id):
            if not info.target_channels or msg.channel.id in info.target_channels:
                await info.voice.on_message(msg)


class DataInfo:
    def __init__(
        self, guild: discord.Guild, cog: MyCog, initial_channel_id: int | None = None
    ) -> None:
        self.guild = guild
        self.cog = cog
        self._closing = False
        self.target_channels: set[int] = set()
        if initial_channel_id:
            self.target_channels.add(initial_channel_id)

        if isinstance(guild.voice_client, discord.VoiceClient):
            self.vc: discord.VoiceClient = guild.voice_client
            if self.vc.channel:
                self.target_channels.add(self.vc.channel.id)
        else:
            _log.error("vcがVoiceClientじゃない")
            asyncio.create_task(self.bye())
            return

        self.MA = MultiAudioVoiceClient(guild, self)
        self.voice = ChatReader(self)

    async def bye(self, text: str = '切断') -> None:
        if self._closing:
            return
        self._closing = True
        asyncio.create_task(self._bye(text))

    async def _bye(self, text: str) -> None:
        if hasattr(self, 'voice'):
            self.voice.close()
        if hasattr(self, 'MA'):
            self.MA.kill()
        self.cog.g_opts.pop(self.guild.id, None)

        _log.info(f'{self.guild.name} : #{text}')
        await asyncio.sleep(0.02)
        try:
            if hasattr(self, 'vc') and self.vc.is_connected():
                await self.vc.disconnect()
        except Exception:
            pass
