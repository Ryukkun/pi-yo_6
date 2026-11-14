import asyncio
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager, contextmanager
import io
import logging
from pathlib import Path
import threading
from typing import Callable, Optional

import numpy as np
import pyopenjtalk
from pyopenjtalk.htsengine import HTSEngine
import scipy.io

from pi_yo_6.config import app_config
from pi_yo_6.models import EngineType, NoMetasError, SpeakerMeta, VoiceSetting

_log = logging.getLogger(__name__)


def _lazy_hts_manager(voice_path: bytes) -> Callable[[], AbstractContextManager[HTSEngine]]:
    """HTSEngineインスタンスをスレッドセーフかつ遅延初期化するマネージャー"""
    instance: HTSEngine | None = None
    mutex = threading.Lock()

    @contextmanager
    def manager() -> Generator[HTSEngine, None, None]:
        nonlocal instance
        with mutex:
            if instance is None:
                instance = HTSEngine(voice_path)
            yield instance

    return manager


class OpenJTalkEngine:
    """OpenJTalk (pyopenjtalk-plus) によるローカル音声合成エンジン"""

    _executor = ThreadPoolExecutor()

    def __init__(self, hts_folder: Path | None = None) -> None:
        self.hts_folder = hts_folder or app_config.OpenJtalk.hts_path
        self.metas = self._load_metas()
        if not self.metas:
            raise NoMetasError('再生可能な htsvoice が存在しません')

        self.hts: dict[str, Callable[[], AbstractContextManager[HTSEngine]]] = {}
        for meta in self.metas:
            for style in meta['styles']:
                path = style['id']
                voice_bytes = str(Path(path).resolve()).encode("utf-8")
                self.hts[path] = _lazy_hts_manager(voice_bytes)

    async def run_test(self) -> None:
        default_voice = VoiceSetting(
            type=EngineType.OPEN_JTALK,
            name=self.metas[0]['name'],
            style=self.metas[0]['styles'][0]['name'],
        )
        data = await self.synthesize('テスト', default_voice)
        if data.getbuffer().nbytes == 0:
            raise RuntimeError(
                'Open Jtalkの動作確認に失敗しました。htsvoiceのパスや、辞書のパスが正しいか確認してください。'
            )

    async def _generate_waveform(
        self, text: str, hts_id: str, speed: float = 1.2, tone: float = 0.0
    ) -> tuple[np.typing.NDArray[np.float64], int]:
        labels = pyopenjtalk.extract_fullcontext(text)
        if isinstance(labels, tuple) and len(labels) == 2:
            labels = labels[1]

        hts = self.hts[hts_id]

        def _synthesize() -> tuple[np.typing.NDArray[np.float64], int]:
            with hts() as htsengine:
                sr = htsengine.get_sampling_frequency()
                htsengine.set_speed(speed)
                htsengine.add_half_tone(tone)
                return htsengine.synthesize(labels), sr

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, _synthesize)

    async def synthesize(self, text: str, voice: VoiceSetting) -> io.BytesIO:
        buffer = io.BytesIO()
        if not text.strip():
            return buffer

        speaker_path = self.to_speaker_id(voice)
        if speaker_path is None:
            speaker_path = self.metas[0]['styles'][0]['id']

        data, sr = await self._generate_waveform(
            text, speaker_path, speed=voice.speed, tone=voice.tone
        )
        max_val = np.abs(data).max()
        if max_val > 0:
            pcm_data = (data / max_val / 6 * 32767).astype(np.int16)
        else:
            pcm_data = data.astype(np.int16)
        scipy.io.wavfile.write(buffer, sr, pcm_data)
        buffer.seek(0)
        return buffer

    def to_speaker_id(self, voice: VoiceSetting) -> Optional[str]:
        for meta in self.metas:
            if meta['name'] == voice.name:
                for style in meta['styles']:
                    if style['name'] == voice.style:
                        return style['id']
        return None

    def _load_metas(self) -> list[SpeakerMeta]:
        hts_dic: dict[str, list[tuple[str, str]]] = {}
        for path in sorted(self.hts_folder.glob('*.htsvoice')):
            hts_name = path.stem
            hts_split = hts_name.split('_')
            hts_author = hts_split[0] if hts_split else hts_name
            style_name = "_".join(hts_split[1:]) if len(hts_split) >= 2 else hts_author
            hts_dic.setdefault(hts_author, []).append((style_name, str(path)))

        return [
            {
                'name': k,
                'styles': [{'name': style_name, 'id': path} for style_name, path in v],
            }
            for k, v in hts_dic.items()
        ]
