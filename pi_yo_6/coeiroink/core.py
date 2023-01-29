import os
import soundfile
import asyncio

from typing import Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from config import Config
from .. import downloader as Downloader

class CreateCoeiroink:
    def __init__(self) -> None:
        
        # Load Coeiroink
        print('Loading Coeiroink ....')
        self.coeiroink = Coeiroink()

        parent = Path(__file__).parent
        file_name = 'coeiroink_engine'
        file_path = parent / file_name
        if not os.path.isdir(file_path):
            url = 'https://github.com/shirowanisan/voicevox_engine/archive/refs/heads/c-1.6.0+v-0.12.3.zip'
            Downloader.download_zip(url, parent, file_name)

            model_file = parent / 'coeiroink_engine' / 'voicevox_engine' / 'model.py'
            befor_text = 'from voicevox_engine.utility import engine_root'
            after_text = 'from .utility import engine_root'
            with open(model_file, 'r') as f:
                text = f.read()
            if befor_text in text:
                with open(model_file, 'w') as f:
                    f.write(text.replace(befor_text, after_text))

        from .coeiroink_engine.voicevox_engine.kana_parser import create_kana
        from .coeiroink_engine.voicevox_engine.model import AudioQuery
        from .coeiroink_engine.voicevox_engine.dev.core import metas as mock_metas
        from .coeiroink_engine.voicevox_engine.dev.core import supported_devices as mock_supported_devices

        from .synthetic_engine import FixedMSEngine
        from .coeiroink import get_metas_dict


        self.metas = get_metas_dict()
        self.exe = ThreadPoolExecutor(1)
        self.TEXT_LIMIT = 100


    async def create_voice(
        self, 
        text: str,
        speaker: int,
        out: str = "./output.wav",
        speed: float = 1.0,
        tone: float = 0.0,
        intnation: float = 1.0
        ):
        # 文字数上限
        if len(text) > self.TEXT_LIMIT:
            text = text[:self.TEXT_LIMIT]

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.exe, 
            self.coeiroink.easy_synthesis,
                text, 
                speaker,
                out,
                speed,
                tone,
                intnation
            )


    def to_speaker_id(self, hts):
        try: hts = int(hts)
        except Exception: pass
        else:
            for meta in self.metas:
                for style in meta['styles']:
                    if style['id'] == hts:
                        return hts
            return
        
        res = None
        hts = hts.lower()
        for meta in self.metas:
            if meta['name'].lower() in hts:
                styles = meta['styles']
                for style in styles:
                    if style['name'].lower() in hts:
                        res = style['id']
                if type(res) != int:
                    res = styles[0]['id']
                break
        return res


class Coeiroink:
    def __init__(self) -> None:
        self.synthesis_engine = FixedMSEngine(
            speakers=mock_metas(),
            supported_devices=mock_supported_devices(),
            load_all_models=Config.Coeiroink.load_all_models,
            use_gpu=False,
        )
        self.sampling_rate = self.synthesis_engine.default_sampling_rate


    def easy_synthesis(self,
        text: str,
        speaker: int,
        out: str = "./output.wav",
        speed: float = 1.0,
        pitch: float = 0.0,
        intnation: float = 1.0,
        ):

        query = self.audio_query(text=text, speaker=speaker)
        query.speedScale = speed
        query.pitchScale = pitch
        query.intonationScale = intnation
        query.prePhonemeLength = 0.0
        query.postPhonemeLength = 0.0
        query.volumeScale = 0.4

        self.synthesis(
            query= query,
            speaker= speaker,
            enable_interrogative_upspeak= True,
            out= out,
            text= text
            )



    def audio_query(self, text: str, speaker: int):
        """
        クエリの初期値を得ます。ここで得られたクエリはそのまま音声合成に利用できます。各値の意味は`Schemas`を参照してください。
        """
        accent_phrases = self.synthesis_engine.create_accent_phrases(text, speaker_id=speaker)
        return AudioQuery(
            accent_phrases=accent_phrases,
            speedScale=1,
            pitchScale=0,
            intonationScale=1,
            volumeScale=1,
            prePhonemeLength=0.1,
            postPhonemeLength=0.1,
            outputSamplingRate=self.sampling_rate,
            outputStereo=False,
            kana=create_kana(accent_phrases),
        )



    def synthesis(
        self,
        query: AudioQuery,
        speaker: int,
        enable_interrogative_upspeak: bool = True, #疑問系のテキストが与えられたら語尾を自動調整する
        out: str = "./output.wav",
        text: str = '',
    ):
        wave = self.synthesis_engine.synthesis(
            query=query,
            speaker_id=speaker,
            enable_interrogative_upspeak=enable_interrogative_upspeak,
            text=text
        )

        soundfile.write(
            file=out, data=wave, samplerate=query.outputSamplingRate, format="WAV"
        )



if __name__ == "__main__":
    coe = Coeiroink(load_add_models=False)

    coe.easy_synthesis(speaker=0, text="テストなのだ？", speed=2.0)

    coe.easy_synthesis(speaker=11, text="テストなのだ？", out="./1.wav", pitch=2.0)
    #_ = coe.audio_query(speaker=0, text="テストなのだ？")
    #_.speedScale = 2.0
    #print(_)
    #coe.synthesis(query=_, speaker=0, out="./2.wav")
    # coe.easy_synthesis(speaker=60, text="テストなのだ？", out="./3.wav")
    # coe.easy_synthesis(speaker=43, text="テストなのだ？", out="./4.wav")
