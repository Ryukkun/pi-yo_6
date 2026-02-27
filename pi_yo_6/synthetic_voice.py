import asyncio

import aiohttp
import logging
from typing import Optional

from pi_yo_6.message_unit import MessageUnit

from .voicevox.core import CreateVoicevox, VoicevoxEngineBase
from .open_jtalk.core import CreateOpenJtalk

from config import Config


_log = logging.getLogger(__name__)







class SyntheticEngines:
    _session: Optional[aiohttp.ClientSession] = None
    def __init__(self) -> None:
        self.voicevox: Optional[CreateVoicevox] = None
        self.coeiroink: Optional[VoicevoxEngineBase] = None
        self.open_jtalk: Optional[CreateOpenJtalk] = None
    
    async def init_all(self):
        """gather を使って全エンジンを爆速で初期化する"""
        tasks = []

        if Config.VOICEVOX.enable:
            tasks.append(self._init_voicevox())
        if Config.Coeiroink.enable:
            tasks.append(self._init_coeiroink())
        if Config.OpenJtalk.enable:
            tasks.append(self._init_open_jtalk())
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
            engine: CreateVoicevox = CreateVoicevox(Config.VOICEVOX, session=session)
            
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
            self.coeiroink = engine
            _log.info('Loaded Coeiroink!!')
        except Exception as e:
            _log.warning(f'Coeiroink失敗: {e}')


    async def _init_open_jtalk(self) -> None:
        """Open JTalk専用の初期化タスク"""
        try:
            self.open_jtalk = CreateOpenJtalk()
            _log.info('Loaded Open_Jtalk!!')
        except Exception as e:
            _log.warning(f'Open JTalk失敗: {e}')



    async def create_voice(self, Itext:MessageUnit, out):
        _type = Itext.speaker.type

        if _type == 'open_jtalk':
            if not self.open_jtalk: return

            Itext.out_path = out
            if Itext.speed == None:
                Itext.speed = "1.2"

            if (tone := Itext.tone) != None:
                Itext.tone = f' -fm {tone}'

            if (intnation := Itext.intnation) != None:
                Itext.intnation = f' -jf {intnation}'

            if (a := Itext.a) != None:
                Itext.a = f' -a {a}'

            if Itext.out_path == None:
                Itext.out_path = f"{Config.output}output.wav"

            await self.open_jtalk.create_voice(Itext)



        elif _type == 'voicevox':
            if not self.voicevox: return

            speaker = Itext.speaker.id
            if (speaker := self.voicevox.to_speaker_id(speaker)) == None:
                return
            Itext.speaker.id = str(speaker)

            with open(out, 'wb')as f:
                f.write( await self.voicevox.create_voice(Itext))



        elif _type == 'coeiroink':
            if not self.coeiroink: return

            speaker = Itext.speaker.id
            if (speaker := self.coeiroink.to_speaker_id(speaker)) == None:
                return
            Itext.speaker.id = str(speaker)

            if Itext.speed == None:
                Itext.speed = 1.0
            if Itext.tone == None:
                Itext.tone = 0.0
            if Itext.intnation == None:
                Itext.intnation = 1.0

            with open(out, 'wb')as f:
                f.write( await self.coeiroink.create_voice(Itext))