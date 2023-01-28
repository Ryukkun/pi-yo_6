import os
import asyncio
import requests
import tarfile
from tqdm import tqdm
from pathlib import Path

from glob import glob
from platform import system

from config import Config
from .. import downloader as Downloader

_os = system().lower()
if _os == 'windows':
    EFormat = 'shift_jis'
else:
    EFormat = 'utf-8'
parent_path = Path(__file__).parent

class DownloadDic:
    @classmethod
    def utf_8(self):
        file_name = 'open_jtalk_dic_utf_8-1.11'
        file_path = parent_path / file_name
        if not file_path.is_dir():
            url = 'https://jaist.dl.sourceforge.net/project/open-jtalk/Dictionary/open_jtalk_dic-1.11/open_jtalk_dic_utf_8-1.11.tar.gz'
            Downloader.download_tar(url, parent_path, file_name)
        return str(file_path)

    @classmethod
    def shift_jis(self):
        file_name = 'open_jtalk_dic_shift_jis-1.11'
        file_path = parent_path / file_name
        if not file_path.is_dir():
            url = 'https://jaist.dl.sourceforge.net/project/open-jtalk/Dictionary/open_jtalk_dic-1.11/open_jtalk_dic_shift_jis-1.11.tar.gz'
            Downloader.download_tar(url, parent_path, file_name)
        return str(file_path)




class CreateOpenJtalk:
    def __init__(self) -> None:
        self.metas = self.get_metas()

        if _os == 'windows':
            DownloadDic.shift_jis()

        DownloadDic.utf_8()


    async def create_voice(
        self, 
        text: str,
        speaker: str,
        out: str = f"{Config.output}output.wav",
        speed: str = '1.2',
        tone: str = '',
        intnation: str = '',
        a: str = ''
        ):

        if _os == 'windows':
            dic = DownloadDic.shift_jis()
        else:
            dic = DownloadDic.utf_8()

        cmd=f'open_jtalk -x "{dic}" -ow "{out}" -m {speaker} -r {speed}{tone}{intnation}{a}'
        prog = await asyncio.create_subprocess_shell(cmd,stdin=asyncio.subprocess.PIPE)
        await prog.communicate(input= text.encode(EFormat))



    def get_metas(self) -> list:
        hts_list = [os.path.split(_)[1].replace('.htsvoice','') for _ in glob(f'{Config.OJ.hts_path}*.htsvoice')]
        hts_dic = {}
        for hts in hts_list:
            _hts = hts.split('_')
            hts_name = _hts[0]
            if not hts_dic.get(hts_name): hts_dic[hts_name] = []
            hts_dic[hts_name].append(hts)
        return [
            {
                'name':k,
                'styles':[
                    {'name': _, 'id': _} for _ in v
                ]
            } for k, v, in hts_dic.items()
        ]