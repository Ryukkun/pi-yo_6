import asyncio
from collections import deque
import io
import logging
from math import sqrt
from pathlib import Path
import threading
import time
from typing import TYPE_CHECKING, Any, Callable, Union

from discord import FFmpegAudio, FFmpegOpusAudio, FFmpegPCMAudio, Guild, SpeakingState, opus
import numpy as np

if TYPE_CHECKING:
    from pi_yo_6.main import DataInfo

_log = logging.getLogger(__name__)


class StreamAudioData:
    def __init__(
        self,
        source: str | Path | io.BufferedIOBase,
        volume: float | None = None,
    ) -> None:
        """音声データの作成

        Parameters
        ----------
        source : str | Path | io.BufferedIOBase
            strの場合はURL、Pathの場合はローカルファイルとして扱う
        volume : float | None, optional
            ボリューム (dB), by default None
        """
        self.source = source
        self.volume = volume

    def _get_ffmpegaudio(
        self, use_opus: bool, before_options: list[str], options: list[str]
    ) -> Union[FFmpegOpusAudio, FFmpegPCMAudio]:
        option = ' '.join(options)
        before_option = ' '.join(before_options)
        source = str(self.source) if isinstance(self.source, Path) else self.source
        is_pipe = isinstance(self.source, io.BufferedIOBase)

        if use_opus:
            return FFmpegOpusAudio(
                source, before_options=before_option, options=option, pipe=is_pipe
            )
        return FFmpegPCMAudio(
            source, before_options=before_option, options=option, pipe=is_pipe
        )

    def get_ffmpegaudio(self, use_opus: bool) -> 'FFmpegReader':
        before_options: list[str] = []
        options = ['-vn', '-loglevel', 'quiet']
        if use_opus:
            options.extend(['-application', 'audio'])

        if isinstance(self.source, str):
            before_options.extend(
                (
                    '-reconnect',
                    '1',
                    '-reconnect_streamed',
                    '1',
                    '-reconnect_delay_max',
                    '5',
                    '-analyzeduration',
                    '2147483647',
                    '-probesize',
                    '2147483647',
                )
            )

        if self.volume is not None:
            options.extend(('-af', f'volume={self.volume}dB'))

        return FFmpegReader(self._get_ffmpegaudio(use_opus, before_options, options))


class FFmpegReader:
    """ffmpegのreadのブロックをなくすことを目的としている"""

    def __init__(self, ffmpeg: FFmpegAudio) -> None:
        self.ffmpeg = ffmpeg
        self.next_q: deque[bytes] = deque()
        self.stop_flag = threading.Event()
        self._done = False

        def read_all() -> None:
            try:
                while not self.stop_flag.is_set() and (data := self.ffmpeg.read()):
                    self.next_q.append(data)
            finally:
                self._done = True

        self._thread = threading.Thread(target=read_all, daemon=True)
        self._thread.start()

    def read(self) -> bytes | None:
        """
        Returns
        -------
        bytes | None
            b''は読み込み終了を意味する。
            Noneはまだ読み込みは終わっていないがreadが間に合っていない
        """
        if self.next_q:
            return self.next_q.popleft()
        if self._done:
            return b''
        return None

    def cleanup(self) -> None:
        self.stop_flag.set()
        try:
            self.ffmpeg.cleanup()
        except Exception:
            pass
        self.next_q.clear()


