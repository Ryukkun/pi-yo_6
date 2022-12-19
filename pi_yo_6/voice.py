import time
import os

from .synthetic_voice import GenerateVoice
from .audio_source import StreamAudioData as SAD
try: from ..main import DataInfo
except Exception: pass

class ChatReader():
    def __init__(self, Info):
        try: self.Info:DataInfo
        except Exception: pass
        self.Info = Info
        self.MA = self.Info.MA
        self.Vvc = self.Info.MA.add_player('Voice' ,RNum=-1 ,opus=False)
        self.guild = self.Info.guild
        self.gid = self.Info.gid
        self.gn = self.Info.gn
        self.vc = self.guild.voice_client
        self.Queue = []
        self.Config = Info.Config
        self.CLoop = Info.loop
        self.creat_voice = GenerateVoice(self.Config, self.Info.VVox).creat_voice

    async def on_message(self, message):
        # 読み上げ
        # 発言者がBotの場合はPass
        if message.author.bot:
            return

        print(f'.\n#message.server  : {self.gn} ({message.channel.name})')
        print( message.author.name +" (",message.author.display_name,') : '+ message.content)

        # コマンドではなく なおかつ Joinしている場合
        if not message.content.startswith(self.Config.Prefix) and self.vc:

            now_time = time.time()
            source = f"{self.Config.OJ.Output}{self.gid}-{now_time}.wav"
            self.Queue.append([source,0])

            # 音声ファイル ファイル作成
            try: await self.creat_voice(message.content,str(self.gid),str(now_time))
            except Exception as e:                                              # Error
                print(f"Error : 音声ファイル作成に失敗 {e}")
                self.Queue.remove([source,0])

            print(f'生成時間 : {time.time()-now_time}')
            self.Queue = [[source,1] if i[0] == source else i for i in self.Queue]  # 音声ファイルが作成済みなのを記述

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
            print(f"Play  <{self.gn}>")

            await self.Vvc.play(SAD(source).Url_Only(),lambda : self.CLoop.create_task(self.play_loop()))
            return

        if self.Queue[0][1] == 0:                   # Skip
            print(f"作成途中かな {self.Queue}")