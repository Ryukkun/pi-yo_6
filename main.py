import discord
import os
import re
import shutil
from discord.ext import commands

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




####  基本的コマンド
@client.event
async def on_ready():
    print('Logged in')
    print(client.user.name)
    print(client.user.id)
    print('----------------')
    


@client.command()
async def join(ctx):
    if vc := ctx.author.voice:
        gid = ctx.guild.id
        print(f'{ctx.guild.name} : #join')
        try: await vc.channel.connect(self_deaf=True)
        except discord.ClientException: return
        g_opts[gid] = DataInfo(ctx.guild)

        with open(config.User_dic+ str(ctx.guild.id) + '.txt', 'a'): pass
    

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
    await g_opts[ctx.guild.id].Music._playing()

@client.event
async def on_reaction_add(Reac,User):
    await g_opts[User.guild.id].Music.on_reaction_add(Reac,User)

#---------------------------------------------------------------------------------------------------
#   Skip
#---------------------------------------------------------------------------------------------------

@client.command()
async def skip(ctx):
    await g_opts[ctx.guild.id].Music._skip(ctx)





##############################################################################
# Play & Queue
##############################################################################

@client.command()
async def queue(ctx,*args):
    if not ctx.guild.voice_client:
        await join(ctx)
    await g_opts[ctx.guild.id].Music._play(ctx,args,True)

@client.command()
async def q(ctx,*args):
    if not ctx.guild.voice_client:
        await join(ctx)
    await g_opts[ctx.guild.id].Music._play(ctx,args,True)

@client.command()
async def play(ctx,*args):
    if not ctx.guild.voice_client:
        await join(ctx)
    await g_opts[ctx.guild.id].Music._play(ctx,args,False)

@client.command()
async def p(ctx,*args):
    if not ctx.guild.voice_client:
        await join(ctx)
    await g_opts[ctx.guild.id].Music._play(ctx,args,False)







############################################################################################
#   Playlist
############################################################################################

@client.command()
async def playlist(ctx,*args):
    if not ctx.guild.voice_client:
        await join(ctx)
    await g_opts[ctx.guild.id].Music._playlist(ctx,args)

@client.command()
async def pl(ctx,*args):
    if not ctx.guild.voice_client:
        await join(ctx)
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
        g_opts[gid].Vvc.stop()
        await g_opts[gid].play_Vloop()

@client.command()
async def shutup(ctx):
    if ctx.guild.voice_client:
        gid = ctx.guild.id
        g_opts[gid].Vvc.stop()
        await g_opts[gid].play_Vloop()

@client.event
async def on_message(message):
    gid = message.guild.id
    try:
        await g_opts[gid].Music.on_message(message)
        await g_opts[gid].Voice.on_message(message)
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