class MultiAudioVoiceClient:
    """
    Discord標準のAudioPlayerは同時に1つまでの音源再生にしか対応していないため、
    複数トラックを20ms間隔で合成・送信する独自プレイヤー。
    """

    def __init__(self, guild: Guild, info: "DataInfo") -> None:
        self.enable_loop = True
        self.guild = guild
        self.loop = info.cog.bot.loop
        self.info = info
        self.tracks: list['AudioTrack'] = []
        self.enc_bool = False
        self.info.vc.encoder = opus.Encoder()
        self._thread_lock = threading.Lock()
        self._is_running = False

    def kill(self) -> None:
        self.enable_loop = False
        for track in self.tracks:
            track._cleanup_reader()

    def add_track(self, opus: bool = False) -> 'AudioTrack':
        player = AudioTrack(use_opus=opus, vc=self)
        self.tracks.append(player)
        self.enc_bool = len(self.tracks) != 1 or not opus
        return player

    def run_loop_check(self) -> None:
        playing = any(not p.is_paused() for p in self.tracks)
        if not playing:
            return
        with self._thread_lock:
            if self._is_running or not self.enable_loop:
                return
            self._is_running = True
            threading.Thread(target=self._run_loop, daemon=True).start()

    def __speak(self, speaking: SpeakingState) -> None:
        """音声ステータスを変える（botがjoinした後に参加した人にも音を届けるため）"""
        try:
            ws = getattr(self.info.vc, 'ws', None)
            if ws is not None:
                asyncio.run_coroutine_threadsafe(ws.speak(speaking), self.loop)
        except Exception:
            _log.exception(f"func:__speak  guild:{self.info.guild.name}")

    def _run_loop(self) -> None:
        """
        音声データを別スレッドで20msごとに合成・送信する。
        """
        send_audio = self.info.vc.send_audio_packet
        self.__speak(SpeakingState.voice)
        _start = time.perf_counter()
        try:
            while self.enable_loop:
                byte_list: list[bytes] = []
                for track in self.tracks:
                    if _byte := track.read_bytes():
                        byte_list.append(_byte)

                audio_bytes = b''
                active_track = len(byte_list)
                if active_track == 1:
                    audio_bytes = byte_list[0]
                elif active_track >= 2:
                    if self.enc_bool:
                        max_len = max(len(b) for b in byte_list)
                        arrays = [
                            np.frombuffer(b.ljust(max_len, b'\x00'), dtype=np.int16)
                            for b in byte_list
                        ]
                        adjust_vol = 1 / sqrt(active_track)
                        audio_numpy = np.sum(arrays, axis=0) * adjust_vol
                        audio_bytes = np.clip(audio_numpy, -32768, 32767).astype(np.int16).tobytes()
                    else:
                        audio_bytes = byte_list[0]

                # Loop Delay (20ms)
                _start += 0.02
                delay = max(0.0, _start - time.perf_counter())
                time.sleep(delay)

                if audio_bytes:
                    send_audio(audio_bytes, encode=self.enc_bool)
                else:
                    send_audio(opus.OPUS_SILENCE, encode=False)
                    if not any(not p.is_paused() for p in self.tracks):
                        self.__speak(SpeakingState.none)
                        break
        except Exception:
            _log.exception(f"func:_run_loop  guild:{self.info.guild.name}")
        finally:
            with self._thread_lock:
                self._is_running = False


class AudioTrack:
    def __init__(self, use_opus: bool, vc: 'MultiAudioVoiceClient') -> None:
        self.ffmpeg_audio: FFmpegReader | None = None
        self.audio_data: StreamAudioData | None = None
        self.pausing: bool = True
        self.vc = vc
        self.after: Callable[[], Any] | None = None
        self.use_opus: bool = use_opus
        self._lock = threading.RLock()

    def _cleanup_reader(self) -> None:
        if self.ffmpeg_audio is not None:
            self.ffmpeg_audio.cleanup()
            self.ffmpeg_audio = None

    async def play(self, sad: StreamAudioData, after: Callable[[], Any] | None = None) -> None:
        with self._lock:
            self._cleanup_reader()
            self.audio_data = sad
            self.ffmpeg_audio = sad.get_ffmpegaudio(self.use_opus)
            self.after = after
            self.pausing = False
        self.vc.run_loop_check()

    def has_play_data(self) -> bool:
        return self.audio_data is not None

    def is_paused(self) -> bool:
        return self.pausing

    def read_bytes(self) -> bytes:
        """別スレッドからの呼び出しを想定。音声データがない場合は b'' を返す。"""
        if self.ffmpeg_audio and not self.pausing:
            if self._lock.acquire(blocking=False):
                try:
                    if self.ffmpeg_audio is None:
                        return b''
                    read_res = self.ffmpeg_audio.read()
                    if read_res:
                        return read_res
                    elif read_res is None:
                        return b''
                    else:
                        self._finish()
                finally:
                    self._lock.release()
        return b''

    def _finish(self) -> None:
        with self._lock:
            self._cleanup_reader()
            self.audio_data = None
            self.pausing = True
            after_cb = self.after
            self.after = None
        if after_cb:
            after_cb()
