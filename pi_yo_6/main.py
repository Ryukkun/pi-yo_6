import discord
import os
import re
import asyncio
import logging
import random
from pathlib import Path
from discord.ext import commands, tasks
from typing import Literal, Optional, Dict

_my_dir = Path(__file__).parent.parent
os.chdir(str(_my_dir))

####  Config
from .utils import set_logger, check_config
check_config()
from config import Config


from . import voice_list as VoiceList
from .load_config import GC
from .voice_client import MultiAudioVoiceClient
from .voice import ChatReader
from .embeds import EmBase
from .synthetic_voice import SyntheticEngines


set_logger()
_log = logging.getLogger(__name__)

#dif_config(config_path, temp_config_path)




####  起動準備 And 初期設定





async def not_perm(ctx:discord.Interaction, com_name, com_bool, GConfig):
    if not ctx.permissions.administrator and GConfig['admin_only'].setdefault(com_name,com_bool):
        await ctx.response.send_message(embed=EmBase.no_perm(), ephemeral= True)
        return GConfig



class MyCog(commands.Cog):
    def __init__(self, bot:commands.Bot, engines:SyntheticEngines) -> None:
        self.bot = bot
        self.engines = engines
        self.g_opts:dict[int, 'DataInfo'] = {}


    @discord.app_commands.command(name="auto_join", description="自動接続 要権限")
    async def auto_join(self, ctx:discord.Interaction, action:Literal['True','False']):
        gid = ctx.guild_id
        _GC = GC(gid)
        GConfig = _GC.Read()

        if _ := await not_perm(ctx, 'auto_join', True, GConfig):
            _GC.Write(_)
            return
        if action == 'True':
            GConfig['auto_join'] = True
        else:
            GConfig['auto_join'] = False

        _GC.Write(GConfig)
        embed = discord.Embed(title=f'auto_join を {action} に変更しました', colour=EmBase.main_color())
        await ctx.response.send_message(embed=embed, ephemeral= True)



    @discord.app_commands.command(name="admin_only", description="特定のコマンドを管理者しか使えないようにするか否か 要権限")
    async def admin_only(self, ctx:discord.Interaction, command:Literal['auto_join','my_voice','server_voice','another_voice'], action: Literal['True','False']):
        gid = ctx.guild_id
        _GC = GC(gid)
        GConfig = _GC.Read()

        if not ctx.permissions.administrator:
            await ctx.response.send_message(embed=EmBase.no_perm(), ephemeral= True)
            return
        if action == 'True':
            GConfig['admin_only'][command] = True
        else:
            GConfig['admin_only'][command] = False

        _GC.Write(GConfig)
        embed = discord.Embed(title='権限状況', colour=EmBase.main_color())
        for k, v in GConfig['admin_only'].items():
            embed.add_field(name=k,value=str(v),inline=True)
        await ctx.response.send_message(embed=embed, ephemeral= True)



    ####  基本的コマンド
    @commands.Cog.listener()
    async def on_ready(self):
        _log.info('Logged in')
        _log.info(self.bot.user.name if self.bot.user else "error")
        _log.info(self.bot.user.id if self.bot.user else -1)
        print('--------------------------')

        activity = discord.Activity(name='華麗なる美声', type=discord.ActivityType.listening)
        await self.bot.change_presence(activity=activity)
    


    @commands.command()
    async def join(self, ctx:commands.Context):
        if ctx.guild and not self.g_opts.get(ctx.guild.id):
            try: 
                if isinstance(ctx.author, discord.Member) and ctx.author.voice and ctx.author.voice.channel:
                    await ctx.author.voice.channel.connect(self_deaf=True)
                    _log.info(f'{ctx.guild.name} : #join')
                    self.g_opts[ctx.guild.id] = DataInfo(ctx.guild, self)
                    dicPath = f'{Config.user_dic}{ctx.guild.id}.txt'
                    with open(dicPath,'w'): pass
                    GC(ctx.guild.id)
                    return True
            except:
                _log.exception(f"func:join  guild:{ctx.guild.name}")
            return True


    @commands.command()
    async def bye(self, ctx:commands.Context):
        if ctx.guild and (info := self.g_opts.get(ctx.guild.id)):
            await info.bye()



