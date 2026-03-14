import asyncio
import random
import time
import logging
from discord import Message
from typing import TYPE_CHECKING

from pi_yo_6.message_unit import MessageUnit
from pi_yo_6.load_config import UserConfig
from pi_yo_6.utils import ENGINE_TYPE, VoiceUnit
from pi_yo_6.voice_client import StreamAudioData


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
            if not self.info.cog.engines.is_available(user_config.data.voice):
                user_config.data.voice = self.random_voice()
                user_config.write()

            msg_unit = MessageUnit(text, self.info.cog.engines, message.created_at)
            msg_unit.voice = user_config.data.voice
            await msg_unit.normalize_text(self.guild.id)
            await self.play_message(msg_unit)


    def random_voice(self) -> VoiceUnit:
        """ランダムなVoiceUnitを返す"""
        metas = self.info.cog.engines.open_jtalk.metas
        for meta in metas:
            if meta['name'] == 'mei':
                style = random.choice(meta['styles'])
                return VoiceUnit(ENGINE_TYPE.OPEN_JTALK, name='mei', style=style['name'], speed=1.2, tone=random.uniform(-15.0, 15.0))
        return VoiceUnit(ENGINE_TYPE.OPEN_JTALK, name=metas[0]['name'], style=metas[0]['styles'][0]['id'], speed=1.2, tone=random.uniform(-15.0, 15.0))


    async def play_message(self, msg_unit:MessageUnit):
            now_time = time.perf_counter()
            self.Queue.append(msg_unit)
            self.Queue.sort(key=lambda x: x.time) # 時間でソート
            try: 
                await msg_unit.create_voice()
            except Exception as e:                                              # Error
                _log.error(f"音声ファイル作成に失敗 {e}")
                self.Queue.remove(msg_unit)
                return

            _log.info(f'生成時間 : {time.perf_counter()-now_time}')

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
            if msg.data == None:
                return
            _log.info(f"Play  <{self.guild.name}>")
            await self.track.play(StreamAudioData(msg.data), after=lambda: self.callback())
            return
        else:
            _log.info(f"作成途中かな {self.guild.name} {self.Queue}")

    def callback(self):
        asyncio.run_coroutine_threadsafe(self.play_loop(), self.info.cog.bot.loop)