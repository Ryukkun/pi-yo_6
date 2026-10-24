import asyncio
from collections import deque
import io
import logging
from math import sqrt
from pathlib import Path
import threading
import time
from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar, Union

from discord import FFmpegAudio, FFmpegOpusAudio, FFmpegPCMAudio, Guild, SpeakingState, opus
import numpy as np

from pi_yo_6.utils import run_check_storage

if TYPE_CHECKING:
    from pi_yo_6.main import DataInfo

_log = logging.getLogger(__name__)


class StreamAudioData:
    def __init__(
        self,
        source: str | Path | io.BufferedIOBase,
        volume: float | None = None,
        duration: int | None = None,
    ) -> None:
        """音声データの作成

        Parameters
        ----------
        source : str | Path | io.BufferedIOBase
            strの場合はURL、Pathの場合はローカルファイルとして扱う
        volume : float | None, optional
            ボリューム, by default None
        duration : int | None, optional
            音声の再生時間（秒）, by default None
        """
        self.source = source
        self.volume = volume
        self.duration = duration

    def _get_ffmpegaudio(
        self, opus: bool, before_options: list[str], options: list[str]
    ) -> Union[FFmpegOpusAudio, FFmpegPCMAudio]:
        option: str = ' '.join(options)
        before_option: str = ' '.join(before_options)
        source = str(self.source) if isinstance(self.source, Path) else self.source
        is_pipe = isinstance(self.source, io.BufferedIOBase)

        if opus:
            # options.extend(('-c:a', 'libopus', '-ar', '48000'))
            return FFmpegOpusAudio(
                source, before_options=before_option, options=option, pipe=is_pipe
            )
        else:
            # options.extend(('-c:a', 'pcm_s16le', '-ar', '48000'))
            return FFmpegPCMAudio(
                source, before_options=before_option, options=option, pipe=is_pipe
            )

    def get_ffmpegaudio(
        self, opus: bool, sec: float = 0.0, speed: float = 1.0, pitch: int = 0
    ) -> 'FFmpegReader':
        before_options: list[str] = []
        options = ['-vn', '-application', 'audio', '-loglevel', 'quiet']
        # options = ['-vn', '-application', 'lowdelay']
        af: list[str] = []

        # Sec
        if int(sec):
            before_options.extend(('-ss', str(sec)))
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

        # Pitch
        if pitch != 0:
            pitch_float = 2 ** (pitch / 12)
            af.append(f'rubberband=pitch={pitch_float}')

        if float(speed) != 1.0:
            af.append(f'rubberband=tempo={speed}')

        if self.volume:
            af.append(f'volume={self.volume}dB')

        # af -> str
        if af:
            options.extend(('-af', ','.join(af)))

        return FFmpegReader(self._get_ffmpegaudio(opus, before_options, options))


class FFmpegReader:
    """ffmpegのreadのブロックをなくすことを目的としている"""

    def __init__(self, ffmpeg: FFmpegAudio) -> None:
        self.ffmpeg = ffmpeg
        self.next_q: deque[bytes] = deque()
        self.prev_q: deque[bytes] = deque()
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

    def is_done(self) -> bool:
        return self._done

    def read(self) -> bytes | None:
        """
        Returns
        -------
        bytes|None
            b''は読み込み終了を意味する。
            Noneはまだ読み込みは終わっていないがreadが間に合っていない
        """
        if self.next_q:
            data = self.next_q.popleft()
            self.prev_q.append(data)
            return data
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
        self.prev_q.clear()

    def rewind(self, count: int) -> None:
        while self.prev_q and count > 0:
            self.next_q.appendleft(self.prev_q.pop())
            count -= 1

    def skip(self, count: int) -> None:
        while self.next_q and count > 0:
            self.prev_q.append(self.next_q.popleft())
            count -= 1


V = TypeVar("V", int, float)


