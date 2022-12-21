import discord
import os
import re
import shutil
from discord.ext import commands
from typing import Literal

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
import pi_yo_6.voicevox.speaker_id as Speaker

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
VVox = CreateVOICEVOX(Config, use_gpu=False)



tree = client.tree
group = discord.app_commands.Group(name="pi-yo6",description="ぴーよ6号設定")

@group.command(description="呼んでないのに通話に入ってくる オフロスキー系ぴーよ")
@discord.app_commands.describe(action='初期 : False')
async def auto_join(ctx: discord.Interaction, action: Literal['True','False']):
    gid = ctx.guild_id
    _GC = GC(Config.Guild_Config, gid)
    GConfig = _GC.Read()
    if not ctx.permissions.administrator:
        embed = discord.Embed(title=f'権限がありません', colour=0xe1bd5b)
        await ctx.response.send_message(embed=embed, ephemeral= True)
        return
    if action == 'True':
        GConfig['auto_join'] = True
    else:
        GConfig['auto_join'] = False

    _GC.Write(GConfig)
    embed = discord.Embed(title=f'auto_join を {action} に変更しました', colour=0xe1bd5b)
    await ctx.response.send_message(embed=embed, ephemeral= True)


@group.command(description="自分の声帯設定")
@discord.app_commands.describe(voice='声帯設定　 　無効＝"-1"　 　例 >> "ずんだもん_ささやき"、"25"、"四国"')
@discord.app_commands.describe(voice='サーバー反映')
#@discord.app_commands.choices(voice=Speaker.speaker_list())
@discord.app_commands.choices(only=[discord.app_commands.Choice(name='このサーバーにだけ反映',value='True'),discord.app_commands.Choice(name='他のサーバーでも反映',value='False')])
async def my_voice(ctx: discord.Interaction, voice: str, only:Literal['このサーバーにだけ反映','他のサーバーにも反映']):
    gid = ctx.guild_id
    _voice = Speaker.get_speaker_id(voice)
    if type(_voice) != int: 
        embed = discord.Embed(title=f'失敗 ;w;', colour=0xe1bd5b)

    else:
        uid = ctx.user.id
        if only == 'True':
            _GC = GC(Config.Guild_Config, gid)
            GConfig = _GC.Read()
            GConfig['voice'][str(uid)] = _voice
            _GC.Write(GConfig)

        else:
            _UC = UC(Config.User_Config)
            UConfig = _UC.Read(uid)
            UConfig['voice'] = _voice
            _UC.Write(uid, UConfig)

        embed = discord.Embed(title=f'voice を {voice}({_voice}) に変更しました   [このサーバーにだけ反映:{only}]', colour=0xe1bd5b)

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
        GC(Config.Guild_Config,gid).Read()
        return True


@client.command()
async def bye(ctx:commands.Context):
    guild = ctx.guild
    gid = guild.id
    vc = guild.voice_client
    if vc:
        print(f'{guild.name} : #切断')

        g_opts[gid].MA.loop = False
        del g_opts[gid]
        await vc.disconnect()
        
  
  
@client.event
async def on_voice_state_update(member:discord.Member, befor:discord.VoiceState, after:discord.VoiceState):
    # voice channelに誰もいなくなったことを確認
    if not befor.channel:
        return
    if befor.channel != after.channel:
        if vc := befor.channel.guild.voice_client:
            if not befor.channel == vc.channel:
                return
            if mems := befor.channel.members:
                for mem in mems:
                    if not mem.bot:
                        return
                await bye(befor.channel)







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

    _GC = GC(Config.Guild_Config, gid).Read()
    if voice and _GC['auto_join']:
        if voice.channel and not guild.voice_client:
            if voice.mute or voice.self_mute:
                await join(message)

    try: await g_opts[gid].Voice.on_message(message)
    except KeyError:pass

    # Fin
    await client.process_commands(message)





class DataInfo():
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


client.run(Config.Token)