import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from pi_yo_6.config import guild_configs, user_configs
from pi_yo_6.session import GuildVoiceSession
from pi_yo_6.tts.manager import TTSManager
from pi_yo_6.ui import (
    DictionaryView,
    VoiceSelectorView,
    make_failed_embed,
    make_info_embed,
)

_log = logging.getLogger(__name__)


class TTSCog(commands.Cog):
    """Discord読み上げボットのコマンドおよびイベントリスナーを統括するCog"""

    def __init__(self, bot: commands.Bot, tts: TTSManager) -> None:
        self.bot = bot
        self.tts = tts
        self.sessions: dict[int, GuildVoiceSession] = {}
        self._empty_vc_tasks: dict[int, asyncio.Task] = {}

    async def cog_unload(self) -> None:
        for task in list(self._empty_vc_tasks.values()):
            if not task.done():
                task.cancel()
        self._empty_vc_tasks.clear()

        if self.sessions:
            await asyncio.gather(
                *(
                    session.close(reason="bot_shutdown", wait=True)
                    for session in list(self.sessions.values())
                ),
                return_exceptions=True,
            )

    def _remove_session(self, guild_id: int) -> None:
        self.sessions.pop(guild_id, None)
        self._cancel_empty_timer(guild_id)

    def _cancel_empty_timer(self, guild_id: int) -> None:
        task = self._empty_vc_tasks.pop(guild_id, None)
        if task and not task.done():
            task.cancel()

    def _schedule_empty_disconnect(self, guild: discord.Guild, delay: float = 5.0) -> None:
        self._cancel_empty_timer(guild.id)

        async def _auto_disconnect() -> None:
            try:
                await asyncio.sleep(delay)
                session = self.sessions.get(guild.id)
                if not session or not session.vc or not session.vc.channel:
                    return
                if not any(not m.bot for m in session.vc.channel.members):
                    _log.info("VCが空になったため自動切断します: %s", guild.name)
                    await session.close(reason="empty_vc")
            except asyncio.CancelledError:
                pass
            finally:
                self._empty_vc_tasks.pop(guild.id, None)

        self._empty_vc_tasks[guild.id] = self.bot.loop.create_task(_auto_disconnect())

    async def _join_vc(
        self,
        channel: discord.VoiceChannel | discord.StageChannel,
        text_channel_id: int | None = None,
    ) -> GuildVoiceSession:
        guild = channel.guild
        existing = self.sessions.get(guild.id)
        if existing:
            if text_channel_id:
                existing.target_channels.add(text_channel_id)
            if existing.vc.channel != channel:
                await existing.vc.move_to(channel)
            return existing

        vc = await channel.connect(self_deaf=True)
        session = GuildVoiceSession(
            guild=guild,
            vc=vc,
            loop=self.bot.loop,
            tts=self.tts,
            initial_channel_id=text_channel_id,
            on_close=self._remove_session,
        )
        self.sessions[guild.id] = session
        return session

    # --- スラッシュコマンド ---

    @app_commands.command(name="auto_join", description="VC入室時の自動接続設定を変更します。")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def auto_join(self, interaction: discord.Interaction, action: bool) -> None:
        if not interaction.guild_id:
            return
        gc = guild_configs.get(interaction.guild_id)
        gc.data.auto_join = action
        gc.write()
        state = "有効" if action else "無効"
        await interaction.response.send_message(
            embed=make_info_embed("自動接続設定を変更しました", f"自動接続: **{state}**")
        )

    @app_commands.command(name="announce", description="VCへの入退室アナウンス設定を変更します。")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def announce(self, interaction: discord.Interaction, action: bool) -> None:
        if not interaction.guild_id:
            return
        gc = guild_configs.get(interaction.guild_id)
        gc.data.announce_join_leave = action
        gc.write()
        state = "有効" if action else "無効"
        await interaction.response.send_message(
            embed=make_info_embed("入退室アナウンス設定を変更しました", f"アナウンス: **{state}**")
        )

    @app_commands.command(name="overlap", description="複数人の同時読み上げ（音声の重ね合わせ）設定を変更します。")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def overlap(
        self,
        interaction: discord.Interaction,
        action: bool,
        max_tracks: app_commands.Range[int, 1, 3] = 3,
    ) -> None:
        if not interaction.guild_id:
            return
        gc = guild_configs.get(interaction.guild_id)
        gc.data.overlap_mode = action
        gc.data.max_tracks = max_tracks
        gc.write()

        session = self.sessions.get(interaction.guild_id)
        if session:
            session.notify_config_changed()

        state = "有効" if action else "無効"
        desc = f"同時読み上げ: **{state}**"
        if action:
            desc += f"\n最大同時トラック数: **{max_tracks}**"
        await interaction.response.send_message(
            embed=make_info_embed("同時読み上げ設定を変更しました", desc)
        )

    # --- プレフィックスコマンド ---

    @commands.command()
    @commands.guild_only()
    async def join(self, ctx: commands.Context) -> None:
        if not isinstance(ctx.author, discord.Member) or not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.reply(embed=make_failed_embed("VCに参加していません", "先にボイスチャンネルへ参加してください。"))
            return

        channel = ctx.author.voice.channel
        try:
            await self._join_vc(channel, text_channel_id=ctx.channel.id)
            await ctx.reply(embed=make_info_embed("接続しました", f"{channel.mention} に接続しました。"))
        except Exception as e:
            _log.exception("VC接続エラー: %s", e)
            await ctx.reply(embed=make_failed_embed("接続に失敗しました", str(e)))

    @commands.command()
    @commands.guild_only()
    async def bye(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            return
        session = self.sessions.get(ctx.guild.id)
        if not session:
            await ctx.reply(embed=make_failed_embed("VCに接続していません"))
            return

        await session.close(reason="bye_command")
        await ctx.reply(embed=make_info_embed("切断しました", "ボイスチャンネルから退出しました。"))

    @commands.command()
    @commands.guild_only()
    async def register(self, ctx: commands.Context, word: str, reading: str) -> None:
        if not ctx.guild:
            return
        gc = guild_configs.get(ctx.guild.id)
        gc.data.dic.put(word, reading)
        gc.write()
        await ctx.reply(embed=make_info_embed("辞書に登録しました", f"`{word}` → `{reading}`"))

    @commands.command()
    @commands.guild_only()
    async def delete(self, ctx: commands.Context, word: str) -> None:
        if not ctx.guild:
            return
        gc = guild_configs.get(ctx.guild.id)
        if gc.data.dic.contains(word):
            gc.data.dic.remove(word)
            gc.write()
            await ctx.reply(embed=make_info_embed("辞書から削除しました", f"`{word}` を削除しました。"))
        else:
            await ctx.reply(embed=make_failed_embed("単語が見つかりません", f"`{word}` は辞書に登録されていません。"))

    @commands.command(aliases=["dictionary", "dics"])
    @commands.guild_only()
    async def dic(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            return
        gc = guild_configs.get(ctx.guild.id)
        view = DictionaryView(ctx.guild.id, gc.data.dic)
        embed = view.create_embed(ctx.guild.name)
        await ctx.reply(embed=embed, view=view)

    @commands.command(aliases=["s"])
    @commands.guild_only()
    async def shutup(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            return
        session = self.sessions.get(ctx.guild.id)
        if not session:
            await ctx.reply(embed=make_failed_embed("VCに接続していません"))
            return
        session.stop_all()
        await ctx.reply(embed=make_info_embed("読み上げを停止しました"))

    @commands.command(aliases=["vl"])
    @commands.guild_only()
    async def voice_list(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            return
        uc = user_configs.get(ctx.author.id)
        view = VoiceSelectorView(self.sessions, self.tts, voice=uc.data.voice)
        await ctx.reply(view=view)

    @commands.command(aliases=["reload_engine", "reload_engines"])
    async def reload(self, ctx: commands.Context) -> None:
        reloaded = await self.tts.reload_unloaded_engines()
        if reloaded:
            await ctx.reply(
                embed=make_info_embed("エンジンを再読み込みしました", f"再読み込み済み: {', '.join(reloaded)}")
            )
        else:
            await ctx.reply(embed=make_info_embed("再読み込み完了", "新しく読み込まれたエンジンはありません。"))

    @commands.command(aliases=["ch"])
    @commands.guild_only()
    async def channel(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            return
        session = self.sessions.get(ctx.guild.id)
        if not session:
            await ctx.reply(embed=make_failed_embed("VCに接続していません"))
            return

        ch_id = ctx.channel.id
        if ch_id in session.target_channels:
            session.target_channels.discard(ch_id)
            await ctx.reply(embed=make_info_embed("対象チャンネルから解除しました", f"{ctx.channel.mention} を読み上げ対象から外しました。"))
        else:
            session.target_channels.add(ch_id)
            await ctx.reply(embed=make_info_embed("対象チャンネルに追加しました", f"{ctx.channel.mention} を読み上げ対象に追加しました。"))

    # --- イベントリスナー ---

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.CommandNotFound):
            return
        _log.error("Command '%s' failed: %s", ctx.command or ctx.message.content, error, exc_info=error)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        try:
            synced = await self.bot.tree.sync()
            _log.info("スラッシュコマンドを同期しました (%d件)", len(synced))
        except Exception as e:
            _log.error("スラッシュコマンド同期エラー: %s", e)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        guild = member.guild
        session = self.sessions.get(guild.id)

        # ボット自身が切断・移動された場合
        if self.bot.user and member.id == self.bot.user.id:
            if before.channel and not after.channel and session:
                await session.close(reason="forced_disconnect")
            return

        if not session or not session.vc or not session.vc.channel:
            return

        bot_channel = session.vc.channel
        if before.channel != bot_channel and after.channel != bot_channel:
            return

        # 有人チェックによる自動切断タイマーの制御
        has_humans = any(not m.bot for m in bot_channel.members)
        if not has_humans:
            self._schedule_empty_disconnect(guild)
        else:
            self._cancel_empty_timer(guild.id)

        # ボット以外の入退室アナウンス
        if member.bot:
            return

        gc = guild_configs.get(guild.id)
        if not gc.data.announce_join_leave:
            return

        if before.channel != bot_channel and after.channel == bot_channel:
            text = f"{member.display_name}さんが入室しました"
        elif before.channel == bot_channel and after.channel != bot_channel:
            text = f"{member.display_name}さんが退室しました"
        else:
            return

        voice = session.resolve_user_voice(member.id)
        await session.enqueue_speech(text, voice, guild=guild)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        if msg.author.bot or not msg.guild:
            return

        guild = msg.guild
        session = self.sessions.get(guild.id)

        # 自動接続判定
        if not session and isinstance(msg.author, discord.Member) and msg.author.voice and msg.author.voice.channel:
            gc = guild_configs.get(guild.id)
            vs = msg.author.voice
            if gc.data.auto_join and (vs.self_mute or vs.mute):
                try:
                    session = await self._join_vc(vs.channel, text_channel_id=msg.channel.id)
                except Exception as e:
                    _log.warning("自動VC接続に失敗しました: %s", e)
                    return

        if not session:
            return

        if not session.target_channels or msg.channel.id in session.target_channels:
            await session.enqueue_message(msg)
