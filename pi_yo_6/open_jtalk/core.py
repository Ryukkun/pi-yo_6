import logging
import os
import asyncio
import subprocess
import wave

from pathlib import Path
from glob import glob
from platform import system
from typing import Optional

from pi_yo_6.load_config import Config
from pi_yo_6.message_unit import MessageUnit
from pi_yo_6.utils import ENGINE_TYPE, NoMetas, SpeakerMeta, VoiceUnit

_os = system().lower()
if _os == 'windows':
    EFormat = 'shift_jis'
else:
    EFormat = 'utf-8'


_log = logging.getLogger(__name__)


class CreateOpenJtalk:
    def __init__(self) -> None:
        try: subprocess.check_call('open_jtalk', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError:
            raise Exception('Open Jtalkをインストールしてください')
        
        self.hts_path = Config.OpenJtalk.hts_path
        self.metas = self.get_metas()
        if not self.metas:
            raise NoMetas('再生可能な htsvoice が存在しません')
        

    async def run_test(self):
        path = Config.output / f"test.wav"
        await self.create_voice('テスト', VoiceUnit(ENGINE_TYPE.OPEN_JTALK ,name=self.metas[0]['name'], style=self.metas[0]['styles'][0]['name']), path)
        if self.__playable_wav(path):
            os.remove(path)
        else:
            raise Exception('Open Jtalkの動作確認に失敗しました。htsvoiceのパスや、辞書のパスが正しいか確認してください。')


    async def create_voice(self, msg: str|MessageUnit, _voice: Optional[VoiceUnit] = None, _out_path: Optional[Path] = None) -> None:
        if isinstance(msg, str) and _voice != None and _out_path != None:
            voice = _voice
            out_path = _out_path
        elif isinstance(msg, MessageUnit):
            voice = msg.voice
            out_path = msg.out_path
            msg = msg.text
        else:
            _log.error('Invalid arguments for create_voice')
            return

        speaker_path = self.to_speaker_id(voice)
        if speaker_path == None: speaker_path = self.metas[0]['styles'][0]['id'] # デフォルトは最初のhtsvoice

        options:list[str] = []
        options.append(f"-r {voice.speed}")

        if voice.tone:
            options.append(f"-fm {voice.tone}")
    
        cmd=f'open_jtalk -x "{Config.OpenJtalk.dictionary_path}" -ow "{out_path}" -m "{speaker_path}" {" ".join(options)}'
        _log.info(f"Running command: {cmd}")
        prog = await asyncio.create_subprocess_shell(cmd,stdin=asyncio.subprocess.PIPE)
        await prog.communicate(input= msg.encode(EFormat))


    def to_speaker_id(self, voice:VoiceUnit) -> Optional[str]:
        res = None
        for meta in self.metas:
            if meta['name'] == voice.name:
                styles = meta['styles']
                for style in styles:
                    if style['name'] == voice.style:
                        res = style['id']
        return res


    def get_metas(self) -> list[SpeakerMeta]:
        """stylesのnameに拡張子は含まれない、 idはファイルパス
        例 :
        { 
            "name": "mei",
            "styles": [
                {
                    "name": "normal",
                    "id": "C:/htsvoice/mei_normal.htsvoice"
                },
                ...]
        }
        Returns
        -------
        list[SpeakerMeta]
            metas
        """
        hts_list = [(_, os.path.split(_)[-1].replace('.htsvoice','')) for _ in glob(str( Config.OpenJtalk.hts_path / '*.htsvoice'))]
        hts_dic:dict[str, list[tuple[str, str]]] = {}
        for path, hts_name in hts_list:  # hts_nameに拡張子は含まれない
            hts_split = hts_name.split('_')
            hts_author = hts_split[0] if len(hts_split) >= 1 else hts_name
            style_name = "_".join(hts_split[1:]) if len(hts_split) >= 2 else hts_author
            if not hts_dic.get(hts_author): hts_dic[hts_author] = []
            hts_dic[hts_author].append((style_name, path))
        return [
            {
                'name':k,
                'styles':[
                    {'name': style_name, 'id': path} for style_name, path in v
                ]
            } for k, v in hts_dic.items()
        ]


    def __playable_wav(self, path:Path) -> bool:
        if not (path.is_file() and path.suffix.lower() == '.wav'):
            return False
        
        size = os.path.getsize(path)
        # 一般的なWAVヘッダーは約44バイトなので、それ以下なら確実にデータがありません
        if size <= 44:
            return False
        
        try:
            with wave.open(str(path.resolve()), 'rb') as f:
                # 基本情報を取得（チャンネル数、サンプルサイズ、サンプリングレート、フレーム数）
                # フレーム数が0なら、中身が空（無音ではなくデータ自体がない）
                if f.getparams().nframes == 0:
                    return False
                return True
        except Exception as e:
            return False