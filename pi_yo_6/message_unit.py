from dataclasses import dataclass
from datetime import datetime
import enum
import os
from pathlib import Path
import re
from typing import TYPE_CHECKING
import uuid

import alkana

from pi_yo_6.config import Config
from pi_yo_6.romaji.to_kana import Romaji

if TYPE_CHECKING:
    from pi_yo_6.synthetic_voice import SyntheticEngines


re_mention = re.compile(r'<(@&|@)\d+>')
re_emoji = re.compile(r'<:.+:[0-9]+>')
re_url = re.compile(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+')
re_speed = re.compile(r'(^|\s)speed:([\d.]*)(?=\s|$)')
re_a = re.compile(r'(^|\s)a:([\d.]*)(?=\s|$)')
re_tone = re.compile(r'(^|\s)tone:([\d.]*)(?=\s|$)')
re_int = re.compile(r'(^|\s)intnation:([\d.]*)(?=\s|$)')
re_voice = re.compile(r'(^|\s)voice:(\S*)(?=\s|$)')
#re_romaji_unit = re.compile(r'(^|[^a-zA-Z])([a-zA-Z\-]+)($|[^a-zA-Z])') #(先頭|英語以外の文字)(英単語)(末尾|英語以外の文字)
re_romaji_unit = re.compile(r'\b([a-zA-Z\-]+)\b') #(単語境界)(英単語)(単語境界)
#re_not_romaji = re.compile(r'[^a-zA-Z\-]')
#_status = 'voice:\S*\s|speed:\S*\s|a:\S*\s|tone:\S*\s|intnation:\S*\s'
#re_text_status = re.compile(r'({0}|^)+.+?(?=\s({0})|$)'.format(_status)) # [(^|_status) 癖の強い文字たち ($|_status)]


class ENGINE_TYPE(str, enum.Enum):
    OPEN_JTALK = 'open_jtalk'
    VOICEVOX = 'voicevox'
    COEIROINK = 'coeiroink'

@dataclass
class VoiceUnit:
    type:ENGINE_TYPE = ENGINE_TYPE.OPEN_JTALK
    id:str = ""
    speed:float = 1.2
    a:float = 0.0
    tone:float = 0.0
    """= pitch"""
    intnation:float = 0.0


class MessageUnit:
    def __init__(self, text:str, engines:"SyntheticEngines", time:datetime = datetime.now()) -> None:
        self.time = time
        self.engines = engines
        self.text:str = text
        self.voice = VoiceUnit()
        self.out_path:Path = Config.output / f'{uuid.uuid4()}.wav'
        self.generated = False


    def _custom_text(self, Itext, path:Path):
        text_out = Itext
        format_num = 0
        replace_list = []

        with open(path, 'r') as f:
            while (line := f.readline().strip().split(',')) != [""]:
                if line[0] in Itext:
                    text_out = text_out.replace(line[0], '{0['+str(format_num)+']}')
                    format_num += 1
                    replace_list.append(line[1])

        return text_out.format(replace_list)



    #-----------------------------------------------------------
    def _replace_english_kana(self):
        def replacer(match:re.Match) -> str:
            word:str = match.group()
            word_low = word.lower()
            
            if kana := alkana.get_kana(word_low):
                return kana
            if word_low == "i":
                return "あい"
            if re.search(r'[A-Z]', word):
                return word
            return Romaji.to_kana(word_low)

        # 全体の self.text に対して一括置換
        self.text = re_romaji_unit.sub(replacer, self.text)




    # ************************************************
    def _replace_w(self):
        self.text = re.sub(r'(ww+|ｗｗ+)','わらわら', self.text)
        self.text = re.sub(r'(w|ｗ)','わら', self.text)


    async def normalize_text(self, guild_id:int) -> None:                                            # コマンドは読み上げない
        self.text = re.sub(r'^\s+', ' ', self.text)
        self.text = re_url.sub('ユーアールエルは省略するのです！ ',self.text)                    # URL省略
        self.text = re_emoji.sub('',self.text)                                              # 絵文字IDは読み上げない
        self.text = re_mention.sub('メンションは省略するのです！ ',self.text)
        self.text = self._custom_text(self.text, Config.admin_dic)                      # ユーザ登録した文字を読み替える
        self.text = self._custom_text(self.text, Config.user_dic / f'{guild_id}.txt')
        self._replace_english_kana()
        self._replace_w()


    async def create_voice(self) -> None:
        await self.engines.create_voice(self)
        self.generated = True


    def delete_file(self):
        if os.path.isfile(self.out_path):
            os.remove(self.out_path)