import discord
import os
import re
import shutil
import json
from discord.ext import commands
from typing import Literal

from player import MultiAudio
from voice import ChatReader
from music import MusicController




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
intents.reactions = True
intents.voice_states = True
client = commands.Bot(command_prefix=config.Prefix,intents=intents)
g_opts = {}



tree = client.tree
group = discord.app_commands.Group(name="pi-yo",description="ぴーよ6号設定")

@group.command(description="初期:False 呼んでないのに通話に入ってくる オフロスキー系ぴーよ")
async def auto_join(ctx: discord.Interaction, action: Literal['True','False']):
    GC_Check(ctx.guild_id)
    GC_Path = f'{config.Guild_Config}{ctx.guild_id}.json'
    with open(GC_Path,'r') as f:
        GC = json.load(f)
    if not ctx.permissions.administrator and GC.admin_only:
        embed = discord.Embed(title=f'権限がありません', colour=0xe1bd5b)
        await ctx.response.send_message(embed=embed, ephemeral= True)
        return
    if action == 'True':
        GC['auto_join'] = True
    else:
        GC['auto_join'] = False
    print(GC)
    with open(GC_Path,'w') as f:
        json.dump(GC, f, indent=2)
    embed = discord.Embed(title=f'auto_join を {action} に変更しました', colour=0xe1bd5b)
    await ctx.response.send_message(embed=embed, ephemeral= True)


@group.command(description="初期:True 管理者しかスラッシュコマンドを使えないようにするか否か")
async def admin_only(ctx: discord.Interaction, action: Literal['True','False']):
    GC_Check(ctx.guild_id)
    if not ctx.permissions.administrator:
        embed = discord.Embed(title=f'権限がありません', colour=0xe1bd5b)
        await ctx.response.send_message(embed=embed, ephemeral= True)
        return
    GC_Path = f'{config.Guild_Config}{ctx.guild_id}.json'
    with open(GC_Path,'r') as f:
        GC = json.load(f)
    if action == 'True':
        GC['admin_only'] = True
    else:
        GC['admin_only'] = False
    with open(GC_Path,'w') as f:
        json.dump(GC, f, indent=2)
    embed = discord.Embed(title=f'admin_only を {action} に変更しました', colour=0xe1bd5b)
    await ctx.response.send_message(embed=embed, ephemeral= True)

tree.add_command(group)


def GC_Check(gid):
    GC_Path = f'{config.Guild_Config}{gid}.json'
    if not os.path.isfile(GC_Path):
        GC = {
            'auto_join':False,
            'admin_only':True
        }
        with open(GC_Path,'w') as f:
            json.dump(GC, f, indent=2)



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
        GC_Check(gid)
        return True


@client.command()
async def bye(ctx):
    guild = ctx.guild
    gid = guild.id
    vc = guild.voice_client
    if vc:
        print(f'{guild.name} : #切断')

        # 古いEmbedを削除
        if late_E := g_opts[gid].Music.Embed_Message:
            await late_E.delete()
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



#--------------------------------------------------
# GUI操作
#--------------------------------------------------
@client.command()
async def playing(ctx):
    try:
        await g_opts[ctx.guild.id].Music._playing()
    except KeyError:pass

@client.event
async def on_reaction_add(Reac,User):
    try:
        await g_opts[User.guild.id].Music.on_reaction_add(Reac,User)
    except KeyError:pass

#---------------------------------------------------------------------------------------------------
#   Skip
#---------------------------------------------------------------------------------------------------

@client.command()
async def skip(ctx):
    try:
        await g_opts[ctx.guild.id].Music._skip(ctx)
    except KeyError:pass




##############################################################################
# Play & Queue
##############################################################################

@client.command()
async def queue(ctx,*args):
    if not ctx.guild.voice_client:
        if not await join(ctx):
            return
    await g_opts[ctx.guild.id].Music._play(ctx,args,True)

@client.command()
async def q(ctx,*args):
    if not ctx.guild.voice_client:
        if not await join(ctx):
            return
    await g_opts[ctx.guild.id].Music._play(ctx,args,True)

@client.command()
async def play(ctx,*args):
    if not ctx.guild.voice_client:
        if not await join(ctx):
            return
    await g_opts[ctx.guild.id].Music._play(ctx,args,False)

@client.command()
async def p(ctx,*args):
    if not ctx.guild.voice_client:
        if not await join(ctx):
            return
    await g_opts[ctx.guild.id].Music._play(ctx,args,False)







############################################################################################
#   Playlist
############################################################################################

@client.command()
async def playlist(ctx,*args):
    if not ctx.guild.voice_client:
        if not await join(ctx):
            return
    await g_opts[ctx.guild.id].Music._playlist(ctx,args)

@client.command()
async def pl(ctx,*args):
    if not ctx.guild.voice_client:
        if not await join(ctx):
            return
    await g_opts[ctx.guild.id].Music._playlist(ctx,args)





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

    GC_Check(gid)
    GC_Path = f'{config.Guild_Config}{gid}.json'
    with open(GC_Path,'r') as f:
        GC = json.load(f)
    if voice and GC['auto_join']:
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
        self.MA = MultiAudio(guild, client, self)
        self.MA.start()
        self.loop = client.loop
        self.client = client
        self.config = config
        self.Voice = ChatReader(self)
        self.Music = MusicController(self)



client.run(config.Token)