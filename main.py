import discord
import os
import re
import shutil
import asyncio
import tabulate
import glob
from discord.ext import commands, tasks
from typing import Literal, Optional

_my_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(_my_dir)

####  Config
try: from config import Config
except Exception:
    shutil.copyfile('pi_yo_6/template/_config.py', 'config.py')
    from config import Config

from pi_yo_6.load_config import GC, UC
from pi_yo_6.voice_client import MultiAudio
from pi_yo_6.voice import ChatReader
from pi_yo_6.voicevox.core import CreateVOICEVOX
from pi_yo_6.embeds import EmBase
import pi_yo_6.voice_list as VoiceList

try:shutil.rmtree(Config.OJ.Output)
except Exception:pass
os.makedirs(Config.User_dic, exist_ok=True)
os.makedirs(Config.Guild_Config, exist_ok=True)
os.makedirs(Config.User_Config, exist_ok=True)
os.makedirs(Config.OJ.Voice, exist_ok=True)
os.makedirs(Config.OJ.Output, exist_ok=True)
with open(Config.Admin_dic,'a'):pass



####  起動準備 And 初期設定
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
client = commands.Bot(command_prefix=Config.Prefix,intents=intents)
g_opts:dict[int, 'DataInfo'] = {}

try:
    VVox:Optional[CreateVOICEVOX] = CreateVOICEVOX(Config, use_gpu=Config.VVOX.use_gpu)
except Exception as e:
    print(f'\033[31m Error \033[35mpi-yo6 \033[0mVoiceVoxの読み込みに失敗しました。\n{e}')
    VVox = None



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



@group.command(description="自分のボイス設定")
@discord.app_commands.describe(voice='ボイス設定　・　未入力 >> 初期設定　・　例 >> "ずんだもん_ささやき"、"25"、"四国"')
@discord.app_commands.choices(only=[discord.app_commands.Choice(name='このサーバーにだけ反映',value='True'),discord.app_commands.Choice(name='他のサーバーでも反映',value='False')])
async def my_voice(ctx: discord.Interaction, only:str, voice:str='-1'):
    gid = ctx.guild_id
    _voice = VVox.to_speaker_id(voice)
    _GC = GC(gid)
    GConfig = _GC.Read()

    if _ := await not_perm(ctx, 'my_voice', False, GConfig):
        _GC.Write(_)
        return

    if type(_voice) != int: 
        await ctx.response.send_message(embed=EmBase.failed(), ephemeral= True)
        return

    else:
        uid = ctx.user.id
        if only == 'True':
            GConfig['voice'][str(uid)] = _voice
            _GC.Write(GConfig)

        else:
            UConfig = UC.Read(uid)
            UConfig['voice'] = _voice
            UC.Write(uid, UConfig)

        if _voice == -1: _voice = 'N/A'
        embed = discord.Embed(title=f'反映完了', colour=EmBase.main_color())
        embed.add_field(name='Speaker_Id',value=str(_voice))
        embed.add_field(name='このサーバーにだけ反映',value=str(only))
        await ctx.response.send_message(embed=embed, ephemeral= True)



@group.command(description="他人のボイス設定 要権限")
@discord.app_commands.describe(voice='ボイス設定　・　未入力 >> 初期設定　・　例 >> "ずんだもん_ささやき"、"25"、"四国"')
async def another_voice(ctx: discord.Interaction,user:discord.User, voice:str='-1'):
    gid = ctx.guild_id
    _voice = VVox.to_speaker_id(voice)
    _GC = GC(gid)
    GConfig = _GC.Read()

    if _ := await not_perm(ctx, 'another_voice', True, GConfig):
        _GC.Write(_)
        return

    if type(_voice) != int: 
        await ctx.response.send_message(embed=EmBase.failed(), ephemeral= True)
        return
        
    else:
        GConfig['voice'][str(user.id)] = _voice
        _GC.Write(GConfig)

        if _voice == -1: _voice = 'N/A'
        embed = discord.Embed(title=f'反映完了({user.name})', colour=EmBase.main_color())
        embed.add_field(name='Speaker_Id',value=str(_voice))
    await ctx.response.send_message(embed=embed, ephemeral= True)



@group.command(description="サーバーの初期設定ボイス 要権限")
@discord.app_commands.describe(voice='ボイス設定　・　未入力 >> 初期設定　・　例 >> "ずんだもん_ささやき"、"25"、"四国"')
async def server_voice(ctx: discord.Interaction, voice:str='-1'):
    gid = ctx.guild_id
    _voice = VVox.to_speaker_id(voice)
    _GC = GC(gid)
    GConfig = _GC.Read()

    if _ := await not_perm(ctx, 'server_voice', True, GConfig):
        _GC.Write(_)
        return

    if type(_voice) != int: 
        await ctx.response.send_message(embed=EmBase.failed(), ephemeral= True)
        return

    else:
        GConfig['server_voice'] = _voice
        _GC.Write(GConfig)

        if _voice == -1: _voice = 'N/A'
        embed = discord.Embed(title=f'反映完了', colour=EmBase.main_color())
        embed.add_field(name='Speaker_Id',value=str(_voice))
    await ctx.response.send_message(embed=embed, ephemeral= True)

