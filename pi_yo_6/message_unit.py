from datetime import datetime
import os
from pathlib import Path
import re
from typing import TYPE_CHECKING
import uuid

import alkana

from pi_yo_6.config import Config
from pi_yo_6.load_config import GuildConfig
from pi_yo_6.romaji.to_kana import Romaji
from pi_yo_6.utils import VoiceUnit

if TYPE_CHECKING:
    from pi_yo_6.synthetic_voice import SyntheticEngines


re_mention = re.compile(r'<(@&|@)\d+>')
re_emoji = re.compile(r'<:.+:[0-9]+>')
re_url = re.compile(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+')
re_romaji_unit = re.compile(r'\b([a-zA-Z\-]+)\b') #(単語境界)(英単語)(単語境界)


class MessageUnit:
    def __init__(self, text:str, engines:"SyntheticEngines", time:datetime = datetime.now()) -> None:
        self.time = time
        self.engines = engines
        self.text:str = text
        self.voice = VoiceUnit()
        self.out_path:Path = Config.output / f'{uuid.uuid4()}.wav'
        self.generated = False


    def _custom_text(self, gid:int) -> None:
        gc = GuildConfig.get(gid)
        self.text = gc.data.dic.replace(self.text)


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
        self._custom_text(guild_id)                      # ユーザ登録した文字を読み替える
        self._replace_english_kana()
        self._replace_w()


    async def create_voice(self) -> None:
        await self.engines.create_voice(self)
        self.generated = True


    def delete_file(self):
        if os.path.isfile(self.out_path):
            os.remove(self.out_path)