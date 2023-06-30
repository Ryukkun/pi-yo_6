import discord
import os
import re
import shutil
import asyncio
import logging
import random
from pathlib import Path
from discord.ext import commands, tasks
from typing import Literal, Optional, Dict

_my_dir = Path(__file__).parent
os.chdir(str(_my_dir))

####  Config
config_path = str(_my_dir / 'config.py')
temp_config_path = str(_my_dir / 'pi_yo_6' / 'template' / '_config.py')
try:
    from config import Config
except Exception:
    shutil.copyfile(temp_config_path, config_path)
    from config import Config

from . import voice_list as VoiceList
from .load_config import GC, dif_config
from .voice_client import MultiAudio
from .voice import ChatReader
from .embeds import EmBase
from .synthetic_voice import SyntheticEngines
from .utils import set_logger

set_logger()
_log = logging.getLogger(__name__)

#dif_config(config_path, temp_config_path)
try:shutil.rmtree(Config.output)
except Exception:pass
os.makedirs(Config.user_dic, exist_ok=True)
os.makedirs(Config.guild_config, exist_ok=True)
os.makedirs(Config.user_config, exist_ok=True)
os.makedirs(Config.OJ.hts_path, exist_ok=True)
os.makedirs(Config.output, exist_ok=True)
with open(Config.admin_dic,'a'):pass



####  起動準備 And 初期設定
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
client = commands.Bot(command_prefix=Config.prefix,intents=intents)
g_opts:Dict[int, 'DataInfo'] = {}

engines:SyntheticEngines = SyntheticEngines()




async def not_perm(ctx:discord.Interaction, com_name, com_bool, GConfig):
    if not ctx.permissions.administrator and GConfig['admin_only'].setdefault(com_name,com_bool):
        await ctx.response.send_message(embed=EmBase.no_perm(), ephemeral= True)
        return GConfig


tree = client.tree
group = discord.app_commands.Group(name="pi-yo6",description="ぴーよ6号設定")

@group.command(description="自動接続 要権限")
@discord.app_commands.describe(action='初期 : False')
async def auto_join(ctx: discord.Interaction, action: Literal['True','False']):
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



@group.command(description="特定のコマンドを管理者しか使えないようにするか否か 要権限")
@discord.app_commands.describe(action='初期 : True')
async def admin_only(ctx: discord.Interaction, command:Literal['auto_join','my_voice','server_voice','another_voice'], action: Literal['True','False']):
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



tree.add_command(group)




####  基本的コマンド
@client.event
async def on_ready():
    _log.info('Logged in')
    _log.info(client.user.name)
    _log.info(client.user.id)
    _log.info('----------------')
    await tree.sync()
    activity = discord.Activity(name='華麗なる美声', type=discord.ActivityType.listening)
    await client.change_presence(activity=activity)
    


@client.command()
async def join(ctx:commands.Context):
    if vc := ctx.author.voice:
        gid = ctx.guild.id
        _log.info(f'{ctx.guild.name} : #join')
        try: await vc.channel.connect(self_deaf=True)
        except discord.ClientException: return
        g_opts[gid] = DataInfo(ctx.guild)
        Dic_Path = f'{Config.user_dic}{gid}.txt'
        with open(Dic_Path,'w'): pass
        GC(gid)
        return True


@client.command()
async def bye(ctx:commands.Context):
    if info := g_opts.get(ctx.guild.id):
        await info.bye()



#---------------------------------


@client.command()
async def register(ctx:commands.Context, arg1, arg2):
    gid = str(ctx.guild.id)
    with open(Config.user_dic+ gid +'.txt', mode='a') as f:
        f.write(arg1 + ',' + arg2 + '\n')
        _log.info(f'{ctx.guild.name} : #register >> {gid}.txt "{arg1} -> {arg2}"')


@client.command()
async def delete(ctx:commands.Context, arg1):
    gid = str(ctx.guild.id)
    with open(Config.user_dic+ gid +'.txt', mode='r') as f:
        text = f.read()
        replaced_text = re.sub(rf'{arg1},[^\n]+\n','',text)
    if re.search(rf'{arg1},[^\n]+\n',text):
        with open(Config.user_dic+ gid +'.txt', mode='w') as f:
            f.write(replaced_text)
        _log.info(f'{ctx.guild.name} : #delete >> {gid}.txtから "{arg1}" を削除')


