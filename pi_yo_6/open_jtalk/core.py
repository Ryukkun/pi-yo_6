import os
import asyncio
from re import S
import re
import subprocess
from pathlib import Path

from glob import glob
from platform import system

from config import Config
from pi_yo_6.message_unit import MessageUnit
from .. import downloader as Downloader
from pi_yo_6.utils import NoMetas, SpeakerMeta

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
        try: subprocess.check_call('open_jtalk', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            raise Exception('Open Jtalkをインストールしてください')
        
        self.hts_path = Config.OpenJtalk.hts_path
        self.metas = self.get_metas()
        if not self.metas:
            raise NoMetas('再生可能な htsvoice が存在しません')

        if _os == 'windows':
            DownloadDic.shift_jis()

        DownloadDic.utf_8()


    async def create_voice(
        self, 
        text: MessageUnit
        ):

        if _os == 'windows':
            dic = DownloadDic.shift_jis()
        else:
            dic = DownloadDic.utf_8()

        def get_path() -> str:
            for meta in self.metas:
                for style in meta['styles']:
                    if style['name'] == text.speaker.id:
                        return style['id']
            return self.metas[0]['styles'][0]['id'] # デフォルトは最初のhtsvoice
        speaker_path = get_path()
    
        cmd=f'open_jtalk -x "{dic}" -ow "{text.out_path}" -m "{speaker_path}" -r {text.speed}{text.tone}{text.intnation}{text.a}'
        prog = await asyncio.create_subprocess_shell(cmd,stdin=asyncio.subprocess.PIPE)
        await prog.communicate(input= text.text.encode(EFormat))



    def get_metas(self) -> list[SpeakerMeta]:
        hts_list = [(_, os.path.split(_)[1].replace('.htsvoice','')) for _ in glob(str( Config.OpenJtalk.hts_path / '*.htsvoice'))]
        hts_dic:dict[str, list[tuple[str, str]]] = {}
        for path, hts_name in hts_list:
            hts_author = hts_name.split('_')[0]
            if not hts_dic.get(hts_author): hts_dic[hts_author] = []
            hts_dic[hts_author].append((path, hts_name))
        return [
            {
                'name':k,
                'styles':[
                    {'name': hts_name, 'id': path} for path, hts_name in v
                ]
            } for k, v, in hts_dic.items()
        ]