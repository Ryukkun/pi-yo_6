import logging
from typing import Optional

from pi_yo_6.voicevox.core import CreateVOICEVOX
from pi_yo_6.coeiroink.core import CreateCoeiroink
from pi_yo_6.open_jtalk.core import CreateOpenJtalk
from config import Config


_log = logging.getLogger(__name__)

class SyntheticEngines:
    def __init__(self) -> None:


        try:
            self.voicevox = None
            if Config.Vvox.enable:
                self.voicevox: Optional[CreateVOICEVOX] = CreateVOICEVOX()
        except Exception as e:
            _log.warning(f'\033[0mVoiceVoxの読み込みに失敗しました。\n{e}')
            self.voicevox = None

        try:
            self.coeiroink = None
            if Config.Coeiroink.enable:
                self.coeiroink: Optional[CreateCoeiroink] = CreateCoeiroink()
                if not self.coeiroink.metas:
                    self.coeiroink = None
                    _log.warning('Coeiroink 再生可能な speaker_model が存在しません')
        except Exception as e:
            _log.warning(f'\033[0mCoeiroinkの読み込みに失敗しました。\n{e}')
            self.coeiroink = None

        try:
            self.open_jtalk = None
            if Config.OJ.enable:
                self.open_jtalk = CreateOpenJtalk()
                if not self.open_jtalk.metas:
                    raise Exception('再生可能な htsvoice が存在しません')
        except Exception as e:
            _log.warning(f'Open Jtakの読み込みに失敗 : {e}')
            self.open_jtalk = None


    async def create_voice(self, Itext:dict, out):
        _type = Itext['speaker']['type']

        if _type == 'open_jtalk':
            if not self.open_jtalk: return

            Itext['out'] = out
            Itext['speaker'] = Itext['speaker']['id']
            Itext['speed'] = Itext.get('speed',1.2)
            if tone := Itext.get('tone',''):
                Itext['tone'] = f' -fm {tone}'
            if intnation := Itext.get('intnation',''):
                Itext['intnation'] = f' -jf {intnation}'
            if a := Itext.get('a',''):
                Itext['a'] = f' -a {a}'

            await self.open_jtalk.create_voice(**Itext)


        elif _type == 'voicevox':
            if not self.voicevox: return

            speaker = Itext['speaker']['id']
            if (speaker := self.voicevox.to_speaker_id(speaker)) == None:
                return
            Itext['speaker'] = speaker

            with open(out, 'wb')as f:
                f.write( await self.voicevox.create_voice(Itext['text'], speaker))


        elif _type == 'coeiroink':
            if not self.coeiroink: return

            speaker = Itext['speaker']['id']
            Itext['out'] = out
            if (speaker := self.coeiroink.to_speaker_id(speaker)) == None:
                return
            Itext['speaker'] = speaker

            await self.coeiroink.create_voice(**Itext)