@client.command(aliases=['s'])
async def shutup(ctx:commands.Context):
    if ctx.guild.voice_client:
        gid = ctx.guild.id
        g_opts[gid].Voice.Vvc.stop()
        await g_opts[gid].Voice.play_loop()



@client.command(aliases=['vl'])
async def voice_list(ctx:commands.Context):
    await ctx.send(embed=await VoiceList.embed(ctx.guild), view=VoiceList.CreateView(g_opts=g_opts, engines=engines))



@client.command()
async def count(ctx:commands.Context):
    if not ctx.voice_client:
        await join(ctx)
    
    if data := g_opts.get(ctx.guild.id):
        choice = []
        if engines.open_jtalk:
            for _ in engines.open_jtalk.metas:
                if _['name'] == 'mei':
                    for __ in _['styles']:
                        if __['name'] == 'mei_normal':
                            choice.append('mei_normal')
                            break
            if 'mei_normal' not in choice:
                choice.append( random.choice( random.choice(engines.open_jtalk.metas)['styles'] )['id'] )

        if engines.voicevox:
            voices:list[str] = ['ずんだもん','四国めたん','春日部つむぎ','白上虎太郎','冥鳴ひまり','ちび式じい','小夜/SAYO','ナースロボ_タイプT']
            voices = [_.lower() for _ in voices]
            for _ in engines.voicevox.metas:
                if _['name'].lower() in voices:
                    choice.append(f"voicevox:{_['name']}_{_['styles'][0]['name']}")

        if not choice:
            return
        
        message = f"voice:{random.choice(choice)} いっくよー 3 2 1 GO!"
        #await data.Voice.on_message_from_str(message)
        await data.Voice.count(random.choice(choice))



@client.event
async def on_message(message:discord.Message):
    guild = message.guild
    if not guild: return
    gid = message.guild.id
    voice = message.author.voice

    # 読み上げ
    # 発言者がBotの場合はPass
    if message.author.bot:
        return
    print('')
    _log.info(f'#message.server  : {guild.name} ({message.channel.name})')
    _log.info(f'{message.author.name} ({message.author.display_name}) : {message.content}')

    _GC = GC(gid).Read()
    if voice and _GC['auto_join']:
        if voice.channel and not guild.voice_client:
            if voice.mute or voice.self_mute:
                await join(message)

    try: await g_opts[gid].Voice.on_message(message)
    except KeyError:pass

    # Fin
    await client.process_commands(message)





class DataInfo:
    def __init__(self, guild:discord.Guild):
        self.guild = guild
        self.gn = guild.name
        self.gid = guild.id
        self.vc = guild.voice_client
        self.loop = client.loop
        self.client = client
        self.engines = engines
        self.MA = MultiAudio(guild, client, self)
        self.Voice = ChatReader(self)
        self.count_loop = 0
        self.loop_5.start()


    async def bye(self, text:str='切断'):
        self.loop.create_task(self._bye(text))


    async def _bye(self, text:str):
        self.loop_5.stop()
        self.MA.kill()
        del g_opts[self.gid]
        
        _log.info(f'{self.gn} : #{text}')
        await asyncio.sleep(0.02)
        try: await self.vc.disconnect()
        except Exception: pass




    @tasks.loop(seconds=5.0)
    async def loop_5(self):
        mems = self.vc.channel.members
        # 強制切断検知
        if not client.user.id in [_.id for _ in mems]:
            self.count_loop += 1
            if 2 <= self.count_loop:
                await self.bye('強制切断')

        # voice channelに誰もいなくなったことを確認
        elif not False in [_.bot for _ in mems]:
            self.count_loop += 1
            if 2 <= self.count_loop:
                await self.bye('誰もいなくなったため 切断')

        # Reset Count
        else:
            self.count_loop = 0


client.run(Config.token, log_level=logging.WARNING)