import asyncio
import alkana
import re
import os
from discord import Message
from platform import system

from .romaji.to_kana import Romaji
from .voicevox.speaker_id import get_speaker_id

_os = system().lower()
if _os == 'windows':
    EFormat = 'shift_jis'
else:
    EFormat = 'utf-8'

re_mention = re.compile(r'<(@&|@)\d+>')
re_emoji = re.compile(r'<:.+:[0-9]+>')
re_url = re.compile(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+')
re_speed = re.compile(r'(^|\s)speed:([\d.]*)(?=\s|$)')
re_a = re.compile(r'(^|\s)a:([\d.]*)(?=\s|$)')
re_tone = re.compile(r'(^|\s)tone:([\d.]*)(?=\s|$)')
re_jf = re.compile(r'(^|\s)jf:([\d.]*)(?=\s|$)')
re_voice = re.compile(r'(^|\s)voice:([\w.]*)(?=\s|$)')
re_romaji_unit = re.compile(r'(^|[^a-zA-Z])([a-zA-Z\-]+)($|[^a-zA-Z])')
re_not_romaji = re.compile(r'[^a-zA-Z\-]')
_status = 'voice:\w*\s|speed:\S*\s|a:\S*\s|tone:\S*\s|jf:\S*\s'
re_text_status = re.compile(r'({0}|^)+.+?(?=\s({0})|$)'.format(_status)) # [(^|_status) 癖の強い文字たち ($|_status)]

class GenerateVoice:
    def __init__(self, config, VVox) -> None:
        try: 
            from .template._config import Config
            from .voicevox.core import CreateVOICEVOX
            self.Config:Config
            self.VVox: CreateVOICEVOX
        except Exception: pass
        self.Config = config
        self.VVox = VVox


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
        
        hts=['-m', self.Config.OJ.Voice+'mei_normal.htsvoice']
        
        r = list(re_voice.finditer(Itext))
        if len(r) != 0:
            Itext = re_voice.sub('',Itext)
            r = r[-1].group(2)

            _hts = self.Config.OJ.Voice+f'{r}.htsvoice'
            if os.path.isfile(_hts):
                hts = ['-m', _hts]
            else:
                hts = ['voicevox', r]
            
        return Itext, hts
        
    #------------------------------------------------------

    def costom_status(self, Itext, default, _re:re.Pattern):
        
        r = list(_re.finditer(Itext))
        if len(r) != 0:
            Itext = _re.sub('',Itext)
            default[1] = r[-1].group(2)
        
        if default[1] == "auto":
            return Itext, ""
        else:
            return Itext, f"{default[0]} {default[1]}"


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
        Itext = self.custam_text(Itext, self.Config.Admin_dic)                      # ユーザ登録した文字を読み替える
        Itext = self.custam_text(Itext, f'{self.Config.User_dic}{message.guild.id}.txt')

        out_wav = gather_wav = []
        for num, Itext in enumerate(re_text_status.finditer(Itext)):
            Itext = Itext.group()
            out = f'{self.Config.OJ.Output}{message.id}-{num}.wav'
            gather_wav.append(self.split_voice(Itext, out))
            out_wav.append(out)

        await asyncio.gather(*gather_wav)
        return out_wav


    async def split_voice(self, Itext, out_name):
        Itext, hts = self.costom_voice(Itext)                               #voice
        Itext, speed = self.costom_status(Itext, ['-r','1.2'], re_speed)    #speed
        Itext, a = self.costom_status(Itext, ['-a','auto'], re_a)           #AllPath
        Itext, tone = self.costom_status(Itext, ['-fm','auto'], re_tone)    #tone
        Itext, jf = self.costom_status(Itext, ['-jf','auto'], re_jf)        #jf
        Itext = re.sub(r'^\s+', '', Itext)

        Itext = self.replace_english_kana(Itext)
        Itext = self.replace_w(Itext)
        #print(f"変換後 ({FileNum+1}) :") #{Itext}

        if hts[0] == '-m':
            hts = ' '.join(hts)
            
            if _os == 'windows':
                dic = self.Config.OJ.Dic_shift_jis
            else:
                dic = self.Config.OJ.Dic_utf_8
            cmd=f'open_jtalk -x "{dic}" -ow "{out_name}" {hts} {speed} {tone} {jf} {a}'
            
            prog = await asyncio.create_subprocess_shell(cmd,stdin=asyncio.subprocess.PIPE)
            await prog.communicate(input= Itext.encode(EFormat))

        else:
            speaker_id = get_speaker_id(hts[1])
            if speaker_id == None: return
            elif not 0 <= speaker_id <= 38: return
            
            with open(out_name, 'wb')as f:
                f.write( await self.VVox.create_voicevox(Itext, speaker_id, out_name))