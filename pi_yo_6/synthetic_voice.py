import asyncio
import aiohttp
import logging
from typing import Optional

from pi_yo_6.message_unit import MessageUnit
from pi_yo_6.utils import ENGINE_TYPE, VoiceUnit
from pi_yo_6.voicevox.core import VoicevoxEngineBase
from pi_yo_6.open_jtalk.core import CreateOpenJtalk
from pi_yo_6.load_config import Config

_log = logging.getLogger(__name__)



class SyntheticEngines:
    _session: Optional[aiohttp.ClientSession] = None
    def __init__(self) -> None:
        """OpenJtalkは標準で読み込み"""
        self.open_jtalk: CreateOpenJtalk = CreateOpenJtalk()
        _log.info('Loaded Open_Jtalk!!')
        self.voicevox: Optional[VoicevoxEngineBase] = None
        self.coeiroink: Optional[VoicevoxEngineBase] = None
    
    async def init_all(self):
        """gather を使って全エンジンを爆速で初期化する"""
        tasks = []
        tasks.append(self.open_jtalk.run_test())
        if Config.VOICEVOX.enable:
            tasks.append(self._init_voicevox())
        if Config.Coeiroink.enable:
            tasks.append(self._init_coeiroink())
        if tasks:
            await asyncio.gather(*tasks)


    @staticmethod
    async def get_session() -> aiohttp.ClientSession:
        """セッションを使い回すためのゲッター"""
        if SyntheticEngines._session is None or SyntheticEngines._session.closed:
            SyntheticEngines._session = aiohttp.ClientSession()
        return SyntheticEngines._session

    @staticmethod
    async def close():
        """Bot終了時にセッションを閉じるためのメソッド"""
        if SyntheticEngines._session and not SyntheticEngines._session.closed:
            await SyntheticEngines._session.close()


    async def _init_voicevox(self) -> None:
        try:
            session = await self.get_session()
            engine: VoicevoxEngineBase = VoicevoxEngineBase(Config.VOICEVOX, session=session)
            
            async def check_ver():
                async with session.get(f'{engine.url_base}/core_versions', timeout=aiohttp.ClientTimeout(total=1.0)) as r:
                    ver = (await r.json())[0]
                async with session.get('https://api.github.com/repos/VOICEVOX/voicevox_core/releases/latest', timeout=aiohttp.ClientTimeout(total=1.5)) as r:
                    latest = (await r.json())['tag_name']
                    return ver, latest

            _, (ver, latest) = await asyncio.gather(
                engine.initialize(),
                check_ver()
            )
            _log.info(f'Loaded Voicevox!! - Ver.{ver}')
            self.voicevox = engine
            if ver == latest:
                _log.info(f'最新バージョンです')
            else:
                _log.warning(f'最新バージョンは {latest} です')
        except Exception as e:
            _log.warning(f'\033[0mVoiceVoxの読み込みに失敗しました。 : {e}')
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



    async def create_voice(self, msg:MessageUnit):
        _type = msg.voice.type

        if _type == ENGINE_TYPE.OPEN_JTALK and self.open_jtalk:
            await self.open_jtalk.create_voice(msg)

        elif _type == ENGINE_TYPE.VOICEVOX and self.voicevox:
            with open(msg.out_path, 'wb')as f:
                f.write( await self.voicevox.create_voice(msg))

        elif _type == ENGINE_TYPE.COEIROINK and self.coeiroink:
            with open(msg.out_path, 'wb')as f:
                f.write( await self.coeiroink.create_voice(msg))


    def is_available(self, voice:VoiceUnit) -> bool:
        if voice.type == ENGINE_TYPE.OPEN_JTALK:
            return self.open_jtalk.to_speaker_id(voice) != None
        elif voice.style == ENGINE_TYPE.VOICEVOX and self.voicevox:
            return self.voicevox.to_speaker_id(voice) != None
        elif voice.style == ENGINE_TYPE.COEIROINK and self.coeiroink:
            return self.coeiroink.to_speaker_id(voice) != None
        return False