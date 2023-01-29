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


        from .run import Coeiroink

        # Load Coeiroink
        print('Loading Coeiroink ....')
        self.coeiroink = Coeiroink()

        self.metas = self.coeiroink.metas
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