class _Attribute(Generic[V]):
    def __init__(self, init: V, min: V, max: V, update_asource: Callable[..., Any]) -> None:
        self.value = init
        self.update_asource = update_asource
        self.min = min
        self.max = max

    def get(self) -> V:
        return self.value

    async def set(self, num: V) -> bool:
        return await self._check(num)

    async def add(self, num: V) -> bool:
        return await self._check(self.value + num)  # type: ignore[arg-type]

    async def _check(self, num: V) -> bool:
        if self.min <= num <= self.max:
            self.value = num
            await self.update_asource()
            return True
        return False


class MultiAudioVoiceClient:
    """
    Discord に存在する AudioPlayer は 同時に1つまでの音源の再生にしか対応していないため
    独自で Playerを作成
    self.run は制御方法知らんから、常にループしてる 0.02秒(20ms) 間隔で
    """

    def __init__(self, guild: Guild, info: "DataInfo") -> None:
        self.enable_loop = True
        self.guild = guild
        self.loop = info.cog.bot.loop
        self.info = info
        self.tracks: list['AudioTrack'] = []
        self.enc_bool = False
        self.info.vc.encoder = opus.Encoder()
        # self.vc.encoder.set_expected_packet_loss_percent(0.01)

    def kill(self) -> None:
        self.enable_loop = False
        for track in self.tracks:
            track._cleanup_reader()

    def add_track(self, RNum: int = 0, opus: bool = False) -> 'AudioTrack':
        player = AudioTrack(opus=opus, vc=self)
        self.tracks.append(player)
        self.enc_bool = len(self.tracks) != 1 or (len(self.tracks) == 1 and not opus)
        return player

    def run_loop_check(self) -> None:
        playing = sum(not p.is_paused() for p in self.tracks)
        if playing > 0 and not self._run_loop.is_running:
            self._run_loop.run_in_thread()

    def __speak(self, speaking: SpeakingState) -> None:
        """
        音声ステータスを変えるやつ
        これがないと botがjoinしたときに居たメンツにしか 音が聞こえない
        """
        try:
            ws = getattr(self.info.vc, 'ws', None)
            if ws is not None:
                asyncio.run_coroutine_threadsafe(ws.speak(speaking), self.loop)
        except Exception:
            _log.exception(f"func:__speak  guild:{self.info.guild.name}")

    @run_check_storage()
    def _run_loop(self) -> None:
        """
        音声データをを送る 別スレッドで動作する
        音声データ (Bytes) を取得し、必要があれば Numpy で読み込んで 合成しています
        最後に音声データ送信
        """
        send_audio = self.info.vc.send_audio_packet
        self.__speak(SpeakingState.voice)
        _start = time.perf_counter()
        try:
            while self.enable_loop:
                audio_bytes: bytes = b''
                byte_list: list[bytes] = []
                for track in self.tracks:
                    if _byte := track.read_bytes():
                        byte_list.append(_byte)

                active_track = len(byte_list)
                if active_track >= 1:
                    if self.enc_bool:
                        adjust_vol = 1 / sqrt(active_track)
                        audio_numpy: np.ndarray = np.sum(
                            [
                                np.frombuffer(byte_list[i], dtype=np.int16) * adjust_vol
                                for i in range(active_track)
                            ],
                            axis=0,
                        )
                        audio_bytes = audio_numpy.astype(np.int16).tobytes()
                    else:
                        audio_bytes = byte_list[0]

                # Loop Delay
                _start += 0.02
                delay = max(0.0, _start - time.perf_counter())
                time.sleep(delay)

                # Send Bytes
                if audio_bytes:
                    send_audio(audio_bytes, encode=self.enc_bool)
                else:
                    # thread fin
                    send_audio(opus.OPUS_SILENCE, encode=False)
                    playing = sum(not p.is_paused() for p in self.tracks)
                    if playing == 0:
                        self.__speak(SpeakingState.none)
                        break
        except Exception:
            _log.exception(f"func:_run_loop  guild:{self.info.guild.name}")


