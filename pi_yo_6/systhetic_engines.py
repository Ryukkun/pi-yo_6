import asyncio
from platform import system
from typing import Optional

from pi_yo_6.voicevox.core import CreateVOICEVOX
from pi_yo_6.coeiroink.core import CreateCoeiroink
from config import Config

_os = system().lower()
if _os == 'windows':
    EFormat = 'shift_jis'
else:
    EFormat = 'utf-8'


class SyntheticEngines:
    def __init__(self) -> None:


        try:
            self.voicevox: Optional[CreateVOICEVOX] = CreateVOICEVOX()
        except Exception as e:
            print(f'\033[31m Error \033[35mpi-yo6 \033[0mVoiceVoxの読み込みに失敗しました。\n{e}')
            self.voicevox = None

        try:
            self.coeiroink: Optional[CreateCoeiroink] = CreateCoeiroink()
            if not self.coeiroink.metas:
                self.coeiroink = None
                print('Error pi-yo6 再生可能な speaker_model が存在しません')
        except Exception as e:
            print(f'\033[31m Error \033[35mpi-yo6 \033[0mCoeiroinkの読み込みに失敗しました。\n{e}')
            self.coeiroink = None

        self.open_jtalk = None
        if Config.


    async def create_voice(self, Itext:dict, out):
        _type = Itext['hts']['type']
        if _type == 'open_jtalk':
            if _os == 'windows':
                dic = Config.OJ.Dic_shift_jis
            else:
                dic = Config.OJ.Dic_utf_8

            hts = Itext['hts']['id']
            speed = Itext.get('speed',1.2)
            if tone := Itext.get('tone',''):
                tone = f' -fm {tone}'
            if intnation := Itext.get('intnation',''):
                intnation = f' -jf {intnation}'
            if a := Itext.get('a',''):
                a = f' -a {a}'

            cmd=f'open_jtalk -x "{dic}" -ow "{out}" -m {hts} -r {speed}{tone}{intnation}{a}'
            prog = await asyncio.create_subprocess_shell(cmd,stdin=asyncio.subprocess.PIPE)
            await prog.communicate(input= Itext['text'].encode(EFormat))


        elif _type == 'voicevox':
            if not self.voicevox: return

            hts = Itext['hts']['id']
            speed = Itext.get('speed',1.0)
            tone = Itext.get('tone',0.0)
            intnation = Itext.get('intnation',1.0)
            if (hts := self.voicevox.to_speaker_id(hts)) == None:
                return
            with open(out, 'wb')as f:
                f.write( await self.voicevox.create_voice(Itext['text'], hts))


        elif _type == 'coeiroink':
            if not self.coeiroink: return

            hts = Itext['hts']['id']
            speed = Itext.get('speed',1.0)
            tone = Itext.get('tone',0.0)
            intnation = Itext.get('intnation',1.0)
            if (hts := self.coeiroink.to_speaker_id(hts)) == None:
                return

            await self.coeiroink.create_voice(Itext['text'], hts, out, float(speed), float(tone), float(intnation))

