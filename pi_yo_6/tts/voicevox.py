import io
import logging
from typing import Any, TypedDict

import aiohttp

from pi_yo_6.config import VoicevoxConfig
from pi_yo_6.models import NoMetasError, SpeakerMeta, VoiceSetting

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
    kana: str | None


class VoicevoxEngine:
    """VOICEVOX / Coeiroink 互換 HTTP API を利用する音声合成エンジン"""

    def __init__(self, config: VoicevoxConfig, session: aiohttp.ClientSession) -> None:
        self.config = config
        self.session = session
        self.url_base = f'http://{self.config.ip}'
        self.metas: list[SpeakerMeta] = []

    async def initialize(self) -> None:
        url = f'{self.url_base}/speakers'
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=2.0)) as res:
                if res.status != 200:
                    raise NoMetasError(f'metasを読み込めません (Status: {res.status})')
                self.metas = await res.json()
        except (TimeoutError, aiohttp.ClientConnectorError) as e:
            _log.error(f"Engine ({url}) が見つかりませんでした。")
            raise ConnectionError('Engine が、見つかりませんでした！') from e

    async def synthesize(self, text: str, voice: VoiceSetting) -> io.BytesIO | None:
        speaker = self.to_speaker_id(voice)
        if speaker is None:
            _log.error(f"Speaker ID {voice} not found.")
            return None

        tlimit = self.config.text_limit
        target_text = text[:tlimit] if len(text) > tlimit else text

        audio_query_url = f'{self.url_base}/audio_query'
        synthesis_url = f'{self.url_base}/synthesis'

        async with self.session.post(
            audio_query_url, params={"text": target_text, "speaker": speaker}
        ) as res:
            if res.status != 200:
                _log.error(f"audio_query failed with status {res.status}")
                return None
            audio_query: AudioQuery = await res.json()

        if voice.speed != 1.0:
            audio_query['speedScale'] = voice.speed
        if voice.tone != 0.0:
            audio_query['pitchScale'] = max(-0.5, min(0.5, voice.tone))
        if voice.intonation != 0.0:
            audio_query['intonationScale'] = voice.intonation

        headers = {
            'accept': 'audio/wav',
            'Content-Type': 'application/json',
        }
        async with self.session.post(
            url=synthesis_url,
            params={"speaker": speaker},
            json=audio_query,
            headers=headers,
        ) as res:
            if res.status != 200:
                _log.error(f"synthesis failed with status {res.status}")
                return None
            raw = await res.read()
            if not raw:
                return None
            buf = io.BytesIO(raw)
            buf.seek(0)
            return buf

    def to_speaker_id(self, voice: VoiceSetting) -> str | int | None:
        for meta in self.metas:
            if meta['name'] == voice.name:
                for style in meta['styles']:
                    if style['name'] == voice.style:
                        return style['id']
        return None