tree.add_command(group)




####  基本的コマンド
@client.event
async def on_ready():
    print('Logged in')
    print(client.user.name)
    print(client.user.id)
    print('----------------')
    await tree.sync()
    activity = discord.Activity(name='華麗なる美声', type=discord.ActivityType.listening)
    await client.change_presence(activity=activity)
    


@client.command()
async def join(ctx:commands.Context):
    if vc := ctx.author.voice:
        gid = ctx.guild.id
        print(f'{ctx.guild.name} : #join')
        try: await vc.channel.connect(self_deaf=True)
        except discord.ClientException: return
        g_opts[gid] = DataInfo(ctx.guild)
        Dic_Path = f'{Config.User_dic}{gid}.txt'
        with open(Dic_Path,'w'): pass
        GC(gid)
        return True


@client.command()
async def bye(ctx:commands.Context):
    guild = ctx.guild
    vc = guild.voice_client
    if vc:
        print(f'{guild.name} : #切断')
        await _bye(guild)


async def _bye(guild:discord.Guild):
    gid = guild.id
    vc = guild.voice_client

    g_opts[gid].loop_5.stop()
    g_opts[gid].MA.kill()
    del g_opts[gid]
    
    await asyncio.sleep(0.1)
    try: await vc.disconnect()
    except Exception: pass



#---------------------------------


@client.command()
async def register(ctx:commands.Context, arg1, arg2):
    gid = str(ctx.guild.id)
    with open(Config.User_dic+ gid +'.txt', mode='a') as f:
        f.write(arg1 + ',' + arg2 + '\n')
        print(gid +'.txtに書き込み : '+ arg1 + ',' + arg2)


@client.command()
async def delete(ctx:commands.Context, arg1):
    gid = str(ctx.guild.id)
    with open(Config.User_dic+ gid +'.txt', mode='r') as f:
        text = f.read()
        replaced_text = re.sub(rf'{arg1},[^\n]+\n','',text)
    if re.search(rf'{arg1},[^\n]+\n',text):
        with open(Config.User_dic+ gid +'.txt', mode='w') as f:
            f.write(replaced_text)
        print(f'{gid}.txtから削除 : {arg1}')


@client.command(aliases=['s'])
async def shutup(ctx:commands.Context):
    if ctx.guild.voice_client:
        gid = ctx.guild.id
        g_opts[gid].Voice.Vvc.stop()
        await g_opts[gid].Voice.play_loop()


@client.command(aliases=['sp'])
async def speaker(ctx:commands.Context, *args):
    if args:
        sp_list = VVox.name_list()
        hts_list = [os.path.split(_)[1].replace('.htsvoice','') for _ in glob.glob(f'{Config.OJ.Voice}*.htsvoice')]
        hts_dic = {}
        for hts in hts_list:
            _hts = hts.split('_')
            hts_name = _hts[0]
            if not hts_dic.get(hts_name): hts_dic[hts_name] = [hts_name]
            hts_dic[hts_name].append(hts)

        [sp_list.append(_) for _ in list(hts_dic.values())]
        
        sp_list = tabulate.tabulate(tabular_data=sp_list, tablefmt='github')
        await ctx.send(content=f'```{sp_list}```')
        
    else:
        await ctx.send(file=discord.File('./pi_yo_6/template/_speakers.png'))



@client.command(aliases=['vl'])
async def voice_list(ctx:commands.Context):
    await ctx.send(embed=await VoiceList.embed(ctx.guild), view=VoiceList.CreateView(g_opts=g_opts, VVox=VVox))




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
    print(f'.\n#message.server  : {guild.name} ({message.channel.name})')
    print( message.author.name +" (",message.author.display_name,') : '+ message.content)

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
        self.Config = Config
        self.VVox = VVox
        self.MA = MultiAudio(guild, client, self)
        self.Voice = ChatReader(self)
        self.count_loop = 0
        self.loop_5.start()


    @tasks.loop(seconds=5.0)
    async def loop_5(self):
        mems = self.vc.channel.members
        # 強制切断検知
        if not client.user.id in [_.id for _ in mems]:
            self.count_loop += 1
            if 2 <= self.count_loop:
                print(f'{self.gn} : #強制切断')
                await _bye(self.guild)

        # voice channelに誰もいなくなったことを確認
        elif not False in [_.bot for _ in mems]:
            self.count_loop += 1
            if 2 <= self.count_loop:
                print(f'{self.gn} : #誰もいなくなったため 切断')
                await _bye(self.guild)

        # Reset Count
        else:
            self.count_loop = 0


client.run(Config.Token)