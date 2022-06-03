import discord
from discord.ext import commands
from voice_generate import creat_WAV
import asyncio
import os
import ffmpeg
import re
import time
import random
import configparser
import shutil

# 設定 関係--------------------------

if not os.path.isfile('config.ini'):
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'Prefix':'.',
        'Token':'',
        'Admin_dic':'./dic/admin_dic.txt',
        'User_dic':'./dic/user_dic/'
    }
    config['Open_Jtalk'] = {
        'Dic':'/var/lib/mecab/dic/open-jtalk/naist-jdic',
        'Voice':'./Voice/',
        'Output':'./Output/'
    }
    with open('config.ini', 'w') as f:
        config.write(f)

config = configparser.ConfigParser()
config.read('config.ini')

shutil.rmtree(config['Open_Jtalk']['Output'])
os.makedirs(config['DEFAULT']['User_dic'], exist_ok=True)
os.makedirs(config['Open_Jtalk']['Voice'], exist_ok=True)
os.makedirs(config['Open_Jtalk']['Output'], exist_ok=True)
with open(config['DEFAULT']['Admin_dic'],'a'):pass

#---------------------------------

client = commands.Bot(command_prefix=config['DEFAULT']['Prefix'])
voice_client = None
queue_pl = {}


@client.event
async def on_ready():
    print('Logged in')
    print(client.user.name)
    print(client.user.id)
    print('----------------')


@client.command()
async def join(ctx):
    print('#join')
    await ctx.author.voice.channel.connect()
    with open(config['DEFAULT']['User_dic']+ str(ctx.guild.id) + '.txt', 'a'): pass

@client.command()
async def bye(ctx):
    print(f'{ctx.guild.name} : #切断')
    await ctx.voice_client.disconnect()

@client.command()
async def register(ctx, arg1, arg2):
    guild_id = str(ctx.guild.id)
    with open(config['DEFAULT']['User_dic']+ guild_id +'.txt', mode='a') as f:
        f.write(arg1 + ',' + arg2 + '\n')
        print(guild_id +'.txtに書き込み : '+ arg1 + ',' + arg2)

@client.command()
async def delete(ctx, arg1):
    guild_id = str(ctx.guild.id)
    with open(config['DEFAULT']['User_dic']+ guild_id +'.txt', mode='r') as f:
        text = f.read()
        replaced_text = re.sub(rf'{arg1},[^\n]+\n','',text)
    if re.search(rf'{arg1},[^\n]+\n',text):
        with open(config['DEFAULT']['User_dic']+ guild_id +'.txt', mode='w') as f:
            f.write(replaced_text)
        print(f'{guild_id}.txtから削除 : {arg1}')

@client.command()
async def 黙れ(ctx):
    if ctx.guild.voice_client.is_playing():
        ctx.guild.voice_client.stop()
        await ctx.channel.send(random.choice([";w;",":(","><",";<","無限の彼方へ飛ばすぞ","😭","( ´ཫ` )"]))
        print(f'{ctx.guild.name} : #黙る;w;')

@client.event
async def on_message(message):
    msgclient = message.guild.voice_client

    # 発言者がBotの場合はPass
    if message.author.bot:
        print('\n#message.author : bot')
    else:
        print(f'\n#message.server  : {message.guild.name} ({message.channel.name})')
        print( message.author.name +" (",message.author.display_name,') : '+ message.content)
    
        # コマンドではなく なおかつ Joinしている場合
        if not message.content.startswith(config['DEFAULT']['Prefix']) and msgclient:

            now_time = time.time()
            source = config['Open_Jtalk']['Output']+str(message.guild.id)+"-"+str(now_time)+".wav"
            if message.guild.id not in queue_pl: queue_pl[message.guild.id] = []    # 辞書の初期設定
            queue_pl[message.guild.id].append([source,0])

            # 音声ファイル ファイル作成
            try :await asyncio.create_task(creat_WAV(message.content,str(message.guild.id),str(now_time),config))
            except Exception as e:                                              # Error
                print(f"Error : 音声ファイル作成に失敗 {e}")
                queue_pl[message.guild.id].remove([source,0])

            print('生成時間 : '+str(time.time()-now_time))
            queue_pl[message.guild.id] = [[source,1] if i[0] == source else i for i in queue_pl[message.guild.id]]  # 音声ファイルが作成済みなのを記述

            # 再生されるまでループ
            if not msgclient.is_playing():
                play_loop(message.guild.name,message.guild.id,msgclient)


    await client.process_commands(message)

# 再生 Loop
def play_loop(guild_name,guild_id,msgclient):
    
    if queue_pl[guild_id] ==[]: return

    while queue_pl[guild_id][0][1] == 2:                # ファイル削除
        if os.path.isfile(queue_pl[guild_id][0][0]):
            os.remove(queue_pl[guild_id][0][0])
        del queue_pl[guild_id][0]
        if queue_pl[guild_id] ==[]: return

    if queue_pl[guild_id][0][1] == 1:                   # 再生
        source_play = queue_pl[guild_id][0][0]
        queue_pl[guild_id][0][1] = 2
        print(f"Play  <{guild_name}>")
        msgclient.play(discord.FFmpegPCMAudio(source_play),after=lambda e: play_loop(guild_name,guild_id,msgclient))
        return

    if queue_pl[guild_id][0][1] == 0:                   # Skip
        print("作成途中かな " + str(queue_pl[guild_id]))


client.run(config['DEFAULT']['Token'])