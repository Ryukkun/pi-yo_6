import os
import asyncio
import requests
import tarfile
from tqdm import tqdm
from pathlib import Path

from glob import glob
from platform import system

from config import Config

_os = system().lower()
if _os == 'windows':
    EFormat = 'shift_jis'
else:
    EFormat = 'utf-8'


class DownloadDic:
    @classmethod
    def utf_8(self):
        parent_path = Path(__file__).parent
        self.f_name = parent_path / 'open_jtalk_dic_utf_8-1.11'
        if not self.f_name.is_dir():
            self.url = 'https://jaist.dl.sourceforge.net/project/open-jtalk/Dictionary/open_jtalk_dic-1.11/open_jtalk_dic_utf_8-1.11.tar.gz'
            self.download(self)
        return str(self.f_name)

    @classmethod
    def shift_jis(self):
        parent_path = Path(__file__).parent
        self.f_name = parent_path / 'open_jtalk_dic_shift_jis-1.11'
        if not self.f_name.is_dir():
            self.url = 'https://jaist.dl.sourceforge.net/project/open-jtalk/Dictionary/open_jtalk_dic-1.11/open_jtalk_dic_utf_8-1.11.tar.gz'
            self.download(self)
        return str(self.f_name)


    def download(self):
        tar_gz = f'{self.f_name}.tar.gz'
        r = requests.get(self.url, stream=True)
        total_size = int(r.headers.get('content-length', 0))
        chunk_size = 32 * 1024

        pbar = tqdm(total=total_size, unit='B', unit_scale=True)
        with open(tar_gz, 'wb') as f:
            for data in r.iter_content(chunk_size):
                f.write(data)
                pbar.update(chunk_size)
        pbar.close()
        
        # 展開
        with tarfile.open(tar_gz, 'r:gz')as tar:
            tar.extractall(path=self.f_name)
        os.remove(tar_gz)



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