import asyncio
import alkana
import re
import os
import wave
import platform

from .romaji.to_kana import Romaji
from .voicevox import core
from .voicevox.speaker_id import get_speaker_id
try: from ..config import Config
except Exception: pass


if platform.system() == 'Windows':
    EFormat = 'shift_jis'
else:
    EFormat = 'utf-8'

re_mention = re.compile(r'<(@&|@)\d+>')
re_emoji = re.compile(r'<:.+:[0-9]+>')
re_url = re.compile(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+')
re_bot_prefix = re.compile(r'^[,./?!].*')
re_speed = re.compile(r'speed:\S*\s|speed:\S*\Z')
re_a = re.compile(r'a:\S*\s|a:\S*\Z')
re_tone = re.compile(r'tone:\S*\s|tone:\S*\Z')
re_jf = re.compile(r'jf:\S*\s|jf:\S*\Z')
re_voice = re.compile(r'voice:\w*\s|voice:\w*\Z')
re_romaji_unit = re.compile(r'(^|[^a-zA-Z])([a-zA-Z\-]+)($|[^a-zA-Z])')
re_not_romaji = re.compile(r'[^a-zA-Z\-]')
_status = 'voice:\w*\s|speed:\S*\s|a:\S*\s|tone:\S*\s|jf:\S*\s'
re_text_status = re.compile(r'(^|{0})+.+?(?= ({0})|$)'.format(_status)) # [(^|_status) 癖の強い文字たち ($|_status)]

class GenerateVoice:
    def __init__(self, Config, VVox) -> None:
        try:
            self.Config:Config
        except Exception: pass
        self.Config = Config
        self.VVox = VVox


    def custam_text(self, path):
        text_out = self.Itext
        format_num = 0
        replace_list = []

        with open(path, 'r') as f:
            while (line := f.readline().strip().split(',')) != [""]:
                if line[0] in self.Itext:
                    text_out = text_out.replace(line[0], '{0['+str(format_num)+']}')
                    format_num += 1
                    replace_list.append(line[1])

        self.Itext = text_out.format(replace_list)


    #------------------------------------------------------
    def costom_voice(self):
        
        hts=['-m', self.Config.OJ.Voice+'mei_normal.htsvoice']
        
        if r := re_voice.findall(self.Itext):
            r = re.sub(r'\s',"",r[0])
            self.Itext = re.sub(r,'',self.Itext)
            r = re.sub('voice:','',r)

            _hts = self.Config.OJ.Voice+f'{r}.htsvoice'
            if os.path.isfile(_hts):
                hts = ['-m', _hts]
            else:
                hts = ['voicevox', r]
            
            
        return hts
        
    #------------------------------------------------------

    def costom_status(self, default, prefix, _re:re.Pattern):
        
        if r := _re.findall(self.Itext):
            r = re.sub(r'\s',"",r[0])
            self.Itext = re.sub(r,'',self.Itext)
            default[1] = re.sub(prefix,'',r)
        
        if default[1] == "auto":
            return ""
        else:
            return f"{default[0]} {default[1]}"


    #-----------------------------------------------------------
    def replace_english_kana(self):
        temp_text = self.Itext
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

        self.Itext = output + temp_text



    # ************************************************
    def replace_w(self):
        self.Itext = re.sub(r'(ww+|ｗｗ+)','わらわら',self.Itext)
        self.Itext = re.sub(r'(w|ｗ)','わら',self.Itext)


    async def creat_voice(self, Itext:str, guild_id, now_time):

        Itext = Itext.replace('\n',' ')
        Itext = re.sub(re_bot_prefix,'',Itext)                                                              # コマンドは読み上げない
        Itext = re.sub(re_url,'ユーアールエルは省略するのです！ ',Itext)    # URL省略
        Itext = re.sub(re_emoji,'',Itext)                                                            # 絵文字IDは読み上げない
        self.Itext = re.sub(re_mention,'メンションは省略するのです！ ',Itext)
        self.custam_text(self.Config.Admin_dic)                                           # ユーザ登録した文字を読み替える
        self.custam_text(self.Config.User_dic + guild_id + '.txt')


        ItextTemp = re_text_status.finditer(self.Itext)
        ItextTemp = [_.group() for _ in ItextTemp]

        if ItextTemp == []:

            self.replace_english_kana()
            self.replace_w()
            print(f"変換後:{self.Itext}")
            
            cmd = f'open_jtalk -x "{self.Config.OJ.Dic}" -m "{self.Config.OJ.Voice}mei_normal.htsvoice" -r 1.2 -ow "{self.Config.OJ.Output}{guild_id}-{now_time}.wav"'
            #print(cmd)
            prog = await asyncio.create_subprocess_shell(cmd,stdin=asyncio.subprocess.PIPE)
            await prog.communicate(input= Itext.encode(EFormat))


        else:
            FileNum = 0
            gather_wav = []
            for Itext in ItextTemp:
                gather_wav.append(self.split_voice(FileNum,f'{guild_id}-{now_time}'))
                FileNum += 1
            await asyncio.gather(*gather_wav)

            with wave.open(self.Config.OJ.Output+guild_id+"-"+now_time+".wav", 'wb') as wav_out:
                for Num in range(FileNum):
                    path = f"{self.Config.OJ.Output}{guild_id}-{now_time}-{str(Num)}.wav"
                    with wave.open(path, 'rb') as wav_in:
                        if not wav_out.getnframes():
                            wav_out.setparams(wav_in.getparams())
                        wav_out.writeframes(wav_in.readframes(wav_in.getnframes()))
                    if os.path.isfile(path):
                        os.remove(path)


    async def split_voice(self, FileNum, id_time):
        hts = self.costom_voice()                                   #voice
        speed = self.costom_status(['-r','1.2'],"speed:",re_speed)  #speed
        a = self.costom_status(['-a','auto'],"a:",re_a)             #AllPath
        tone = self.costom_status(['-fm','auto'],"tone:",re_tone)   #tone
        jf = self.costom_status(['-jf','auto'],"jf:",re_jf)         #jf

        self.replace_english_kana()
        self.replace_w()
        print(f"変換後 ({FileNum+1}) :{self.Itext}")
        FileName = self.Config.OJ.Output+id_time+"-"+str(FileNum)+".wav"

        if hts[0] == '-m':
            hts = ' '.join(hts)
            
            cmd=f'open_jtalk -x "{self.Config.OJ.Dic}" -ow "{FileName}" {hts} {speed} {tone} {jf} {a}'
            
            prog = await asyncio.create_subprocess_shell(cmd,stdin=asyncio.subprocess.PIPE)
            await prog.communicate(input= self.Itext.encode(EFormat))

        else:
            speaker_id = get_speaker_id(hts[1])
            if speaker_id == None: return
            elif not 0 <= speaker_id <= 38: return
            loop = asyncio.get_event_loop()
            wavefmt = await loop.run_in_executor(None, self.VVox.voicevox_tts, self.Itext, speaker_id)
            with open(FileName, 'wb')as f:
                f.write(wavefmt)
            