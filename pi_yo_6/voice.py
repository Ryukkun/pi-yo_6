import asyncio
import time
import logging
from discord import Message
from typing import TYPE_CHECKING

from pi_yo_6.message_unit import MessageUnit
from pi_yo_6.load_config import UserConfig
from pi_yo_6.voice_client import StreamAudioData
from pi_yo_6.config import Config


if TYPE_CHECKING:
    from pi_yo_6.main import DataInfo

bot_prefix = r',./?!;>'
_log = logging.getLogger(__name__)

class ChatReader:
    def __init__(self, Info:"DataInfo") -> None:
        self.info = Info
        self.track = self.info.MA.add_track(opus=True)
        self.guild = self.info.guild
        self.Queue:list[MessageUnit] = []


    async def on_message(self, message:Message):
        if not message.content:
            return
        # コマンドではなく なおかつ Joinしている場合
        if not message.content[0] in bot_prefix and self.guild.voice_client:
            # ボイス初期設定
            text = message.content
            user_config = UserConfig.get(message.author.id)

            msg_unit = MessageUnit(text, self.info.cog.engines, message.created_at)
            msg_unit.voice = user_config.data.voice
            await msg_unit.normalize_text(self.guild.id)
            await self.play_message(msg_unit)



    async def play_message(self, msg_unit:MessageUnit):
            now_time = time.perf_counter()
            self.Queue.append(msg_unit)
            self.Queue.sort(key=lambda x: x.time) # 時間でソート
            try: 
                await msg_unit.create_voice()
            except Exception as e:                                              # Error
                print(f"Error : 音声ファイル作成に失敗 {e}")
                self.Queue.remove(msg_unit)
                return

            print(f'生成時間 : {time.perf_counter()-now_time}')

            # 再生されるまでループ
            if not self.track.has_play_data():
                await self.play_loop()



#---------------------------------------------------------------------------------------
#   再生 Loop
#---------------------------------------------------------------------------------------
    async def play_loop(self):
        if not self.Queue: return

        if self.Queue[0].generated:           # 再生
            msg = self.Queue.pop(0)
            _log.info(f"Play  <{self.guild.name}> {msg.out_path}")
            await self.track.play(StreamAudioData(msg.out_path), after=lambda: self.callback(msg))
            return
        else:
            _log.info(f"作成途中かな {self.guild.name} {self.Queue}")

    def callback(self, msg_unit:MessageUnit):
        msg_unit.delete_file()
        asyncio.run_coroutine_threadsafe(self.play_loop(), self.info.cog.bot.loop)