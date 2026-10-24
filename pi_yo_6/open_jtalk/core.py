import asyncio
import atexit
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager, ExitStack
from importlib.resources import as_file
import io
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

import numpy as np
import pyopenjtalk
from pyopenjtalk.htsengine import HTSEngine
import scipy.io

from pi_yo_6.load_config import Config
from pi_yo_6.utils import ENGINE_TYPE, NoMetas, SpeakerMeta, VoiceUnit

if TYPE_CHECKING:
    from pi_yo_6.message_unit import MessageUnit

_log = logging.getLogger(__name__)


class CreateOpenJtalk:
    exe = ThreadPoolExecutor()

    def __init__(self) -> None:
        self.hts_folder = Config.OpenJtalk.hts_path
        self.metas = self.get_metas()
        if not self.metas:
            raise NoMetas('再生可能な htsvoice が存在しません')

        self.hts: dict[str, Callable[[], AbstractContextManager[HTSEngine]]] = {}
        for meta in self.metas:
            for style in meta['styles']:
                path = style['id']
                _file = ExitStack()
                atexit.register(_file.close)
                voice = str(_file.enter_context(as_file(Path(path)))).encode("utf-8")
                self.hts[path] = pyopenjtalk._global_instance_manager(lambda v=voice: HTSEngine(v))

    async def run_test(self) -> None:
        default_voice = VoiceUnit(
            type=ENGINE_TYPE.OPEN_JTALK,
            name=self.metas[0]['name'],
            style=self.metas[0]['styles'][0]['name'],
        )
        data = await self.create_voice('テスト', default_voice)
        if data.getbuffer().nbytes == 0:
            raise RuntimeError(
                'Open Jtalkの動作確認に失敗しました。htsvoiceのパスや、辞書のパスが正しいか確認してください。'
            )

    async def generate_voice(
        self, msg: str, hts_id: str, speed: float = 1.2, tone: float = 0.0
    ) -> tuple[np.typing.NDArray[np.float64], int]:
        """Run OpenJTalk's speech synthesis backend

        Args:
            speed (float): speech speed rate. Default is 1.2.
            tone (float): additional half-tone. Default is 0.

        Returns:
            np.ndarray: speech waveform (dtype: np.float64)
            int: sampling frequency (defualt: 48000)
        """
        labels = pyopenjtalk.extract_fullcontext(msg)
        if isinstance(labels, tuple) and len(labels) == 2:
            labels = labels[1]

        hts = self.hts[hts_id]

        def block() -> tuple[np.typing.NDArray[np.float64], int]:
            with hts() as htsengine:
                sr = htsengine.get_sampling_frequency()
                htsengine.set_speed(speed)
                htsengine.add_half_tone(tone)
                return htsengine.synthesize(labels), sr

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.exe, block)

    async def create_voice(
        self, msg: "str | MessageUnit", _voice: Optional[VoiceUnit] = None
    ) -> io.BytesIO:
        buffer = io.BytesIO()
        if isinstance(msg, str):
            if _voice is None:
                _log.error('Invalid arguments for create_voice')
                return buffer
            voice = _voice
            text = msg
        else:
            voice = msg.voice
            text = msg.text

        speaker_path = self.to_speaker_id(voice)
        if speaker_path is None:
            speaker_path = self.metas[0]['styles'][0]['id']  # デフォルトは最初のhtsvoice

        data, sr = await self.generate_voice(text, speaker_path, speed=voice.speed, tone=voice.tone)
        max_val = np.abs(data).max()
        if max_val > 0:
            data = data / max_val / 6
        scipy.io.wavfile.write(buffer, sr, data)
        buffer.seek(0)
        return buffer

    def to_speaker_id(self, voice: VoiceUnit) -> Optional[str]:
        for meta in self.metas:
            if meta['name'] == voice.name:
                for style in meta['styles']:
                    if style['name'] == voice.style:
                        return style['id']
        return None

    def get_metas(self) -> list[SpeakerMeta]:
        """stylesのnameに拡張子は含まれない、 idはファイルパス
        例 :
        {
            "name": "mei",
            "styles": [
                {
                    "name": "normal",
                    "id": "C:/htsvoice/mei_normal.htsvoice"
                },
                ...]
        }
        Returns
        -------
        list[SpeakerMeta]
            metas
        """
        hts_dic: dict[str, list[tuple[str, str]]] = {}
        for path in sorted(self.hts_folder.glob('*.htsvoice')):
            hts_name = path.stem  # hts_nameに拡張子は含まれない
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
