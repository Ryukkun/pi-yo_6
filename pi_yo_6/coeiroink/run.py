import soundfile

from .coeiroink_engine.voicevox_engine.kana_parser import create_kana
from .coeiroink_engine.voicevox_engine.model import AudioQuery
from .coeiroink_engine.voicevox_engine.dev.core import metas as mock_metas
from .coeiroink_engine.voicevox_engine.dev.core import supported_devices as mock_supported_devices

from .synthetic_engine import FixedMSEngine
from .coeiroink import get_metas_dict

from config import Config


class Coeiroink:
    def __init__(self) -> None:
        self.synthesis_engine = FixedMSEngine(
            speakers=mock_metas(),
            supported_devices=mock_supported_devices(),
            load_all_models=Config.Coeiroink.load_all_models,
            use_gpu=Config.Coeiroink.use_gpu,
        )
        self.sampling_rate = self.synthesis_engine.default_sampling_rate
        self.metas = get_metas_dict()


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
