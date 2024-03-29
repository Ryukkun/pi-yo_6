from ctypes import cdll, c_char_p
import aiohttp
import urllib.parse
import json
import requests

from ..template._config import VOICEVOX as config_voicevox
from ..utils import MessageUnit, NoMetas







class VoicevoxEngineBase:
    def __init__(self, config:config_voicevox) -> None:
        self.config = config

        # Load
        self.url_base = f'http://{config.ip}'

        self._load_metas(f'{self.url_base}/speakers')
    


    def _load_metas(self, url):
        try:
            res = requests.get(url, timeout=1.0)
        except requests.ConnectionError:
            raise requests.ConnectionError(f'Engine が、見つかりませんでした！')
        if res.status_code != requests.codes.ok:
            raise NoMetas(f'metasを読み込めません')
        self.metas = res.json()


    async def create_voice(self, Itext:MessageUnit):
        text = Itext.text
        speaker = Itext.speaker
        tlimit = self.config.text_limit
        # 文字数上限
        if len(text) > tlimit:
            text = text[:tlimit]

        url_audio_query = fr'{self.url_base}/audio_query?text={urllib.parse.quote(text)}&speaker={speaker}'
        url_synthesis = fr'{self.url_base}/synthesis?speaker={speaker}'

        async with aiohttp.ClientSession() as session:
            res = await session.post(url_audio_query)
            audio_query = await res.text()

            headers = {
                'accept': 'audio/wav',
                'Content-Type': 'application/json',
                }
            res = await session.post(url=url_synthesis, data=audio_query, headers=headers)
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
    def _load_metas(self, url):
        try: 
            super()._load_metas(url)
        except NoMetas:
            try:
                lib = cdll.LoadLibrary(self.config.core_path)
                lib.metas.restype = c_char_p
                self.metas = json.loads(lib.metas().decode())
            except:
                raise NoMetas('metasを読み込めません')