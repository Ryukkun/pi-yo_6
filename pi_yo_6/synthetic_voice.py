import asyncio
import alkana
import re
import os
from discord import Message

from .romaji.to_kana import Romaji
from config import Config


re_mention = re.compile(r'<(@&|@)\d+>')
re_emoji = re.compile(r'<:.+:[0-9]+>')
re_url = re.compile(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+')
re_speed = re.compile(r'(^|\s)speed:([\d.]*)(?=\s|$)')
re_a = re.compile(r'(^|\s)a:([\d.]*)(?=\s|$)')
re_tone = re.compile(r'(^|\s)tone:([\d.]*)(?=\s|$)')
re_int = re.compile(r'(^|\s)intnation:([\d.]*)(?=\s|$)')
re_voice = re.compile(r'(^|\s)voice:([\w.:]*)(?=\s|$)')
re_romaji_unit = re.compile(r'(^|[^a-zA-Z])([a-zA-Z\-]+)($|[^a-zA-Z])')
re_not_romaji = re.compile(r'[^a-zA-Z\-]')
_status = 'voice:\S*\s|speed:\S*\s|a:\S*\s|tone:\S*\s|intnation:\S*\s'
re_text_status = re.compile(r'({0}|^)+.+?(?=\s({0})|$)'.format(_status)) # [(^|_status) 癖の強い文字たち ($|_status)]

class GenerateVoice:
    def __init__(self, engines) -> None:
        try: 
            from .systhetic_engines import SyntheticEngines
            self.engines: SyntheticEngines
        except Exception: pass
        self.engines = engines


    def custam_text(self, Itext, path):
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
    def costom_voice(self, Itext):
        
        _type = 'open_jtalk'
        _id = Config.OJ.Voice+'mei_normal.htsvoice'
        
        r = list(re_voice.finditer(Itext['text']))
        if len(r) != 0:
            Itext['text'] = re_voice.sub('',Itext['text'])
            r = r[-1].group(2).lower()

            _hts = Config.OJ.Voice+f'{r}.htsvoice'
            if os.path.isfile(_hts):
                _type = 'open_jtalk'
                _id = _hts
            elif re.match(r'v.*?:', r):
                r = re.sub(r'v.*?:','', r)
                _type = 'voicevox'
                _id = r
            elif re.match(r'c.*?:', r):
                r = re.sub(r'c.*?:','', r)
                _type = 'coeiroink'
                _id = r
            
        Itext['hts'] = {'type':_type, 'id':_id}
        return Itext
        
    #------------------------------------------------------

    def costom_status(self, Itext, default, _re:re.Pattern):
        
        r = list(_re.finditer(Itext['text']))
        if len(r) != 0:
            Itext['text'] = _re.sub('',Itext['text'])
            Itext[default] = r[-1].group(2)
        
        return Itext


    #-----------------------------------------------------------
    def replace_english_kana(self, Itext):
        temp_text = Itext
        output = ""

        # 先頭から順番に英単語を検索しカタカナに変換
        while word := re_romaji_unit.search(temp_text):
            _word = word.group(2)
            _word_low = _word.lower()

            if word.start() != 0 or re_not_romaji.search(temp_text[0]):    # 文字のスタート位置修復
                output += temp_text[:word.start()+1]

            if kana := alkana.get_kana(_word_low):      # 英語変換
                output += kana
            elif _word_low == "i":
                output += "あい"
            elif re.search(r'[A-Z]',_word):
                output += _word
            else:
                output += Romaji.to_kana(_word_low)   # ローマ字 → カナ 変換
            
            if word.end() != len(temp_text) or re_not_romaji.search(temp_text[-1]):    # 文字の末尾を修復
                temp_text = temp_text[word.end()-1:]
            else:
                temp_text = ""

        return output + temp_text



    # ************************************************
    def replace_w(self, Itext):
        Itext = re.sub(r'(ww+|ｗｗ+)','わらわら', Itext)
        return re.sub(r'(w|ｗ)','わら', Itext)


    async def creat_voice(self, Itext:str, message:Message):
        Itext = Itext.replace('\n',' ')                                             # コマンドは読み上げない
        Itext = re_url.sub('ユーアールエルは省略するのです！ ',Itext)                    # URL省略
        Itext = re_emoji.sub('',Itext)                                              # 絵文字IDは読み上げない
        Itext = re_mention.sub('メンションは省略するのです！ ',Itext)
        Itext = self.custam_text(Itext, Config.admin_dic)                      # ユーザ登録した文字を読み替える
        Itext = self.custam_text(Itext, f'{Config.User_dic}{message.guild.id}.txt')

        out_wav = []
        gather_wav = []
        for num, Itext in enumerate(re_text_status.finditer(Itext)):
            Itext = Itext.group()
            out = f'{Config.OJ.output}{message.id}-{num}.wav'
            gather_wav.append(self.split_voice(Itext, out))
            out_wav.append(out)

        await asyncio.gather(*gather_wav)
        return out_wav


    async def split_voice(self, text, out_name):
        Itext = {"text": text}
        Itext = self.costom_voice(Itext)                        #voice
        Itext = self.costom_status(Itext, 'speed', re_speed)    #speed
        Itext = self.costom_status(Itext, 'a', re_a)            #AllPath
        Itext = self.costom_status(Itext, 'tone', re_tone)      #tone
        Itext = self.costom_status(Itext, 'intnation', re_int)
        Itext['text'] = re.sub(r'^\s+', '', Itext['text'])

        Itext['text'] = self.replace_english_kana(Itext['text'])
        Itext['text'] = self.replace_w(Itext['text'])
        #print(f"変換後 ({FileNum+1}) :") #{Itext}

        await self.engines.create_voice(Itext, out_name)