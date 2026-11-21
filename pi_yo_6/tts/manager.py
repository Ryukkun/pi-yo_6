import asyncio
import io
import logging

import aiohttp

from pi_yo_6.config import app_config
from pi_yo_6.models import EngineType, VoiceSetting
from pi_yo_6.tts.base import TTSEngine
from pi_yo_6.tts.open_jtalk import OpenJTalkEngine
from pi_yo_6.tts.voicevox import VoicevoxEngine

_log = logging.getLogger(__name__)


class TTSManager:
    """全音声合成エンジンのライフサイクルとルーティングを管理する"""

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self.open_jtalk: OpenJTalkEngine = OpenJTalkEngine()
        _log.info('Loaded Open_Jtalk!!')
        self.voicevox: VoicevoxEngine | None = None
        self.coeiroink: VoicevoxEngine | None = None

    async def init_all(self) -> None:
        """有効な全エンジンを並列で初期化する"""
        tasks = [self.open_jtalk.run_test()]
        if app_config.VOICEVOX.enable:
            tasks.append(self._init_voicevox())
        if app_config.Coeiroink.enable:
            tasks.append(self._init_coeiroink())
        await asyncio.gather(*tasks)

    async def reload_unloaded_engines(self) -> list[str]:
        """未読み込みのVOICEVOX / Coeiroinkエンジンの再接続を試行"""
        reloaded: list[str] = []
        if app_config.VOICEVOX.enable and self.voicevox is None:
            await self._init_voicevox()
            if self.voicevox is not None:
                reloaded.append('VOICEVOX')
        if app_config.Coeiroink.enable and self.coeiroink is None:
            await self._init_coeiroink()
            if self.coeiroink is not None:
                reloaded.append('Coeiroink')
        return reloaded

    def get_engine(self, engine_type: EngineType) -> TTSEngine | None:
        if engine_type == EngineType.OPEN_JTALK:
            return self.open_jtalk
        if engine_type == EngineType.VOICEVOX:
            return self.voicevox
        if engine_type == EngineType.COEIROINK:
            return self.coeiroink
        return None

    def find_voice(self, name: str, style: str | None = None) -> VoiceSetting | None:
        """指定された名前とスタイルを持つVoiceSettingを検索"""
        name_lower = name.lower()
        style_lower = (style or '').lower()
        for engine_type in (EngineType.OPEN_JTALK, EngineType.VOICEVOX, EngineType.COEIROINK):
            engine = self.get_engine(engine_type)
            if not engine:
                continue
            for meta in engine.metas:
                if meta['name'].lower() == name_lower:
                    matched_style = style or meta['styles'][0]['name']
                    for s in meta['styles']:
                        if s['name'].lower() == style_lower:
                            matched_style = s['name']
                            break
                    return VoiceSetting(
                        type=engine_type,
                        name=meta['name'],
                        style=matched_style,
                    )
        return None

    async def synthesize(self, text: str, voice: VoiceSetting) -> io.BytesIO | None:
        if not text.strip():
            return None
        engine = self.get_engine(voice.type)
        if not engine:
            return None
        data = await engine.synthesize(text, voice)
        if data is not None:
            data.seek(0)
        return data

    def is_available(self, voice: VoiceSetting) -> bool:
        engine = self.get_engine(voice.type)
        if not engine:
            return False
        return engine.to_speaker_id(voice) is not None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _init_voicevox(self) -> None:
        try:
            session = await self._get_session()
            engine = VoicevoxEngine(app_config.VOICEVOX, session=session)

            async def check_ver() -> tuple[str, str]:
                async with session.get(
                    f'{engine.url_base}/core_versions', timeout=aiohttp.ClientTimeout(total=1.0)
                ) as r:
                    ver = (await r.json())[0]
                async with session.get(
                    'https://api.github.com/repos/VOICEVOX/voicevox_core/releases/latest',
                    timeout=aiohttp.ClientTimeout(total=1.5),
                ) as r:
                    latest = (await r.json())['tag_name']
                    return ver, latest

            _, (ver, latest) = await asyncio.gather(engine.initialize(), check_ver())
            _log.info(f'Loaded Voicevox!! - Ver.{ver}')
            self.voicevox = engine
            if ver == latest:
                _log.info('最新バージョンです')
            else:
                _log.warning(f'最新バージョンは {latest} です')
        except Exception as e:
            _log.warning(f'VoiceVoxの読み込みに失敗しました。 : {e}')
            self.voicevox = None

    async def _init_coeiroink(self) -> None:
        try:
            session = await self._get_session()
            engine = VoicevoxEngine(app_config.Coeiroink, session=session)
            await engine.initialize()
            _log.info('Loaded Coeiroink!!')
            self.coeiroink = engine
        except Exception as e:
            _log.warning(f'Coeiroink失敗: {e}')
            self.coeiroink = None
