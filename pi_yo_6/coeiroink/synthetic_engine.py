import time
import librosa
import resampy

from glob import glob
from pathlib import Path
from typing import Optional, Dict

import concurrent.futures as cf
import numpy as np

from .coeiroink import get_metas_dict
from .coeiroink_engine.voicevox_engine.model import AudioQuery
from .coeiroink_engine.voicevox_engine.dev.synthesis_engine.coeiroink import (
    EspnetModel,
    MockSynthesisEngine,
    EspnetSettings,
)


parent_dir = Path(__file__).parent


class FixedEspnetModel(EspnetModel):
    def __init__(self, settings: EspnetSettings, use_gpu=False, speed_scale=1.0):
        super().__init__(settings, use_gpu, speed_scale)
        self.used = 0
        self.last_used = time.time()


    def make_voice(self, tokens, seed=0):
        self.used += 1
        self.last_used = time.time()
        return super().make_voice(tokens, seed)


    @classmethod
    def get_character_model(cls, use_gpu, speaker_id, speed_scale=1.0):
        uuid = None
        metas = get_metas_dict()
        for meta in metas:
            for style in meta['styles']:
                if speaker_id == style['id']:
                    uuid = meta['speaker_uuid']
        if uuid is None:
            raise Exception("Not Found Speaker Directory")

        acoustic_model_folder_path = parent_dir / 'speaker_info' / uuid / 'model' / str(speaker_id)
        model_files = sorted(glob(f'{acoustic_model_folder_path}/*.pth'))

        return cls.get_espnet_model(
            acoustic_model_path=model_files[0],
            acoustic_model_config_path=f"{acoustic_model_folder_path}/config.yaml",
            use_gpu=use_gpu,
            speed_scale=speed_scale
        )



class FixedMSEngine(MockSynthesisEngine):
    def __init__(self,
                 speakers: str,
                 supported_devices: Optional[str] = None,
                 load_all_models: bool = False,
                 use_gpu: bool = False):
        self._speakers = speakers
        self._supported_devices = supported_devices

        self.default_sampling_rate = 44100
        self.use_gpu = use_gpu

        metas = get_metas_dict()
        #self.previous_speaker_id = metas[0]['styles'][0]['id']
        self.previous_speed_scale = 1.0

        self.speaker_models: Dict[tuple, EspnetModel] = {}
        if load_all_models:

            def _add_speaker_model(_id):
                self.speaker_models[_id] = FixedEspnetModel.get_character_model(
                                            use_gpu=self.use_gpu,
                                            speaker_id=_id[0],
                                            speed_scale=self.previous_speed_scale,
                                            load_forever=True)
            futures = []
            with cf.ThreadPoolExecutor(10) as exe:
                for _ in metas:
                    for style in _['styles']:
                        futures.append(exe.submit(_add_speaker_model, (style["id"], self.previous_speed_scale) ))
            cf.wait(futures)

        self.do_loop = True
        cf.ThreadPoolExecutor(1).submit(self.loop_check)
        #Thread(target=self.loop_check, daemon=True).start()


    def __del__(self):
        self.do_loop = False


    def loop_check(self):
        while self.do_loop:
            time.sleep(10)
            for k, v in self.speaker_models.copy().items():
                if v.load_forever: continue
                if v.used == 0: limit = 120
                elif v.used == 1: limit = 60
                elif 2 <= v.used : limit = 300

                if (v.last_used + limit) < time.time():
                    del self.speaker_models[k]



    def _synthesis_impl(self, query: AudioQuery, speaker_id: int, text: str) -> np.ndarray:
        tokens = self.query2tokens_prosody(query, text)

        if (temp_speaker_model := self.speaker_models.get( (speaker_id, query.speedScale) )):
            pass
        
        else:
            temp_speaker_model = FixedEspnetModel.get_character_model(
                        use_gpu=self.use_gpu,
                        speaker_id=speaker_id,
                        speed_scale=1/query.speedScale
                        )
            self.speaker_models[(speaker_id, query.speedScale)] = temp_speaker_model


        wave = temp_speaker_model.make_voice(tokens)

        # trim
        wave, _ = librosa.effects.trim(wave, top_db=30)

        # volume
        if query.volumeScale != 1:
            wave *= query.volumeScale

        # pitch, intonation
        if query.pitchScale != 0 or query.intonationScale != 1:
            f0, sp, ap = self.get_world(wave.astype(np.float64), query.outputSamplingRate)
            # pitch
            if query.pitchScale != 0:
                f0 *= 2 ** query.pitchScale
            # intonation
            if query.intonationScale != 1:
                m = f0.mean()
                s = f0.std()
                f0_tmp = (f0 - m) / s
                f0 = (f0_tmp * (s * query.intonationScale)) + m
            wave = self.get_wav_from_world(f0, sp, ap, query.outputSamplingRate).astype(np.float32)

        # add sil
        if query.prePhonemeLength != 0 or query.postPhonemeLength != 0:
            pre_pause = np.zeros(int(self.default_sampling_rate * query.prePhonemeLength))
            post_pause = np.zeros(int(self.default_sampling_rate * query.postPhonemeLength))
            wave = np.concatenate([pre_pause, wave, post_pause], 0)

        # resampling
        if query.outputSamplingRate != self.default_sampling_rate:
            wave = resampy.resample(
                wave,
                self.default_sampling_rate,
                query.outputSamplingRate,
                filter="kaiser_fast",
            )

        return wave


if __name__ == '__main__':
    print(Path(__file__).parent)