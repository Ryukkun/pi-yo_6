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

    _SYNTH_TIMEOUT = aiohttp.ClientTimeout(total=15.0)
    _WARMUP_TIMEOUT = aiohttp.ClientTimeout(total=5.0)

    def __init__(self, config: VoicevoxConfig, session: aiohttp.ClientSession) -> None:
        self.config = config
        self.session = session
        self.url_base = f'http://{self.config.ip}'
        self.metas: list[SpeakerMeta] = []
        self._speaker_map: dict[tuple[str, str], str | int] = {}
        self._use_cancellable = True

    async def initialize(self) -> None:
        url = f'{self.url_base}/speakers'
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=2.0)) as res:
                if res.status != 200:
                    raise NoMetasError(f'metasを読み込めません (Status: {res.status})')
                self.metas = await res.json()
                self._speaker_map = {
                    (meta['name'], style['name']): style['id']
                    for meta in self.metas
                    for style in meta['styles']
                }
        except (TimeoutError, aiohttp.ClientConnectorError) as e:
            raise ConnectionError(f'Engine ({url}) が見つかりませんでした。') from e

    async def warmup_speaker(self, voice: VoiceSetting) -> None:
        """話者モデルを事前ロードして初回合成の遅延を抑える"""
        speaker = self.to_speaker_id(voice)
        if speaker is None:
            return
        try:
            async with self.session.post(
                f'{self.url_base}/initialize_speaker',
                params={"speaker": speaker, "skip_reinit": "true"},
                timeout=self._WARMUP_TIMEOUT,
            ):
                pass
        except Exception:
            pass

    async def synthesize(self, text: str, voice: VoiceSetting) -> io.BytesIO | None:
        speaker = self.to_speaker_id(voice)
        if speaker is None:
            _log.error(f"Speaker ID {voice} not found.")
            return None

        tlimit = self.config.text_limit
        target_text = text[:tlimit] if len(text) > tlimit else text

        audio_query_url = f'{self.url_base}/audio_query'

        async with self.session.post(
            audio_query_url,
            params={"text": target_text, "speaker": speaker},
            timeout=self._SYNTH_TIMEOUT,
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
        audio_query['outputSamplingRate'] = 48000
        audio_query['outputStereo'] = True
        audio_query['prePhonemeLength'] = min(audio_query.get('prePhonemeLength', 0.1), 0.03)
        audio_query['postPhonemeLength'] = min(audio_query.get('postPhonemeLength', 0.1), 0.03)

        headers = {
            'accept': 'audio/wav',
            'Content-Type': 'application/json',
        }
        raw = await self._request_synthesis(speaker, audio_query, headers)
        if not raw:
            return None
        buf = io.BytesIO(raw)
        buf.seek(0)
        return buf

    async def _request_synthesis(
        self,
        speaker: str | int,
        audio_query: AudioQuery,
        headers: dict[str, str],
    ) -> bytes | None:
        if self._use_cancellable:
            async with self.session.post(
                url=f'{self.url_base}/cancellable_synthesis',
                params={"speaker": speaker},
                json=audio_query,
                headers=headers,
                timeout=self._SYNTH_TIMEOUT,
            ) as res:
                if res.status == 200:
                    return await res.read()
                if res.status != 404:
                    _log.error(f"cancellable_synthesis failed with status {res.status}")
                    return None
                self._use_cancellable = False

        async with self.session.post(
            url=f'{self.url_base}/synthesis',
            params={"speaker": speaker},
            json=audio_query,
            headers=headers,
            timeout=self._SYNTH_TIMEOUT,
        ) as res:
            if res.status != 200:
                _log.error(f"synthesis failed with status {res.status}")
                return None
            return await res.read()

    def to_speaker_id(self, voice: VoiceSetting) -> str | int | None:
        return self._speaker_map.get((voice.name, voice.style))
