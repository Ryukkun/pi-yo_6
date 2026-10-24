import asyncio
import logging
import random
import time
from typing import TYPE_CHECKING

from discord import Message

from pi_yo_6.load_config import GuildConfig, UserConfig
from pi_yo_6.message_unit import MessageUnit
from pi_yo_6.synthetic_voice import SyntheticEngines
from pi_yo_6.utils import ENGINE_TYPE, VoiceUnit
from pi_yo_6.voice_client import AudioTrack, StreamAudioData

if TYPE_CHECKING:
    from pi_yo_6.main import DataInfo

bot_prefix = r',./?!;>'
_log = logging.getLogger(__name__)


class ChatReader:
    def __init__(self, Info: "DataInfo") -> None:
        self.info = Info
        self.guild = self.info.guild
        # 最大3トラックを事前に確保
        self.tracks: list[AudioTrack] = [self.info.MA.add_track(opus=True) for _ in range(3)]
        self.track = self.tracks[0]  # 後方互換用参照
        self._queue: asyncio.Queue[tuple[MessageUnit, asyncio.Task[None]]] = asyncio.Queue()
        self._available_tracks: asyncio.Queue[AudioTrack] = asyncio.Queue()
        self._active_track_count = 1
        self._sync_track_pool()
        self._worker_task: asyncio.Task[None] = asyncio.create_task(self._play_worker())

    def _sync_track_pool(self) -> None:
        gc = GuildConfig.get(self.guild.id)
        desired = (
            min(max(1, gc.data.max_tracks), len(self.tracks)) if gc.data.overlap_mode else 1
        )
        if desired != self._active_track_count:
            # 現在の利用可能キューをリセットして再構築
            while not self._available_tracks.empty():
                try:
                    self._available_tracks.get_nowait()
                except asyncio.QueueEmpty:
                    break
            self._active_track_count = desired
            for i in range(desired):
                self._available_tracks.put_nowait(self.tracks[i])
        elif self._available_tracks.empty() and not any(
            t.has_play_data() for t in self.tracks[: self._active_track_count]
        ):
            for i in range(self._active_track_count):
                self._available_tracks.put_nowait(self.tracks[i])

    def stop_all(self) -> None:
        """すべてのトラックの再生を即座に停止し、待ち行列をクリア"""
        while not self._queue.empty():
            try:
                _, gen_task = self._queue.get_nowait()
                if not gen_task.done():
                    gen_task.cancel()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break

        for track in self.tracks:
            track._finish()

    def close(self) -> None:
        if not self._worker_task.done():
            self._worker_task.cancel()
        self.stop_all()

    async def on_message(self, message: Message) -> None:
        raw_content = message.content or ""
        # プレフィックスコマンドの場合はスキップ
        if raw_content and raw_content[0] in bot_prefix:
            return
        if not self.guild.voice_client:
            return

        text_parts: list[str] = []
        if raw_content:
            text_parts.append(raw_content)

        # 添付ファイル対応
        if message.attachments:
            attach_types: list[str] = []
            for a in message.attachments:
                ctype = a.content_type or ""
                if ctype.startswith("image/"):
                    attach_types.append("画像")
                elif ctype.startswith("video/"):
                    attach_types.append("動画")
                elif ctype.startswith("audio/"):
                    attach_types.append("音声")
                else:
                    attach_types.append("ファイル")
            if attach_types:
                text_parts.append(f"{'と'.join(attach_types)}が送信されました")

        # スタンプ対応
        if message.stickers:
            sticker_names = [s.name for s in message.stickers]
            text_parts.append(f"スタンプ、{', '.join(sticker_names)}")

        if not text_parts:
            return

        full_text = " ".join(text_parts).strip()
        if not full_text:
            return

        # ボイス初期設定
        user_config = UserConfig.get(message.author.id)
        if not SyntheticEngines.current.is_available(user_config.data.voice):
            user_config.data.voice = self.random_voice()
            user_config.write()

        msg_unit = MessageUnit(full_text, message.created_at)
        msg_unit.voice = user_config.data.voice
        await msg_unit.normalize_text(guild=self.guild)
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

            self._sync_track_pool()
            # 空きトラックの取得を待機
            track = await self._available_tracks.get()

            # トラック再生を開始
            asyncio.create_task(self._play_on_track(track, msg_unit, loop))
            self._queue.task_done()

    async def _play_on_track(
        self, track: AudioTrack, msg_unit: MessageUnit, loop: asyncio.AbstractEventLoop
    ) -> None:
        done_event = asyncio.Event()
        _log.info(f"Play <{self.guild.name}> on track")
        try:
            if msg_unit.data is not None:
                await track.play(
                    StreamAudioData(msg_unit.data),
                    after=lambda: loop.call_soon_threadsafe(done_event.set),
                )
                await done_event.wait()
        except Exception as e:
            _log.error(f"Error during playback: {e}")
        finally:
            self._available_tracks.put_nowait(track)