class AudioTrack:
    FRAME_LENGTH = opus.Encoder.FRAME_LENGTH / 1000  # Second
    FRAME_PER_SEC = 1000 / opus.Encoder.FRAME_LENGTH

    def __init__(self, opus: bool, vc: 'MultiAudioVoiceClient') -> None:
        self.ffmpeg_audio: FFmpegReader | None = None
        self.audio_data: StreamAudioData | None = None
        self.pausing: bool = True
        self.vc = vc
        self.timer: float = 0.0
        self.pitch = _Attribute(init=0, min=-60, max=60, update_asource=self.update_asouce_sec)
        self.speed = _Attribute(
            init=1.0, min=0.1, max=3.0, update_asource=self.update_asouce_sec
        )
        self.after: Callable[[], Any] | None = None
        self.opus: bool = opus
        self._lock = threading.RLock()

    def _cleanup_reader(self) -> None:
        if self.ffmpeg_audio is not None:
            self.ffmpeg_audio.cleanup()
            self.ffmpeg_audio = None

    async def play(self, sad: StreamAudioData, after: Callable[[], Any] | None = None) -> None:
        with self._lock:
            self._cleanup_reader()
            self.audio_data = sad
            self.ffmpeg_audio = sad.get_ffmpegaudio(
                self.opus, speed=self.speed.value, pitch=self.pitch.value
            )
            # 最初のロードは少し時間かかるから先にロード
            self.timer = 0.0
            self.after = after
            self.pausing = False
        self.vc.run_loop_check()

    def resume(self) -> None:
        if self.pausing:
            self.pausing = False
            self.vc.run_loop_check()

    def pause(self) -> None:
        if not self.pausing:
            self.pausing = True

    def has_play_data(self) -> bool:
        return self.audio_data is not None

    def is_paused(self) -> bool:
        return self.pausing

    async def skip_time(self, sec: float) -> None:
        if self.audio_data is None or self.ffmpeg_audio is None:
            return

        with self._lock:
            # n秒 進む
            if sec > 0:
                skip_data_len = int(sec * self.FRAME_PER_SEC / self.speed.get())
                target_sec = self.timer + sec
                if self.audio_data.duration is not None and self.audio_data.duration < target_sec:
                    self._finish()
                    return

                if len(self.ffmpeg_audio.next_q) + (AudioTrack.FRAME_PER_SEC * 10) < skip_data_len:
                    await self.update_asouce_sec(sec=target_sec)
                    return
                while len(self.ffmpeg_audio.next_q) < skip_data_len and not self.ffmpeg_audio.is_done():
                    await asyncio.sleep(0.01)
                self.ffmpeg_audio.skip(skip_data_len)
                self.timer += skip_data_len * self.FRAME_LENGTH * self.speed.get()

            # n秒 前に戻る
            elif sec < 0:
                target_sec = self.timer + sec
                if target_sec < 0:
                    target_sec = 0
                    sec = -self.timer
                rwd_data_len = int(-sec * self.FRAME_PER_SEC / self.speed.get())
                self.ffmpeg_audio.rewind(rwd_data_len)
                self.timer += -rwd_data_len * self.FRAME_LENGTH * self.speed.get()

    def read_bytes(self) -> bytes:
        """別スレッドからの呼び出しを想定

        Returns
        -------
        bytes
            音声データ ない場合はb''
        """
        _byte = b''
        if self.ffmpeg_audio and not self.pausing:
            # Read Bytes
            if self._lock.acquire(blocking=False):
                try:
                    if self.ffmpeg_audio is None:
                        return b''
                    read_res = self.ffmpeg_audio.read()
                    if read_res:
                        self.timer += self.FRAME_LENGTH * self.speed.get()
                        return read_res
                    elif read_res is None:
                        return b''
                    else:
                        # b'' は終了
                        self._finish()
                finally:
                    self._lock.release()
        return _byte

    async def update_asouce_sec(self, sec: float | None = None) -> None:
        if not self.audio_data:
            return
        if sec is None:
            sec = self.timer

        with self._lock:
            self._cleanup_reader()
            self.ffmpeg_audio = self.audio_data.get_ffmpegaudio(
                self.opus, sec, speed=self.speed.value, pitch=self.pitch.value
            )
            self.timer = sec

    def _finish(self) -> None:
        with self._lock:
            self._cleanup_reader()
            self.audio_data = None
            self.pausing = True
            after_cb = self.after
            self.after = None
        if after_cb:
            after_cb()