#---------------------------------


    @commands.command()
    async def register(self, ctx:commands.Context, arg1, arg2):
        if not ctx.guild: return
        gid = str(ctx.guild.id)
        with open(Config.user_dic+ gid +'.txt', mode='a') as f:
            f.write(arg1 + ',' + arg2 + '\n')
            _log.info(f'{ctx.guild.name} : #register >> {gid}.txt "{arg1} -> {arg2}"')


    @commands.command()
    async def delete(self, ctx:commands.Context, arg1):
        if not ctx.guild: return
        gid = str(ctx.guild.id)
        with open(Config.user_dic+ gid +'.txt', mode='r') as f:
            text = f.read()
            replaced_text = re.sub(rf'{arg1},[^\n]+\n','',text)
        if re.search(rf'{arg1},[^\n]+\n',text):
            with open(Config.user_dic+ gid +'.txt', mode='w') as f:
                f.write(replaced_text)
            _log.info(f'{ctx.guild.name} : #delete >> {gid}.txtから "{arg1}" を削除')


    @commands.command(aliases=['s'])
    async def shutup(self, ctx:commands.Context):
        if ctx.guild and ctx.guild.voice_client and (data := self.g_opts.get(ctx.guild.id)):
            await data.voice.play_loop()



    @commands.command(aliases=['vl'])
    async def voice_list(self, ctx:commands.Context):
        if not ctx.guild: return
        await ctx.send(embed=await VoiceList.embed(ctx.guild), view=VoiceList.CreateView(g_opts=self.g_opts, engines=self.engines))



    @commands.command()
    async def count(self, ctx:commands.Context):
        if not ctx.guild: return

        if not ctx.voice_client:
            await self.join(ctx)
        if data := self.g_opts.get(ctx.guild.id):
            choice = []
            if self.engines.open_jtalk:
                for _ in self.engines.open_jtalk.metas:
                    if _['name'] == 'mei':
                        for __ in _['styles']:
                            if __['name'] == 'mei_normal':
                                choice.append('mei_normal')
                                break
                if 'mei_normal' not in choice:
                    choice.append( random.choice( random.choice(self.engines.open_jtalk.metas)['styles'] )['id'] )

            if self.engines.voicevox:
                voices:list[str] = ['ずんだもん','四国めたん','春日部つむぎ','白上虎太郎','冥鳴ひまり','ちび式じい','小夜/SAYO','ナースロボ_タイプT']
                voices = [_.lower() for _ in voices]
                for _ in self.engines.voicevox.metas:
                    if _['name'].lower() in voices:
                        choice.append(f"voicevox:{_['name']}_{_['styles'][0]['name']}")

            if not choice:
                return
            
            message = f"voice:{random.choice(choice)} いっくよー 3 2 1 GO!"
            #await data.Voice.on_message_from_str(message)
            await data.voice.count(random.choice(choice))



    @commands.Cog.listener()
    async def on_message(self, msg:discord.Message):
        if not msg.guild or not msg.author: return
        if isinstance(msg.channel, (discord.DMChannel, discord.PartialMessageable)): return
        if isinstance(msg.author, discord.User): return

        # 読み上げ
        # 発言者がBotの場合はPass
        if msg.author.bot:
            return
        print('')

        _log.info(f'#message.server  : {msg.guild.name} ({msg.channel.name})')
        _log.info(f'{msg.author.name} ({msg.author.display_name}) : {msg.content}')

        _GC = GC(msg.guild.id).Read()
        if msg.author.voice and _GC['auto_join']:
            if msg.author.voice.channel and not msg.guild.voice_client:
                if msg.author.voice.mute or msg.author.voice.self_mute:
                    await self.join(await self.bot.get_context(msg))

        try: await self.g_opts[msg.guild.id].voice.on_message(msg)
        except KeyError:pass





class DataInfo:
    def __init__(self, guild:discord.Guild, cog:MyCog):
        if isinstance(guild.voice_client, discord.VoiceClient):
            self.vc:discord.VoiceClient = guild.voice_client
        else:
            _log.error("vcがVoiceClientじゃない")
            asyncio.create_task(self.bye())
        self.guild = guild
        self.cog = cog
        self.MA = MultiAudioVoiceClient(guild, self)
        self.voice = ChatReader(self)
        self.count_loop = 0
        self.loop_5.start()


    async def bye(self, text:str='切断'):
        asyncio.create_task(self._bye(text))
        self.loop_5.stop()
        

    async def _bye(self, text:str):
        self.MA.kill()
        del self.cog.g_opts[self.guild.id]
        
        _log.info(f'{self.guild.name} : #{text}')
        await asyncio.sleep(0.02)
        try: await self.vc.disconnect()
        except Exception: pass




    @tasks.loop(seconds=5.0)
    async def loop_5(self):
        if not self.guild.id in self.cog.g_opts:
            return

        # 強制切断検知
        client_user_id = self.cog.bot.user.id if self.cog.bot.user else -1
        mems = self.vc.channel.members
        if not client_user_id in [_.id for _ in mems]:
            await self.bye('強制切断')

        # voice channelに誰もいなくなったことを確認
        elif not False in [_.bot for _ in mems]:
            self.count_loop += 1
            if 2 <= self.count_loop:
                await self.bye('誰もいなくなったため 切断')

        # Reset Count
        else:
            self.count_loop = 0