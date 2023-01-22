import glob
import time
from typing import List, NamedTuple, Optional, Dict

from os import path
import librosa
import numpy as np
import pyworld as pw
import resampy
import torch
import yaml
from espnet2.text.token_id_converter import TokenIDConverter
from espnet2.bin.tts_inference import Text2Speech
import concurrent.futures as cf
#from threading import Thread

from ..core.coeiroink import get_metas_dict
from ...model import AccentPhrase, AudioQuery
from ...synthesis_engine import SynthesisEngineBase

parents_folder = path.dirname(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

class EspnetSettings(NamedTuple):
    acoustic_model_config_path: str
    acoustic_model_path: str


class EspnetModel:
    def __init__(self, settings: EspnetSettings, use_gpu=False, speed_scale=1.0):
        self.device = 'cuda' if use_gpu else 'cpu'
        self.tts_model = Text2Speech(
            settings.acoustic_model_config_path,
            settings.acoustic_model_path,
            device=self.device,
            seed=0,
            # Only for FastSpeech & FastSpeech2 & VITS
            speed_control_alpha=speed_scale,
            # Only for VITS
            noise_scale=0.333,
            noise_scale_dur=0.333,
        )

        with open(settings.acoustic_model_config_path) as f:
            config = yaml.safe_load(f)
        self.token_id_converter = TokenIDConverter(
            token_list=config["token_list"],
            unk_symbol="<unk>",
        )

        self.used = 0
        self.last_used = time.time()

    def make_voice(self, tokens, seed=0):
        self.used += 1
        self.last_used = time.time()
        np.random.seed(seed)
        torch.manual_seed(seed)
        text_ints = np.array(self.token_id_converter.tokens2ids(tokens), dtype=np.int64)
        with torch.no_grad():
            wave = self.tts_model(text_ints)["wav"]
        wave = wave.view(-1).cpu().numpy()
        return wave



    @classmethod
    def get_espnet_model(cls, acoustic_model_path, acoustic_model_config_path, use_gpu, speed_scale=1.0):
        settings = EspnetSettings(
            acoustic_model_config_path=acoustic_model_config_path,
            acoustic_model_path=acoustic_model_path,
        )
        return cls(settings, use_gpu=use_gpu, speed_scale=speed_scale)

    @classmethod
    def get_character_model(cls, use_gpu, speaker_id, speed_scale=1.0, load_forever:bool=False):
        cls.load_forever = load_forever
        uuid = None
        metas = get_metas_dict()
        for meta in metas:
            for style in meta['styles']:
                if speaker_id == style['id']:
                    uuid = meta['speaker_uuid']
        if uuid is None:
            raise Exception("Not Found Speaker Directory")

        
        acoustic_model_folder_path = path.join(parents_folder, 'speaker_info', uuid, 'model', str(speaker_id))
        model_files = sorted(glob.glob(acoustic_model_folder_path + '/*.pth'))

        return cls.get_espnet_model(
            acoustic_model_path=model_files[0],
            acoustic_model_config_path=f"{acoustic_model_folder_path}/config.yaml",
            use_gpu=use_gpu,
            speed_scale=speed_scale
        )





class MockSynthesisEngine(SynthesisEngineBase):
    def __init__(self,
                 speakers: str,
                 supported_devices: Optional[str] = None,
                 load_all_models: bool = False):
        self._speakers = speakers
        self._supported_devices = supported_devices

        self.default_sampling_rate = 44100
        self.use_gpu = False

        metas = get_metas_dict()
        #self.previous_speaker_id = metas[0]['styles'][0]['id']
        self.previous_speed_scale = 1.0

        self.speaker_models: Dict[tuple, EspnetModel] = {}
        if load_all_models:

            def _add_speaker_model(_id):
                self.speaker_models[_id] = EspnetModel.get_character_model(
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


    @property
    def speakers(self) -> str:
        return self._speakers

    @property
    def supported_devices(self) -> Optional[str]:
        return self._supported_devices

    @staticmethod
    def replace_phoneme_length(accent_phrases: List[AccentPhrase], speaker_id: int) -> List[AccentPhrase]:
        return accent_phrases

    @staticmethod
    def replace_mora_pitch(accent_phrases: List[AccentPhrase], speaker_id: int) -> List[AccentPhrase]:
        return accent_phrases

    def _synthesis_impl(self, query: AudioQuery, speaker_id: int, text: str) -> np.ndarray:
        start_time = time.time()
        tokens = self.query2tokens_prosody(query, text)

        if (temp_speaker_model := self.speaker_models.get( (speaker_id, query.speedScale) )):
            pass
        
        else:
            temp_speaker_model = EspnetModel.get_character_model(
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

        rtf = (time.time() - start_time)
        print(f"Synthesis Time: {rtf}")
        return wave

    @staticmethod
    def query2tokens_prosody(query: AudioQuery, text: str):
        tokens = ['^']
        for i, accent_phrase in enumerate(query.accent_phrases):
            up_token_flag = False
            for j, mora in enumerate(accent_phrase.moras):
                if mora.consonant:
                    tokens.append(mora.consonant.lower())
                if mora.vowel == 'N':
                    tokens.append(mora.vowel)
                else:
                    tokens.append(mora.vowel.lower())
                if accent_phrase.accent == j+1 and j+1 != len(accent_phrase.moras):
                    tokens.append(']')
                if accent_phrase.accent-1 >= j+1 and up_token_flag is False:
                    tokens.append('[')
                    up_token_flag = True
            if i+1 != len(query.accent_phrases):
                if accent_phrase.pause_mora:
                    tokens.append('_')
                else:
                    tokens.append('#')
        try:
            if query.accent_phrases[-1].is_interrogative or text[-1] in ['?', '？']:
                tokens.append('?')
            else:
                tokens.append('$')
        except IndexError:
            tokens.append('$')
        return tokens

    @staticmethod
    def get_world(wave, fs):
        _f0, t = pw.dio(wave, fs)
        f0 = pw.stonemask(wave, _f0, t, fs)
        sp = pw.cheaptrick(wave, f0, t, fs)
        ap = pw.d4c(wave, f0, t, fs)
        return f0, sp, ap

    @staticmethod
    def get_wav_from_world(f0, sp, ap, fs):
        wav = pw.synthesize(f0, sp, ap, fs)
        return wav
