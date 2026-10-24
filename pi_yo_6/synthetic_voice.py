import asyncio
import io
import logging
from typing import TYPE_CHECKING, Optional
import aiohttp

from pi_yo_6.load_config import Config
from pi_yo_6.open_jtalk.core import CreateOpenJtalk
from pi_yo_6.utils import ENGINE_TYPE, VoiceUnit
from pi_yo_6.voicevox.core import VoicevoxEngineBase

if TYPE_CHECKING:
    from pi_yo_6.message_unit import MessageUnit

_log = logging.getLogger(__name__)


class SyntheticEngines:
    current: "SyntheticEngines"
    _session: Optional[aiohttp.ClientSession] = None

    def __init__(self) -> None:
        """OpenJtalkは標準で読み込み"""
        self.open_jtalk: CreateOpenJtalk = CreateOpenJtalk()
        _log.info('Loaded Open_Jtalk!!')
        self.voicevox: Optional[VoicevoxEngineBase] = None
        self.coeiroink: Optional[VoicevoxEngineBase] = None

    async def init_all(self) -> None:
        """gather を使って全エンジンを爆速で初期化する"""
        tasks = [self.open_jtalk.run_test()]
        if Config.VOICEVOX.enable:
            tasks.append(self._init_voicevox())
        if Config.Coeiroink.enable:
            tasks.append(self._init_coeiroink())
        if tasks:
            await asyncio.gather(*tasks)
        SyntheticEngines.current = self

    async def reload_unloaded_engines(self) -> list[str]:
        """未読み込みのVOICEVOX / Coeiroinkエンジンの再接続を試行"""
        reloaded: list[str] = []
        if Config.VOICEVOX.enable and self.voicevox is None:
            await self._init_voicevox()
            if self.voicevox is not None:
                reloaded.append('VOICEVOX')
        if Config.Coeiroink.enable and self.coeiroink is None:
            await self._init_coeiroink()
            if self.coeiroink is not None:
                reloaded.append('Coeiroink')
        return reloaded

    def find_voice(self, name: str, style: str | None = None) -> VoiceUnit | None:
        """指定された名前とスタイルを持つVoiceUnitを検索"""
        name_lower = name.lower()
        # 1. OpenJTalk
        if self.open_jtalk:
            for meta in self.open_jtalk.metas:
                if meta['name'].lower() == name_lower:
                    matched_style = style or meta['styles'][0]['name']
                    for s in meta['styles']:
                        if s['name'].lower() == (style or '').lower():
                            matched_style = s['name']
                            break
                    return VoiceUnit(
                        type=ENGINE_TYPE.OPEN_JTALK,
                        name=meta['name'],
                        style=matched_style,
                    )
        # 2. VOICEVOX
        if self.voicevox:
            for meta in self.voicevox.metas:
                if meta['name'].lower() == name_lower:
                    matched_style = style or meta['styles'][0]['name']
                    for s in meta['styles']:
                        if s['name'].lower() == (style or '').lower():
                            matched_style = s['name']
                            break
                    return VoiceUnit(
                        type=ENGINE_TYPE.VOICEVOX,
                        name=meta['name'],
                        style=matched_style,
                    )
        # 3. Coeiroink
        if self.coeiroink:
            for meta in self.coeiroink.metas:
                if meta['name'].lower() == name_lower:
                    matched_style = style or meta['styles'][0]['name']
                    for s in meta['styles']:
                        if s['name'].lower() == (style or '').lower():
                            matched_style = s['name']
                            break
                    return VoiceUnit(
                        type=ENGINE_TYPE.COEIROINK,
                        name=meta['name'],
                        style=matched_style,
                    )
        return None

    @staticmethod
    async def get_session() -> aiohttp.ClientSession:
        """セッションを使い回すためのゲッター"""
        if SyntheticEngines._session is None or SyntheticEngines._session.closed:
            SyntheticEngines._session = aiohttp.ClientSession()
        return SyntheticEngines._session

    @staticmethod
    async def close() -> None:
        """Bot終了時にセッションを閉じるためのメソッド"""
        if SyntheticEngines._session and not SyntheticEngines._session.closed:
            await SyntheticEngines._session.close()

    async def _init_voicevox(self) -> None:
        try:
            session = await self.get_session()
            engine: VoicevoxEngineBase = VoicevoxEngineBase(Config.VOICEVOX, session=session)

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
        """Coeiroink専用の初期化タスク"""
        try:
            session = await self.get_session()
            engine = VoicevoxEngineBase(Config.Coeiroink, session=session)
            await engine.initialize()
            _log.info('Loaded Coeiroink!!')
            self.coeiroink = engine
        except Exception as e:
            _log.warning(f'Coeiroink失敗: {e}')
            self.coeiroink = None

    async def create_voice(self, msg: "MessageUnit") -> None:
        _type = msg.voice.type
        if _type == ENGINE_TYPE.OPEN_JTALK and self.open_jtalk:
            msg.data = await self.open_jtalk.create_voice(msg)
        elif _type == ENGINE_TYPE.VOICEVOX and self.voicevox:
            raw = await self.voicevox.create_voice(msg)
            if raw:
                msg.data = io.BytesIO(raw)
        elif _type == ENGINE_TYPE.COEIROINK and self.coeiroink:
            raw = await self.coeiroink.create_voice(msg)
            if raw:
                msg.data = io.BytesIO(raw)
        else:
            return

        if msg.data is not None:
            msg.data.seek(0)

    def is_available(self, voice: VoiceUnit) -> bool:
        if voice.type == ENGINE_TYPE.OPEN_JTALK and self.open_jtalk:
            return self.open_jtalk.to_speaker_id(voice) is not None
        elif voice.type == ENGINE_TYPE.VOICEVOX and self.voicevox:
            return self.voicevox.to_speaker_id(voice) is not None
        elif voice.type == ENGINE_TYPE.COEIROINK and self.coeiroink:
            return self.coeiroink.to_speaker_id(voice) is not None
        return False
