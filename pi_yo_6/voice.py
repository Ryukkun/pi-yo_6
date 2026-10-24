import asyncio
import logging
import random
import time
from typing import TYPE_CHECKING

from discord import Message

from pi_yo_6.load_config import UserConfig
from pi_yo_6.message_unit import MessageUnit
from pi_yo_6.synthetic_voice import SyntheticEngines
from pi_yo_6.utils import ENGINE_TYPE, VoiceUnit
from pi_yo_6.voice_client import StreamAudioData

if TYPE_CHECKING:
    from pi_yo_6.main import DataInfo

bot_prefix = r',./?!;>'
_log = logging.getLogger(__name__)


class ChatReader:
    def __init__(self, Info: "DataInfo") -> None:
        self.info = Info
        self.track = self.info.MA.add_track(opus=True)
        self.guild = self.info.guild
        self._queue: asyncio.Queue[tuple[MessageUnit, asyncio.Task[None]]] = asyncio.Queue()
        self._worker_task: asyncio.Task[None] = asyncio.create_task(self._play_worker())

    def close(self) -> None:
        if not self._worker_task.done():
            self._worker_task.cancel()

    async def on_message(self, message: Message) -> None:
        if not message.content:
            return
        # コマンドではなく なおかつ Joinしている場合
        if message.content[0] not in bot_prefix and self.guild.voice_client:
            # ボイス初期設定
            text = message.content
            user_config = UserConfig.get(message.author.id)
            if not SyntheticEngines.current.is_available(user_config.data.voice):
                user_config.data.voice = self.random_voice()
                user_config.write()

            msg_unit = MessageUnit(text, message.created_at)
            msg_unit.voice = user_config.data.voice
            await msg_unit.normalize_text(self.guild.id)
            await self.play_message(msg_unit)

    def random_voice(self) -> VoiceUnit:
        """ランダムなVoiceUnitを返す"""
        metas = SyntheticEngines.current.open_jtalk.metas
        for meta in metas:
            if meta['name'] == 'mei':
                style = random.choice(meta['styles'])
                return VoiceUnit(
                    type=ENGINE_TYPE.OPEN_JTALK,
                    name='mei',
                    style=style['name'],
                    speed=1.2,
                    tone=round(random.uniform(-15.0, 15.0), 1),
                )
        return VoiceUnit(
            type=ENGINE_TYPE.OPEN_JTALK,
            name=metas[0]['name'],
            style=metas[0]['styles'][0]['name'],
            speed=1.2,
            tone=round(random.uniform(-15.0, 15.0), 1),
        )

    async def _generate_voice(self, msg_unit: MessageUnit) -> None:
        now_time = time.perf_counter()
        await msg_unit.create_voice()
        _log.info(f'生成時間 : {time.perf_counter() - now_time:.4f}s')

    async def play_message(self, msg_unit: MessageUnit) -> None:
        gen_task = asyncio.create_task(self._generate_voice(msg_unit))
        await self._queue.put((msg_unit, gen_task))

    # ---------------------------------------------------------------------------------------
    #   再生 Loop
    # ---------------------------------------------------------------------------------------
    async def _play_worker(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            msg_unit, gen_task = await self._queue.get()
            try:
                await gen_task
            except Exception as e:
                _log.error(f"音声ファイル作成に失敗 {e}")
                self._queue.task_done()
                continue

            if not msg_unit.generated or msg_unit.data is None:
                self._queue.task_done()
                continue

            done_event = asyncio.Event()
            _log.info(f"Play  <{self.guild.name}>")
            await self.track.play(
                StreamAudioData(msg_unit.data),
                after=lambda: loop.call_soon_threadsafe(done_event.set),
            )
            await done_event.wait()
            self._queue.task_done()
