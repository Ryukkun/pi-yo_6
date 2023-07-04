import time
import os
import uuid
import wave
import logging
import numpy as np
from discord import Message

from .load_config import GC, UC
from .synthetic_voice import GenerateVoice
from .voice_client import _StreamAudioData as SAD
from config import Config

bot_prefix = r',./?!;>'
_log = logging.getLogger(__name__)

class ChatReader:
    def __init__(self, Info):
        try:
            from .main import DataInfo
            self.Info:DataInfo
        except Exception: pass
        self.Info = Info
        self.MA = self.Info.MA
        self.Vvc = self.MA.add_player(opus=True)
        self.guild = self.Info.guild
        self.gid = self.Info.gid
        self.vc = self.guild.voice_client
        self.Queue = []
        self.CLoop = self.Info.loop
        self.GC = GC(self.gid)
        self.generate_voice = GenerateVoice(self.Info.engines)
        self.raw_creat_voice = self.generate_voice.raw_create_voice
        self.creat_voice = self.generate_voice.creat_voice


    async def on_message(self, message:Message):
        if not message.content:
            return
        # コマンドではなく なおかつ Joinしている場合
        if not message.content[0] in bot_prefix and self.vc:

            now_time = time.perf_counter()
            self.Queue.append([message.id, 0])

            # ボイス初期設定
            text = message.content
            uid = str(message.author.id)
            g_config = self.GC.Read()
            speaker_id = -1
            if (speaker_id := g_config['voice'].get(uid,-1)) != -1:
                pass
            elif (speaker_id := UC.Read(uid)['voice']) != -1:
                pass
            elif (speaker_id := g_config.get('server_voice',-1)) != -1:
                pass
            if speaker_id != -1:
                text = f'voice:{speaker_id} {text}'

            # 音声ファイル ファイル作成
            try: source = await self.creat_voice(text, message)
            except Exception as e:                                              # Error
                print(f"Error : 音声ファイル作成に失敗 {e}")
                self.Queue.remove([message.id, 0])
                return

            print(f'生成時間 : {time.perf_counter()-now_time}')
            i = self.Queue.index([message.id, 0])
            self.Queue[i:i+1] = [[_,1] for _ in source]

            # 再生されるまでループ
            if not self.Vvc.is_playing():
                await self.play_loop()


    async def on_message_from_str(self, message:str):
        # Joinしている場合
        if self.vc:

            now_time = time.perf_counter()
            mes_id = uuid.uuid4()
            self.Queue.append([mes_id, 0])

            # 音声ファイル ファイル作成
            try: source = await self.raw_creat_voice(message, mes_id)
            except Exception as e:                                              # Error
                print(f"Error : 音声ファイル作成に失敗 {e}")
                self.Queue.remove([mes_id, 0])
                return

            print(f'生成時間 : {time.perf_counter()-now_time}')
            i = self.Queue.index([mes_id, 0])
            self.Queue[i:i+1] = [[_,1] for _ in source]

            # 再生されるまでループ
            if not self.Vvc.is_playing():
                await self.play_loop()



    async def count(self, voice:str):
        now_time = time.perf_counter()
        voice = f'voice:{voice}'
        v = [
            self.CLoop.create_task( self.raw_creat_voice(f'{voice} 3!')),
            self.CLoop.create_task( self.raw_creat_voice(f'{voice} 2!')),
            self.CLoop.create_task( self.raw_creat_voice(f'{voice} 1!')),
            self.CLoop.create_task( self.raw_creat_voice(f'{voice} 0!')),
            ]
        source = await self.raw_creat_voice(f'{voice} いくよー?')
        source = source[0]

        with wave.open(source, 'rb') as f:
            FRAME_RATE = f.getframerate()
            SAMPWIDTH = f.getsampwidth()
            NCHANNELS = f.getnchannels()
            adata = np.frombuffer(f.readframes(-1), np.int16)
            adata = np.append(adata, np.zeros(FRAME_RATE//2, np.int16))
        os.remove(source)

        for _ in v:
            source = await _
            source = source[0]
            with wave.open(source, 'rb') as f:
                adata = np.append(adata, np.frombuffer(f.readframes(-1), np.int16))
                if v[-1] != _:
                    adata = np.append(adata, np.zeros((FRAME_RATE - f.getnframes()), np.int16))
            os.remove(source)

        out = f'{Config.output}{uuid.uuid4()}.wav'
        with wave.open(out, 'wb') as fw:
            fw.setframerate(FRAME_RATE)
            fw.setsampwidth(SAMPWIDTH)
            fw.setnchannels(NCHANNELS)
            fw.writeframes(adata)

        print(f'生成時間 : {time.perf_counter()-now_time}')
        self.Queue.append([out, 1])

        # 再生されるまでループ
        if not self.Vvc.is_playing():
            await self.play_loop()



#---------------------------------------------------------------------------------------
#   再生 Loop
#---------------------------------------------------------------------------------------
    async def play_loop(self):
        if not self.Queue: return

        while self.Queue[0][1] == 2:                # ファイル削除
            voice_data = self.Queue[0]
            if os.path.isfile(voice_data[0]):
                os.remove(voice_data[0])
            del self.Queue[0]
            if not self.Queue: return

        if self.Queue[0][1] == 1:                   # 再生
            source = self.Queue[0][0]
            self.Queue[0][1] = 2
            _log.info(f"Play  <{self.guild.name}>")

            await self.Vvc.play(SAD(source).from_local_path(),lambda : self.CLoop.create_task(self.play_loop()))
            return

        if self.Queue[0][1] == 0:                   # Skip
            _log.info(f"作成途中かな {self.guild.name} {self.Queue}")