import asyncio
from typing import TYPE_CHECKING, Any, Optional, TypedDict
import aiohttp
import logging


from ..utils import NoMetas, SpeakerMeta, VoiceUnit

if TYPE_CHECKING:
    from pi_yo_6.load_config import VOICEVOX_Engine_Config
    from pi_yo_6.message_unit import MessageUnit



_log = logging.getLogger(__name__)



class AudioQuery(TypedDict):
    accent_phrases: list[Any]
    speedScale: float
    pitchScale: float
    intonationScale: float
    volumeScale: float
    prePhonemeLength: float
    postPhonemeLength: float
    outputSamplingRate: int
    outputStereo: bool
    kana: Optional[str]



class VoicevoxEngineBase:
    def __init__(self, config:"VOICEVOX_Engine_Config", session: aiohttp.ClientSession) -> None:
        self.config = config
        self.session = session

        # Load
        self.url_base = f'http://{self.config.ip}'
        self.metas: list[SpeakerMeta] = []
        # セッションを保持するための変数（後で作成）
        

    async def initialize(self):
        await self._load_metas(f'{self.url_base}/speakers')


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


    async def create_voice(self, msg:"MessageUnit") -> bytes:
        """メッセージから音声データを作成

        Parameters
        ----------
        Itext : MessageUnit
            メッセージ

        Returns
        -------
        bytes
            作成された音声データのbytesデータ
        """
        if (speaker := self.to_speaker_id(msg.voice)) == None:
            _log.error(f"Speaker ID {msg.voice} not found.")
            return b''
        tlimit = self.config.text_limit
        # 文字数上限
        if len(msg.text) > tlimit:
            msg.text = msg.text[:tlimit]

        audio_query_url = fr'{self.url_base}/audio_query'
        audio_query_params = {"text":msg.text, "speaker":speaker}
        synthesis_url = fr'{self.url_base}/synthesis'
        synthesis_params = {"speaker":speaker}

        # Audio Queryの取得
        async with self.session.post(audio_query_url, params=audio_query_params) as res:
            audio_query: AudioQuery = await res.json()

        if msg.voice.speed != 1.0:
            audio_query['speedScale'] = msg.voice.speed
        if msg.voice.tone != 0.0:
            audio_query['pitchScale'] = msg.voice.tone
        if msg.voice.intnation != 0.0:
            audio_query['intonationScale'] = msg.voice.intnation

        headers = {
            'accept': 'audio/wav',
            'Content-Type': 'application/json',
            }
        async with self.session.post(url=synthesis_url, params=synthesis_params, json=audio_query, headers=headers) as res:
            return await res.read()


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


    def to_speaker_id(self, voice:VoiceUnit) -> Optional[str]:
        res = None
        for meta in self.metas:
            if meta['name'] == voice.name:
                styles = meta['styles']
                for style in styles:
                    if style['name'] == voice.style:
                        res = style['id']
        return res