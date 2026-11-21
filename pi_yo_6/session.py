import asyncio
import io
import logging
import random
import time
from typing import Callable, Optional

import discord
from discord.ext import tasks

from pi_yo_6.audio.mixer import AudioMixer, AudioTrack, StreamAudioData
from pi_yo_6.config import guild_configs, user_configs
from pi_yo_6.models import EngineType, VoiceSetting
from pi_yo_6.text.normalizer import TextNormalizer
from pi_yo_6.tts.manager import TTSManager

_COMMAND_PREFIXES = r',./?!;>'
_log = logging.getLogger(__name__)


class GuildVoiceSession:
    """1つのギルドにおけるVC接続・読み上げ対象チャンネル・音声再生キューを統合管理する"""

    def __init__(
        self,
        guild: discord.Guild,
        vc: discord.VoiceClient,
        loop: asyncio.AbstractEventLoop,
        tts: TTSManager,
        initial_channel_id: int | None = None,
        on_close: Optional[Callable[[int], None]] = None,
    ) -> None:
        self.guild = guild
        self.vc = vc
        self.tts = tts
        self._on_close = on_close
        self._closing = False

        self.target_channels: set[int] = set()
        if initial_channel_id:
            self.target_channels.add(initial_channel_id)
        if vc.channel:
            self.target_channels.add(vc.channel.id)

        self.mixer = AudioMixer(vc=vc, loop=loop, guild_name=guild.name)
        self.tracks: list[AudioTrack] = [self.mixer.add_track(opus=False) for _ in range(3)]
        self._queue: asyncio.Queue[asyncio.Task[Optional[io.BytesIO]]] = asyncio.Queue()
        self._busy_tracks: set[int] = set()
        self._track_free_event = asyncio.Event()
        self._empty_channel_loop_count = 0
        self._worker_task: asyncio.Task[None] = asyncio.create_task(self._play_worker())
        self._inactivity_check_loop.start()

    def _get_free_track_idx(self) -> int | None:
        gc = guild_configs.get(self.guild.id)
        max_active = (
            min(max(1, gc.data.max_tracks), len(self.tracks)) if gc.data.overlap_mode else 1
        )
        for idx in range(max_active):
            if idx not in self._busy_tracks and not self.tracks[idx].has_play_data():
                return idx
        return None

    def notify_config_changed(self) -> None:
        """設定変更時に待機中のワーカーへ通知する"""
        self._track_free_event.set()

    def stop_all(self) -> None:
        """すべてのトラックの再生を即座に停止し、待ち行列をクリア"""
        while not self._queue.empty():
            try:
                gen_task = self._queue.get_nowait()
                if not gen_task.done():
                    gen_task.cancel()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break

        for track in self.tracks:
            track.stop()
        self._busy_tracks.clear()
        self._track_free_event.set()

    async def close(self, reason: str = '切断') -> None:
        if self._closing:
            return
        self._closing = True
        asyncio.create_task(self._shutdown(reason))

    async def _shutdown(self, reason: str) -> None:
        self._inactivity_check_loop.cancel()
        if not self._worker_task.done():
            self._worker_task.cancel()
        self.stop_all()
        self.mixer.kill()
        if self._on_close:
            self._on_close(self.guild.id)

        _log.info(f'{self.guild.name} : #{reason}')
        await asyncio.sleep(0.02)
        try:
            if self.vc.is_connected():
                await self.vc.disconnect()
        except Exception:
            pass

    def resolve_user_voice(self, user_id: int) -> VoiceSetting:
        """ユーザー設定のボイスを取得し、利用不可ならランダムボイスを割り当てて保存する"""
        uc = user_configs.get(user_id)
        if not self.tts.is_available(uc.data.voice):
            uc.data.voice = self.random_voice()
            uc.write()
        return uc.data.voice.model_copy()

    def random_voice(self) -> VoiceSetting:
        """ランダムなOpenJTalkのVoiceSettingを返す"""
        metas = self.tts.open_jtalk.metas
        for meta in metas:
            if meta['name'] == 'mei':
                style = random.choice(meta['styles'])
                return VoiceSetting(
                    type=EngineType.OPEN_JTALK,
                    name='mei',
                    style=style['name'],
                    speed=1.2,
                    tone=round(random.uniform(-15.0, 15.0), 1),
                )
        return VoiceSetting(
            type=EngineType.OPEN_JTALK,
            name=metas[0]['name'],
            style=metas[0]['styles'][0]['name'],
            speed=1.2,
            tone=round(random.uniform(-15.0, 15.0), 1),
        )

    async def enqueue_message(self, message: discord.Message) -> None:
        """Discordメッセージを読み上げキューへ投入する"""
        raw_content = message.content or ""
        if raw_content and raw_content[0] in _COMMAND_PREFIXES:
            return
        if not self.guild.voice_client:
            return

        full_text = TextNormalizer.extract_message_text(message)
        if not full_text:
            return

        voice = self.resolve_user_voice(message.author.id)
        await self.enqueue_speech(full_text, voice, guild=self.guild)

    async def enqueue_speech(
        self,
        text: str,
        voice: VoiceSetting,
        guild: Optional[discord.Guild] = None,
    ) -> None:
        """テキストを正規化し、非同期合成タスクを開始して再生キューへ投入する"""
        normalized_text, final_voice = TextNormalizer.normalize(
            text,
            voice,
            guild=guild or self.guild,
            voice_resolver=self.tts.find_voice,
        )
        if not normalized_text.strip():
            return

        gen_task = asyncio.create_task(self._synthesize(normalized_text, final_voice))
        await self._queue.put(gen_task)

    async def _synthesize(self, text: str, voice: VoiceSetting) -> Optional[io.BytesIO]:
        started = time.perf_counter()
        data = await self.tts.synthesize(text, voice)
        _log.info(f'生成時間 : {time.perf_counter() - started:.4f}s')
        return data

    async def _play_worker(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            gen_task = await self._queue.get()
            try:
                audio_data = await gen_task
            except asyncio.CancelledError:
                self._queue.task_done()
                continue
            except Exception as e:
                _log.error(f"音声ファイル作成に失敗 {e}")
                self._queue.task_done()
                continue

            if audio_data is None:
                self._queue.task_done()
                continue

            while True:
                track_idx = self._get_free_track_idx()
                if track_idx is not None:
                    break
                self._track_free_event.clear()
                if (track_idx := self._get_free_track_idx()) is not None:
                    break
                await self._track_free_event.wait()

            self._busy_tracks.add(track_idx)
            asyncio.create_task(self._play_on_track(track_idx, audio_data, loop))
            self._queue.task_done()

    async def _play_on_track(
        self, track_idx: int, audio_data: io.BytesIO, loop: asyncio.AbstractEventLoop
    ) -> None:
        track = self.tracks[track_idx]
        done_event = asyncio.Event()
        _log.info(f"Play <{self.guild.name}> on track[{track_idx}]")
        try:
            await track.play(
                StreamAudioData(audio_data),
                after=lambda: loop.call_soon_threadsafe(done_event.set),
            )
            await done_event.wait()
        except Exception as e:
            _log.error(f"Error during playback: {e}")
        finally:
            self._busy_tracks.discard(track_idx)
            self._track_free_event.set()

    @tasks.loop(seconds=5.0)
    async def _inactivity_check_loop(self) -> None:
        if self._closing:
            return
        channel = self.vc.channel
        if not channel:
            await self.close(reason="チャンネル未存在のため切断")
            return

        members = channel.members
        if self.guild.me and self.guild.me not in members:
            await self.close(reason="強制切断検知")
            return

        if not any(not m.bot for m in members):
            self._empty_channel_loop_count += 1
            if self._empty_channel_loop_count >= 2:
                await self.close(reason="誰もいなくなったため切断")
        else:
            self._empty_channel_loop_count = 0
