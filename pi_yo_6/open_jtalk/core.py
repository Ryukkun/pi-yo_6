import atexit
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager, ExitStack
from importlib.resources import as_file
import io
import logging
import os
import asyncio
import wave

from pathlib import Path
from glob import glob
from platform import system
from typing import TYPE_CHECKING, Callable, Optional

import pyopenjtalk
from pyopenjtalk.htsengine import HTSEngine

import numpy as np
import scipy.io
from pi_yo_6.load_config import Config
from pi_yo_6.utils import ENGINE_TYPE, NoMetas, SpeakerMeta, VoiceUnit


if TYPE_CHECKING:
    from pi_yo_6.message_unit import MessageUnit


_os = system().lower()
if _os == 'windows':
    EFormat = 'shift_jis'
else:
    EFormat = 'utf-8'


_log = logging.getLogger(__name__)


class CreateOpenJtalk:
    exe = ThreadPoolExecutor()
    def __init__(self) -> None:
        self.hts_folder = Config.OpenJtalk.hts_path
        self.metas = self.get_metas()
        if not self.metas:
            raise NoMetas('再生可能な htsvoice が存在しません')
        
        self.hts:dict[str, Callable[[], AbstractContextManager[HTSEngine]]] = {}
        for meta in self.metas:
            for style in meta['styles']:
                path = style['id']
                _file = ExitStack()
                atexit.register(_file.close)
                voice = str(_file.enter_context(as_file(Path(path)))).encode("utf-8")
                self.hts[path] = pyopenjtalk._global_instance_manager(lambda v=voice: HTSEngine(v))
        

    async def run_test(self):
        data = await self.create_voice('テスト', VoiceUnit(ENGINE_TYPE.OPEN_JTALK ,name=self.metas[0]['name'], style=self.metas[0]['styles'][0]['name']))
        if data.getbuffer().nbytes == 0:
            raise Exception('Open Jtalkの動作確認に失敗しました。htsvoiceのパスや、辞書のパスが正しいか確認してください。')


    async def generate_voice(self, msg:str, hts_id:str, speed:float=1.2, tone:float=0.0) -> tuple[np.typing.NDArray[np.float64], int]:
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
        def block():
            with hts() as htsengine:
                sr = htsengine.get_sampling_frequency()
                htsengine.set_speed(speed)
                htsengine.add_half_tone(tone)
                return htsengine.synthesize(labels), sr
            
        return await asyncio.get_event_loop().run_in_executor(self.exe, block)


    async def create_voice(self, msg: "str|MessageUnit", _voice: Optional[VoiceUnit] = None) -> io.BytesIO:
        buffer = io.BytesIO()
        if isinstance(msg, str):
            if _voice == None:
                _log.error('Invalid arguments for create_voice')
                return buffer
            else:
                voice = _voice
        else:
            voice = msg.voice
            msg = msg.text


        speaker_path = self.to_speaker_id(voice)
        if speaker_path == None: speaker_path = self.metas[0]['styles'][0]['id'] # デフォルトは最初のhtsvoice

        data, sr = await self.generate_voice(msg, speaker_path, speed=voice.speed, tone=voice.tone)
        max_val = np.abs(data).max()
        if max_val > 0:
            data = data / max_val
        scipy.io.wavfile.write(buffer, sr, data)
        return buffer


    def to_speaker_id(self, voice:VoiceUnit) -> Optional[str]:
        res = None
        for meta in self.metas:
            if meta['name'] == voice.name:
                styles = meta['styles']
                for style in styles:
                    if style['name'] == voice.style:
                        res = style['id']
        return res


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
        hts_list = [(_, os.path.split(_)[-1].replace('.htsvoice','')) for _ in glob(str( Config.OpenJtalk.hts_path / '*.htsvoice'))]
        hts_dic:dict[str, list[tuple[str, str]]] = {}
        for path, hts_name in hts_list:  # hts_nameに拡張子は含まれない
            hts_split = hts_name.split('_')
            hts_author = hts_split[0] if len(hts_split) >= 1 else hts_name
            style_name = "_".join(hts_split[1:]) if len(hts_split) >= 2 else hts_author
            if not hts_dic.get(hts_author): hts_dic[hts_author] = []
            hts_dic[hts_author].append((style_name, path))
        return [
            {
                'name':k,
                'styles':[
                    {'name': style_name, 'id': path} for style_name, path in v
                ]
            } for k, v in hts_dic.items()
        ]


    def __playable_wav(self, path:Path) -> bool:
        if not (path.is_file() and path.suffix.lower() == '.wav'):
            return False
        
        size = os.path.getsize(path)
        # 一般的なWAVヘッダーは約44バイトなので、それ以下なら確実にデータがありません
        if size <= 44:
            return False
        
        try:
            with wave.open(str(path.resolve()), 'rb') as f:
                # 基本情報を取得（チャンネル数、サンプルサイズ、サンプリングレート、フレーム数）
                # フレーム数が0なら、中身が空（無音ではなくデータ自体がない）
                if f.getparams().nframes == 0:
                    return False
                return True
        except Exception as e:
            return False