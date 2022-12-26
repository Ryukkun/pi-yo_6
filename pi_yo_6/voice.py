import time
import os
from discord import Message

from .load_config import GC, UC
from .synthetic_voice import GenerateVoice
from .audio_source import StreamAudioData as SAD

bot_prefix = r',./?!;>'

class ChatReader():
    def __init__(self, Info):
        try:
            from ..main import DataInfo
            from .template._config import Config
            self.Info:DataInfo
            self.Config:Config
        except Exception: pass
        self.Info = Info
        self.MA = self.Info.MA
        self.Vvc = self.Info.MA.add_player(RNum=-1 ,opus=False)
        self.guild = self.Info.guild
        self.gid = self.Info.gid
        self.gn = self.Info.gn
        self.vc = self.guild.voice_client
        self.Queue = []
        self.Config = Info.Config
        self.CLoop = Info.loop
        self.GC = GC(self.Config.Guild_Config, self.gid)
        self.UC = UC(self.Config.User_Config)
        self.creat_voice = GenerateVoice(self.Config, self.Info.VVox).creat_voice

    async def on_message(self, message:Message):
        # コマンドではなく なおかつ Joinしている場合
        if not message.content[0] in bot_prefix and self.vc:

            now_time = time.time()
            _id = f"{self.gid}{now_time}"
            self.Queue.append([_id,0])

            # ボイス初期設定
            mess = message.content
            uid = str(message.author.id)
            g_config = self.GC.Read()
            speaker_id = -1
            if (speaker_id := g_config['voice'].get(uid,-1)) != -1:
                pass
            elif (speaker_id := self.UC.Read(uid)['voice']) != -1:
                pass
            elif (speaker_id := g_config.get('server_voice',-1)) != -1:
                pass
            if speaker_id != -1:
                mess = f'voice:{speaker_id} {mess}'

            # 音声ファイル ファイル作成
            try: source = await self.creat_voice(mess ,str(self.gid),str(now_time))
            except Exception as e:                                              # Error
                print(f"Error : 音声ファイル作成に失敗 {e}")
                self.Queue.remove([_id,0])
                return

            print(f'生成時間 : {time.time()-now_time}')
            i = self.Queue.index([_id,0])
            self.Queue[i:i+1] = [[_,1] for _ in source]

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