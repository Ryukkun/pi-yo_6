

import asyncio
from dataclasses import dataclass
import enum
import re
import uuid

import alkana
from discord import Guild, Optional

from pi_yo_6.config import Config
from pi_yo_6.romaji.to_kana import Romaji
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


class ENGINE_TYPE(enum.Enum):
    OPEN_JTALK = 'open_jtalk'
    VOICEVOX = 'voicevox'
    COEIROINK = 'coeiroink'

@dataclass
class _SpeakerUnit:
    type:ENGINE_TYPE = ENGINE_TYPE.OPEN_JTALK
    id:str = ""


class MessageUnit:
    def __init__(self, text:str, engines:SyntheticEngines) -> None:
        self.engines = engines
        self.text:str = text
        self.speaker = _SpeakerUnit()
        self.speed:Optional[str] = None
        self.a:str = ""
        self.tone:str = ""
        self.intnation:str = ""
        self.out_path:Optional[str] = None


    def _custom_text(self, Itext, path):
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


    #------------------------------------------------------
    def _set_voice(self):
        _type = 'open_jtalk'
        _id = str( Config.OpenJtalk.hts_path / 'mei_normal.htsvoice' )
        
        r:list[re.Match] = list(re_voice.finditer(Itext.text))
        if len(r) != 0:
            Itext.text = re_voice.sub('',Itext.text)
            r = r[-1].group(2).lower()

            _hts = self.engines.open_jtalk.hts_path / f'{r}.htsvoice'
            if _hts.is_file():
                _type = 'open_jtalk'
                _id = str(_hts)
            elif re.match(r'v.*?:', r):
                r = re.sub(r'v.*?:','', r)
                _type = 'voicevox'
                _id = r
            elif re.match(r'c.*?:', r):
                r = re.sub(r'c.*?:','', r)
                _type = 'coeiroink'
                _id = r
            
        self.speaker.type = _type
        self.speaker.id = _id
        



    #-----------------------------------------------------------
    def _replace_english_kana(self):
        text = self.text
        output = ""

        # 先頭から順番に英単語を検索しカタカナに変換
        while text and (re_word := re_romaji_unit.search(text)):
            word = re_word.group()
            word_low = word.lower()

            if re_word.start() != 0:
                output += text[:re_word.start()+1]

            if kana := alkana.get_kana(word_low):      # 英語変換
                output += kana
            elif word_low == "i":
                output += "あい"
            elif re.search(r'[A-Z]',word):
                output += word
            else:
                output += Romaji.to_kana(word_low)   # ローマ字 → カナ 変換
            
            if re_word.end() != len(text):
                text = text[re_word.end()-1:]
            else:
                text = ""

        self.text = output + text




    # ************************************************
    def _replace_w(self):
        self.text = re.sub(r'(ww+|ｗｗ+)','わらわら', self.text)
        self.text = re.sub(r'(w|ｗ)','わら', self.text)


    async def normalize_text(self, guild_id:int) -> None:                                            # コマンドは読み上げない
        if self.text is not None:
            self.text = re.sub(r'^\s+', ' ', self.text)
        self.text = re_url.sub('ユーアールエルは省略するのです！ ',self.text)                    # URL省略
        self.text = re_emoji.sub('',self.text)                                              # 絵文字IDは読み上げない
        self.text = re_mention.sub('メンションは省略するのです！ ',self.text)
        self.text = self._custom_text(self.text, Config.admin_dic)                      # ユーザ登録した文字を読み替える
        self.text = self._custom_text(self.text, f'{Config.user_dic}{guild_id}.txt')
        self._replace_english_kana()
        self._replace_w()


    async def create_voice(self):
        out_file_name = f'{Config.output}{uuid.uuid4()}.wav'
        self._set_voice()
        await self.engines.create_voice(self, out_file_name)
        return out_file_name