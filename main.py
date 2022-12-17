import discord
import os
import re
import shutil
import asyncio
from discord.ext import commands
from typing import Literal

from .pi_yo_6.guild_config import GC
from .pi_yo_6.voice_client import MultiAudio
from .pi_yo_6.voice import ChatReader




os.chdir(os.path.dirname(os.path.abspath(__file__)))

####  Config
try: import config
except Exception:
    CLines= [
        "Prefix = '.'",
        "Token = None",
        "Admin_dic = './dic/admin_dic.txt'",
        "User_dic = './dic/user_dic/'",
        "Guild_Config = './guild_config/'"
        "",
        "class _OJ():",
        "    Dic = '/var/lib/mecab/dic/open-jtalk/naist-jdic'",
        "    Voice = './Voice/'",
        "    Output = './Output/'",
        "OJ = _OJ()"
    ]
    with open('config.py','w') as f:
        f.write('\n'.join(CLines))
    import config


try:shutil.rmtree(config.OJ.Output)
except Exception:pass
os.makedirs(config.User_dic, exist_ok=True)
os.makedirs(config.Guild_Config, exist_ok=True)
os.makedirs(config.OJ.Voice, exist_ok=True)
os.makedirs(config.OJ.Output, exist_ok=True)
with open(config.Admin_dic,'a'):pass



####  起動準備 And 初期設定
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
client = commands.Bot(command_prefix=config.Prefix,intents=intents)
g_opts = {}



tree = client.tree
group = discord.app_commands.Group(name="pi-yo6",description="ぴーよ6号設定")

@group.command(description="呼んでないのに通話に入ってくる オフロスキー系ぴーよ")
@discord.app_commands.describe(action='初期 : False')
async def auto_join(ctx: discord.Interaction, action: Literal['True','False']):
    gid = ctx.guild_id
    _GC = GC.Read(gid)

    if not ctx.permissions.administrator:
        embed = discord.Embed(title=f'権限がありません', colour=0xe1bd5b)
        await ctx.response.send_message(embed=embed, ephemeral= True)
        return
    if action == 'True':
        _GC['auto_join'] = True
    else:
        _GC['auto_join'] = False

    GC.Write(gid,_GC)
    embed = discord.Embed(title=f'auto_join を {action} に変更しました', colour=0xe1bd5b)
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
async def join(ctx):
    if vc := ctx.author.voice:
        gid = ctx.guild.id
        print(f'{ctx.guild.name} : #join')
        try: await vc.channel.connect(self_deaf=True)
        except discord.ClientException: return
        g_opts[gid] = DataInfo(ctx.guild)
        Dic_Path = f'{config.User_dic}{gid}.txt'
        with open(Dic_Path,'w'): pass
        GC.Check(gid)
        return True


@client.command()
async def bye(ctx):
    guild = ctx.guild
    gid = guild.id
    vc = guild.voice_client
    if vc:
        print(f'{guild.name} : #切断')

        g_opts[gid].MA.loop = False
        del g_opts[gid]
        await vc.disconnect()
        
  
  
@client.event
async def on_voice_state_update(member, befor, after):
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
async def register(ctx, arg1, arg2):
    gid = str(ctx.guild.id)
    with open(config.User_dic+ gid +'.txt', mode='a') as f:
        f.write(arg1 + ',' + arg2 + '\n')
        print(gid +'.txtに書き込み : '+ arg1 + ',' + arg2)


@client.command()
async def delete(ctx, arg1):
    gid = str(ctx.guild.id)
    with open(config.User_dic+ gid +'.txt', mode='r') as f:
        text = f.read()
        replaced_text = re.sub(rf'{arg1},[^\n]+\n','',text)
    if re.search(rf'{arg1},[^\n]+\n',text):
        with open(config.User_dic+ gid +'.txt', mode='w') as f:
            f.write(replaced_text)
        print(f'{gid}.txtから削除 : {arg1}')


@client.command()
async def s(ctx):
    if ctx.guild.voice_client:
        gid = ctx.guild.id
        g_opts[gid].Voice.Vvc.stop()
        await g_opts[gid].Voice.play_loop()


@client.command()
async def shutup(ctx):
    if ctx.guild.voice_client:
        gid = ctx.guild.id
        g_opts[gid].Voice.Vvc.stop()
        await g_opts[gid].Voice.play_loop()


@client.event
async def on_message(message):
    guild = message.guild
    if not guild: return
    gid = message.guild.id
    voice = message.author.voice

    _GC = GC.Read(gid)
    if voice and _GC['auto_join']:
        if voice.channel and not guild.voice_client:
            if voice.mute or voice.self_mute:
                await join(message)

    try: await g_opts[gid].Voice.on_message(message)
    except KeyError:pass

    # Fin
    await client.process_commands(message)





class DataInfo():
    def __init__(self, guild):
        self.guild = guild
        self.gn = guild.name
        self.gid = guild.id
        self.vc = guild.voice_client
        self.loop = client.loop
        self.client = client
        self.config = config
        self.MA = MultiAudio(guild, client, self)
        self.MA.start()
        self.Voice = ChatReader(self)



client.run(config.Token)