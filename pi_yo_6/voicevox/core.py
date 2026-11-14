import asyncio
import logging
from typing import TYPE_CHECKING, Any, Optional, TypedDict
import aiohttp

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
    def __init__(self, config: "VOICEVOX_Engine_Config", session: aiohttp.ClientSession) -> None:
        self.config = config
        self.session = session

        # Load
        self.url_base = f'http://{self.config.ip}'
        self.metas: list[SpeakerMeta] = []

    async def initialize(self) -> None:
        await self._load_metas(f'{self.url_base}/speakers')

    async def _load_metas(self, url: str) -> None:
        """完全非同期でmetasを読み込む"""
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=2.0)) as res:
                if res.status != 200:
                    raise NoMetas(f'metasを読み込めません (Status: {res.status})')
                self.metas = await res.json()
        except (aiohttp.ClientConnectorError, asyncio.TimeoutError):
            _log.error(f"Engine ({url}) が見つかりませんでした。")
            raise ConnectionError('Engine が、見つかりませんでした！')

    async def create_voice(self, msg: "MessageUnit") -> bytes:
        """メッセージから音声データを作成

        Parameters
        ----------
        msg : MessageUnit
            メッセージ

        Returns
        -------
        bytes
            作成された音声データのbytesデータ
        """
        speaker = self.to_speaker_id(msg.voice)
        if speaker is None:
            _log.error(f"Speaker ID {msg.voice} not found.")
            return b''

        tlimit = self.config.text_limit
        # 文字数上限（元のmsg.textを破壊しない）
        text = msg.text[:tlimit] if len(msg.text) > tlimit else msg.text

        audio_query_url = f'{self.url_base}/audio_query'
        audio_query_params = {"text": text, "speaker": speaker}
        synthesis_url = f'{self.url_base}/synthesis'
        synthesis_params = {"speaker": speaker}

        # Audio Queryの取得
        async with self.session.post(audio_query_url, params=audio_query_params) as res:
            if res.status != 200:
                _log.error(f"audio_query failed with status {res.status}")
                return b''
            audio_query: AudioQuery = await res.json()

        if msg.voice.speed != 1.0:
            audio_query['speedScale'] = msg.voice.speed
        if msg.voice.tone != 0.0:
            # VOICEVOXのpitchScaleは±0.15前後が標準のため安全範囲にクランプ
            audio_query['pitchScale'] = max(-0.5, min(0.5, msg.voice.tone))
        if msg.voice.intonation != 0.0:
            audio_query['intonationScale'] = msg.voice.intonation

        headers = {
            'accept': 'audio/wav',
            'Content-Type': 'application/json',
        }
        async with self.session.post(
            url=synthesis_url, params=synthesis_params, json=audio_query, headers=headers
        ) as res:
            if res.status != 200:
                _log.error(f"synthesis failed with status {res.status}")
                return b''
            return await res.read()

    def name_list(self) -> list[list[str]]:
        res = []
        for name_dic in self.metas:
            name = name_dic['name']
            _res = [name]
            for style_dic in name_dic['styles']:
                style = style_dic['name']
                _res.append(f'{style}')
            res.append(_res)

        return res

    def to_speaker_id(self, voice: VoiceUnit) -> Optional[str | int]:
        for meta in self.metas:
            if meta['name'] == voice.name:
                for style in meta['styles']:
                    if style['name'] == voice.style:
                        return style['id']
        return None
