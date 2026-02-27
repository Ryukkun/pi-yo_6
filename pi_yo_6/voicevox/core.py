import asyncio
from ctypes import cdll, c_char_p
import stat
from typing import TYPE_CHECKING, Any, Optional
import aiohttp
import json
import logging

from pi_yo_6.message_unit import MessageUnit

from ..utils import NoMetas

if TYPE_CHECKING:
    from pi_yo_6.config import VOICEVOX_Engine_Config



_log = logging.getLogger(__name__)


class VoicevoxEngineBase:
    def __init__(self, config:VOICEVOX_Engine_Config, session: aiohttp.ClientSession) -> None:
        self.config = config
        self.session = session

        # Load
        self.url_base = f'http://{self.config.ip}'
        self.metas: list[dict[str, Any]] = []
        # セッションを保持するための変数（後で作成）
        

    async def initialize(self):
        await self._load_metas(f'{self.url_base}/metas')


    async def _load_metas(self, url):
        """完全非同期でmetasを読み込む"""
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=2.0)) as res:
                if res.status != 200:
                    raise NoMetas(f'metasを読み込めません (Status: {res.status})')
                self.metas = await res.json()
        except (aiohttp.ClientConnectorError, asyncio.TimeoutError):
            _log.error(f"Engine ({url}) が見つかりませんでした。")
            raise ConnectionError(f'Engine が、見つかりませんでした！')


    async def create_voice(self, Itext:MessageUnit) -> bytes:
        text = Itext.text
        speaker = Itext.speaker.id
        tlimit = self.config.text_limit
        # 文字数上限
        if len(text) > tlimit:
            text = text[:tlimit]

        audio_query_url = fr'{self.url_base}/audio_query'
        audio_query_params = {"text":text, "speaker":speaker}
        synthesis_url = fr'{self.url_base}/synthesis'
        synthesis_params = {"speaker":speaker}

        # Audio Queryの取得
        async with self.session.post(audio_query_url, params=audio_query_params) as res:
            audio_query = await res.text()

        headers = {
            'accept': 'audio/wav',
            'Content-Type': 'application/json',
            }
        async with self.session.post(url=synthesis_url, params=synthesis_params, data=audio_query, headers=headers) as res:
            res = await res.read()
        return res


    def name_list(self):
        res = []
        for name_dic in self.metas:
            name = name_dic['name']
            _res = [name]
            for style_dic in name_dic['styles']:
                style = style_dic['name']
                id = style_dic['id']
                _res.append(f'{style}')
            res.append(_res)

        return res


    def to_speaker_id(self, hts):
        try: hts = int(hts)
        except Exception: pass
        else:
            for meta in self.metas:
                for style in meta['styles']:
                    if style['id'] == hts:
                        return hts
            return
        
        res = None
        hts = hts.lower()
        for meta in self.metas:
            if meta['name'].lower() in hts:
                styles = meta['styles']
                for style in styles:
                    if style['name'].lower() in hts:
                        res = style['id']
                if type(res) != int:
                    res = styles[0]['id']
                break
        return res




class CreateVoicevox(VoicevoxEngineBase):
    async def _load_metas(self, url):
        try: 
            await super()._load_metas(url)
        except NoMetas:
            try:
                lib = cdll.LoadLibrary(self.config.core_path)
                lib.metas.restype = c_char_p
                self.metas = json.loads(lib.metas().decode())
            except:
                raise NoMetas('metasを読み込めません(HTTP/Core両方失敗)')