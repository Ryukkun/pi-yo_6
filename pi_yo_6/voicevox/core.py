'''
Copyright (c) 2021 Hiroshiba Kazuyuki

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
# ライブラリの位置だけ少し変えさせていただきます


from ctypes import *
import platform
import os
import numpy
import time
import asyncio
import json
import requests
from concurrent.futures import ThreadPoolExecutor

from config import Config

# 何故かバグるからタイミング調整なのだ
# その他上限設定
class CreateVOICEVOX:
    def __init__(self) -> None:
        
        # Load VoiceVox
        print('Loading VoiceVox ....')
        self.VVox = VOICEVOX(use_gpu= Config.VVOX.use_gpu, load_all_models= Config.VVOX.load_all_models)
        self.metas = json.loads(self.VVox.metas())
        res = requests.get('https://api.github.com/repos/VOICEVOX/voicevox_core/releases/latest')
        res = res.json()
        print(f'Loaded VoiceVox!! - Ver.{self.metas[0]["version"]}')
        if self.metas[0]["version"] == res['tag_name']:
            print(f'最新バージョンです')
        else:
            print(f'最新バージョンは {res["tag_name"]} です {res["html_url"]}')

        self.exe = ThreadPoolExecutor(1)
        self.TEXT_LIMIT = 100


    async def create_voice(self, Itext, speaker_id):
        # 文字数上限
        if len(Itext) > self.TEXT_LIMIT:
            Itext = Itext[:self.TEXT_LIMIT]

        loop = asyncio.get_event_loop()
        data = None
        data = await loop.run_in_executor(self.exe, self.VVox.voicevox_tts, Itext, speaker_id)
        return data


    def name_list(self):
        res = []
        for name_dic in self.metas:
            name = name_dic['name']
            _res = [name]
            for style_dic in name_dic['styles']:
                style = style_dic['name']
                id = style_dic['id']
                _res.append(f'{style}')
            res.append(_res)

        return res


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
        for meta in self.metas:
            if hts in meta['name']:
                styles = meta['styles']
                for style in styles:
                    if hts in style['name']:
                        res = style['id']
                if type(res) != int:
                    res = styles[0]['id']
                break
        return res



class VOICEVOX:
    def __init__(self,use_gpu: bool, cpu_num_threads=0, load_all_models=True):
        # numpy ndarray types
        int64_dim1_type = numpy.ctypeslib.ndpointer(dtype=numpy.int64, ndim=1)
        float32_dim1_type = numpy.ctypeslib.ndpointer(dtype=numpy.float32, ndim=1)
        int64_dim2_type = numpy.ctypeslib.ndpointer(dtype=numpy.int64, ndim=2)
        float32_dim2_type = numpy.ctypeslib.ndpointer(dtype=numpy.float32, ndim=2)

        get_os = platform.system()
        
        if get_os == "Windows":
            lib_file = Config.VVOX.core_windows
        elif get_os == "Darwin":
            lib_file = Config.VVOX.core_darwin
        elif get_os == "Linux":
            lib_file = Config.VVOX.core_linux

        # ライブラリ読み込み
        if not os.path.exists(lib_file):
            raise Exception(f"coreライブラリファイルが{lib_file}に存在しません")
        self.lib = cdll.LoadLibrary(lib_file)

        # 関数型定義
        self.lib.initialize.argtypes = (c_bool, c_int, c_bool)
        self.lib.initialize.restype = c_bool

        self.lib.load_model.argtypes = (c_int64,)
        self.lib.load_model.restype = c_bool

        self.lib.is_model_loaded.argtypes = (c_int64,)
        self.lib.is_model_loaded.restype = c_bool

        self.lib.finalize.argtypes = ()

        self.lib.metas.restype = c_char_p

        self.lib.supported_devices.restype = c_char_p

        self.lib.yukarin_s_forward.argtypes = (
            c_int64, int64_dim1_type, int64_dim1_type, float32_dim1_type)
        self.lib.yukarin_s_forward.restype = c_bool

        self.lib.yukarin_sa_forward.argtypes = (c_int64, int64_dim2_type, int64_dim2_type, int64_dim2_type,
                                        int64_dim2_type, int64_dim2_type, int64_dim2_type, int64_dim1_type, float32_dim2_type)
        self.lib.yukarin_sa_forward.restype = c_bool

        self.lib.decode_forward.argtypes = (
            c_int64, c_int64, float32_dim2_type, float32_dim2_type, int64_dim1_type, float32_dim1_type)
        self.lib.decode_forward.restype = c_bool

        self.lib.last_error_message.restype = c_char_p

        self.lib.voicevox_load_openjtalk_dict.argtypes = (c_char_p,)
        self.lib.voicevox_load_openjtalk_dict.restype = c_int

        self.lib.voicevox_tts.argtypes = (c_char_p, c_int64, POINTER(c_int), POINTER(POINTER(c_uint8)))
        self.lib.voicevox_tts.restype = c_int

        self.lib.voicevox_tts_from_kana.argtypes = (c_char_p, c_int64, POINTER(c_int), POINTER(POINTER(c_uint8)))
        self.lib.voicevox_tts_from_kana.restype = c_int

        self.lib.voicevox_wav_free.argtypes = (POINTER(c_uint8),)

        self.lib.voicevox_error_result_to_message.argtypes = (c_int,)
        self.lib.voicevox_load_openjtalk_dict.argtypes = (c_char_p,)

        self.voicevox_load_openjtalk_dict(Config.OJ.Dic_utf_8)
        success = self.lib.initialize(use_gpu, cpu_num_threads, load_all_models)
        if not success:
            raise Exception(self.lib.last_error_message().decode())


    def load_model(self, speaker_id: int):
        success = self.lib.load_model(speaker_id)
        if not success:
            raise Exception(self.lib.last_error_message().decode())

    def is_model_loaded(self, speaker_id: int) -> bool:
        return self.lib.is_model_loaded(speaker_id)

    def metas(self) -> str:
        return self.lib.metas().decode()


    def supported_devices(self) -> str:
        return self.lib.supported_devices().decode()


    def yukarin_s_forward(self, length: int, phoneme_list: numpy.ndarray, speaker_id: numpy.ndarray) -> numpy.ndarray:
        output = numpy.zeros((length, ), dtype=numpy.float32)
        success = self.lib.yukarin_s_forward(length, phoneme_list, speaker_id, output)
        if not success:
            raise Exception(self.lib.last_error_message().decode())
        return output


    def yukarin_sa_forward(
        self,
        length: int,
        vowel_phoneme_list,
        consonant_phoneme_list,
        start_accent_list,
        end_accent_list,
        start_accent_phrase_list,
        end_accent_phrase_list,
        speaker_id
    ):
        output = numpy.empty((len(speaker_id), length,), dtype=numpy.float32)
        success = self.lib.yukarin_sa_forward(
            length, vowel_phoneme_list, consonant_phoneme_list, start_accent_list, end_accent_list, start_accent_phrase_list, end_accent_phrase_list, speaker_id, output
        )
        if not success:
            raise Exception(self.lib.last_error_message().decode())
        return output


    def decode_forward(self, length: int, phoneme_size: int, f0, phoneme, speaker_id):
        output = numpy.empty((length*256,), dtype=numpy.float32)
        success = self.lib.decode_forward(
            length, phoneme_size, f0, phoneme, speaker_id, output
        )
        if not success:
            raise Exception(self.lib.last_error_message().decode())
        return output

    def voicevox_load_openjtalk_dict(self, dict_path: str):
        errno = self.lib.voicevox_load_openjtalk_dict(dict_path.encode())
        if errno != 0:
            raise Exception(self.lib.voicevox_error_result_to_message(errno).decode())

    def voicevox_tts(self, text: str, speaker_id: int) -> bytes:
        output_binary_size = c_int()
        output_wav = POINTER(c_uint8)()
        errno = self.lib.voicevox_tts(text.encode(), speaker_id, byref(output_binary_size), byref(output_wav))
        if errno != 0:
            raise Exception(self.lib.voicevox_error_result_to_message(errno).decode())
        output = create_string_buffer(output_binary_size.value * sizeof(c_uint8))
        memmove(output, output_wav, output_binary_size.value * sizeof(c_uint8))
        self.lib.voicevox_wav_free(output_wav)
        return output

    def voicevox_tts_from_kana(self, text: str, speaker_id: int) -> bytes:
        output_binary_size = c_int()
        output_wav = POINTER(c_uint8)()
        errno = self.lib.voicevox_tts_from_kana(text.encode(), speaker_id, byref(output_binary_size), byref(output_wav))
        if errno != 0:
            raise Exception(self.lib.voicevox_error_result_to_message(errno).decode())
        output = create_string_buffer(output_binary_size.value * sizeof(c_uint8))
        memmove(output, output_wav, output_binary_size.value * sizeof(c_uint8))
        self.lib.voicevox_wav_free(output_wav)
        return output

    def finalize(self, ):
        self.lib.finalize()
