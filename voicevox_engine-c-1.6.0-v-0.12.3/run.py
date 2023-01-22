# import asyncio
import json

# import sys
from typing import Dict, List, Optional

import soundfile

from voicevox_engine import __version__
from voicevox_engine.kana_parser import create_kana
from voicevox_engine.model import (
    AudioQuery,
    Speaker,
    SpeakerInfo
)
from voicevox_engine.synthesis_engine import SynthesisEngineBase, make_synthesis_engines


class Coeiroink:
    def __init__(self, load_add_models:bool =False, cpu_num:Optional[int] =None ) -> None:
        self.synthesis_engine = make_synthesis_engines(
            use_gpu=False,
            voicelib_dirs=None,
            voicevox_dir=None,
            runtime_dirs=None,
            cpu_num_threads=cpu_num,
            enable_mock=False,
            load_all_models=load_add_models,
        )
        self.sampling_rate = self.synthesis_engine.default_sampling_rate


    def easy_synthesis(self,
        text: str,
        speaker: int,
        enable_interrogative_upspeak: bool = True, #疑問系のテキストが与えられたら語尾を自動調整する
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

        coe.synthesis(
            query= query,
            speaker= speaker,
            enable_interrogative_upspeak= enable_interrogative_upspeak,
            out=out,
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



    def speakers(self):
        return self.synthesis_engine.speakers


    def speaker_info(self, speaker_uuid: str):
        """
        指定されたspeaker_uuidに関する情報をjson形式で返します。
        画像や音声はbase64エンコードされたものが返されます。

        Returns
        -------
        ret_data: SpeakerInfo
        """
        speakers = json.loads(self.synthesis_engine.speakers)
        for i in range(len(speakers)):
            if speakers[i]["speaker_uuid"] == speaker_uuid:
                speaker = speakers[i]
                break
        else:
            raise #HTTPException(status_code=404, detail="該当する話者が見つかりません")

        try:
            ret_data = SpeakerInfo.from_local(Speaker(**speaker))
        except FileNotFoundError:
            import traceback
            traceback.print_exc()
            raise #HTTPException(status_code=500, detail="追加情報が見つかりませんでした")

        return ret_data


    
    def initialize_speaker(self, speaker: int, core_version: Optional[str] = None):
        """
        指定されたspeaker_idの話者を初期化します。
        実行しなくても他のAPIは使用できますが、初回実行時に時間がかかることがあります。
        """
        self.synthesis_engine.initialize_speaker_synthesis(speaker)

   
    def is_initialized_speaker(self, speaker: int, core_version: Optional[str] = None):
        """
        指定されたspeaker_idの話者が初期化されているかどうかを返します。
        """
        return self.synthesis_engine.is_initialized_speaker_synthesis(speaker)



if __name__ == "__main__":
    coe = Coeiroink(load_add_models=False)
    import asyncio
    loop = asyncio.get_event_loop()
    coe.easy_synthesis(speaker=0, text="テストなのだ？", speed=2.0)
    #loop.run_until_complete(asyncio.sleep(40))
    coe.easy_synthesis(speaker=11, text="テストなのだ？", out="./1.wav", pitch=2.0)
    #_ = coe.audio_query(speaker=0, text="テストなのだ？")
    #_.speedScale = 2.0
    #print(_)
    #coe.synthesis(query=_, speaker=0, out="./2.wav")
    # coe.easy_synthesis(speaker=60, text="テストなのだ？", out="./3.wav")
    # coe.easy_synthesis(speaker=43, text="テストなのだ？", out="./4.wav")
