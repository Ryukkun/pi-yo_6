import asyncio
import time
import os
import uuid
import wave
import logging
import numpy as np
from discord import Message

from pi_yo_6.message_unit import MessageUnit

from .load_config import GC, UC
from .voice_client import StreamAudioData
from config import Config

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main import DataInfo

bot_prefix = r',./?!;>'
_log = logging.getLogger(__name__)

class ChatReader:
    def __init__(self, Info:"DataInfo") -> None:
        self.info = Info
        self.track = self.info.MA.add_track(opus=True)
        self.guild = self.info.guild
        self.Queue = []
        self.GC = GC(self.guild.id)


    async def on_message(self, message:Message):
        if not message.content:
            return
        # コマンドではなく なおかつ Joinしている場合
        if not message.content[0] in bot_prefix and self.guild.voice_client:

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
            try: 
                msg_unit = MessageUnit(text, self.info.cog.engines)
                await msg_unit.normalize_text(self.guild.id)
                source = await msg_unit.create_voice()
            except Exception as e:                                              # Error
                print(f"Error : 音声ファイル作成に失敗 {e}")
                self.Queue.remove([message.id, 0])
                return

            print(f'生成時間 : {time.perf_counter()-now_time}')
            i = self.Queue.index([message.id, 0])
            self.Queue[i:i+1] = [[_,1] for _ in source]

            # 再生されるまでループ
            if not self.track.has_play_data():
                await self.play_loop()


    async def on_message_from_str(self, message:str):
        # Joinしている場合
        if self.info.vc:

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
            if not self.track.has_play_data():
                await self.play_loop()



    async def count(self, voice:str):
        now_time = time.perf_counter()
        voice = f'voice:{voice}'
        v = [
            asyncio.create_task( self.raw_creat_voice(f'{voice} 3!')),
            asyncio.create_task( self.raw_creat_voice(f'{voice} 2!')),
            asyncio.create_task( self.raw_creat_voice(f'{voice} 1!')),
            asyncio.create_task( self.raw_creat_voice(f'{voice} 0!')),
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
        if not self.track.has_play_data():
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

            await self.track.play(StreamAudioData(source), lambda : asyncio.run_coroutine_threadsafe(self.play_loop(), self.info.cog.bot.loop))
            return

        if self.Queue[0][1] == 0:                   # Skip
            _log.info(f"作成途中かな {self.guild.name} {self.Queue}")