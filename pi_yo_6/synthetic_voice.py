import asyncio
import alkana
import logging
import requests
import uuid
import re
import os
from discord import Message
from typing import Optional, List

from .utils import MessageUnit
from .romaji.to_kana import Romaji
from .voicevox.core import CreateVoicevox, VoicevoxEngineBase
from .open_jtalk.core import CreateOpenJtalk

from config import Config


_log = logging.getLogger(__name__)


re_mention = re.compile(r'<(@&|@)\d+>')
re_emoji = re.compile(r'<:.+:[0-9]+>')
re_url = re.compile(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+')
re_speed = re.compile(r'(^|\s)speed:([\d.]*)(?=\s|$)')
re_a = re.compile(r'(^|\s)a:([\d.]*)(?=\s|$)')
re_tone = re.compile(r'(^|\s)tone:([\d.]*)(?=\s|$)')
re_int = re.compile(r'(^|\s)intnation:([\d.]*)(?=\s|$)')
re_voice = re.compile(r'(^|\s)voice:(\S*)(?=\s|$)')
re_romaji_unit = re.compile(r'(^|[^a-zA-Z])([a-zA-Z\-]+)($|[^a-zA-Z])')
re_not_romaji = re.compile(r'[^a-zA-Z\-]')
_status = 'voice:\S*\s|speed:\S*\s|a:\S*\s|tone:\S*\s|intnation:\S*\s'
re_text_status = re.compile(r'({0}|^)+.+?(?=\s({0})|$)'.format(_status)) # [(^|_status) 癖の強い文字たち ($|_status)]







class SyntheticEngines:
    def __init__(self) -> None:


        try:
            self.voicevox = None
            if Config.Vvox.enable:
                self.voicevox: Optional[CreateVoicevox] = CreateVoicevox(Config.Vvox)
                res = requests.get(f'{self.voicevox.url_base}/core_versions')
                engine_ver = res.json()[0]

                res = requests.get('https://api.github.com/repos/VOICEVOX/voicevox_core/releases/latest').json()
                _log.info(f'Loaded Voicevox!! - Ver.{engine_ver}')
                if engine_ver == res['tag_name']:
                    _log.info(f'最新バージョンです')
                else:
                    _log.warning(f'最新バージョンは {res["tag_name"]} です {res["html_url"]}')

        except Exception as e:
            _log.warning(f'\033[0mVoiceVoxの読み込みに失敗しました。 : {e}')
            self.voicevox = None

        try:
            self.coeiroink = None
            if Config.Coeiroink.enable:
                self.coeiroink: Optional[VoicevoxEngineBase] = VoicevoxEngineBase(Config.Coeiroink)
                _log.info('Loaded Coeiroink!!')
        except Exception as e:
            _log.warning(f'\033[0mCoeiroinkの読み込みに失敗しました。 : {e}')
            self.coeiroink = None

        try:
            self.open_jtalk = None
            if Config.OJ.enable:
                self.open_jtalk = CreateOpenJtalk()
                _log.info('Loaded Open_Jtalk!!')
        except Exception as e:
            _log.warning(f'Open Jtakの読み込みに失敗 : {e}')
            self.open_jtalk = None


    async def create_voice(self, Itext:MessageUnit, out):
        _type = Itext.speaker.type


        if _type == 'open_jtalk':
            if not self.open_jtalk: return

            Itext.out_path = out
            Itext.speaker = Itext.speaker.id
            if Itext.speed == None:
                Itext.speed = 1.2

            if (tone := Itext.tone) != None:
                Itext.tone = f' -fm {tone}'
            else:
                Itext.tone = ''

            if (intnation := Itext.intnation) != None:
                Itext.intnation = f' -jf {intnation}'
            else:
                Itext.intnation = ''

            if (a := Itext.a) != None:
                Itext.a = f' -a {a}'
            else:
                Itext.a = ''

            if Itext.out_path == None:
                Itext.out_path = f"{Config.output}output.wav"

            await self.open_jtalk.create_voice(Itext)



        elif _type == 'voicevox':
            if not self.voicevox: return

            speaker = Itext.speaker.id
            if (speaker := self.voicevox.to_speaker_id(speaker)) == None:
                return
            Itext.speaker = speaker

            with open(out, 'wb')as f:
                f.write( await self.voicevox.create_voice(Itext))



        elif _type == 'coeiroink':
            if not self.coeiroink: return

            speaker = Itext.speaker.id
            if (speaker := self.coeiroink.to_speaker_id(speaker)) == None:
                return
            Itext.speaker = speaker

            if Itext.speed == None:
                Itext.speed = 1.0
            if Itext.tone == None:
                Itext.tone = 0.0
            if Itext.intnation == None:
                Itext.intnation = 1.0

            with open(out, 'wb')as f:
                f.write( await self.coeiroink.create_voice(Itext))







class GenerateVoice:
    def __init__(self, engines:SyntheticEngines) -> None:
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
    def costom_voice(self, Itext:MessageUnit):
        
        _type = 'open_jtalk'
        _id = str( self.engines.open_jtalk.hts_path / 'mei_normal.htsvoice' )
        
        r:List[re.Match] = list(re_voice.finditer(Itext.text))
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
            
        Itext.speaker.type = _type
        Itext.speaker.id = _id
        return Itext
        
    #------------------------------------------------------

    def costom_status(self, Itext:MessageUnit, default, _re:re.Pattern):
        
        r = list(_re.finditer(Itext.text))
        if len(r) != 0:
            Itext.text = _re.sub('',Itext.text)
            setattr(Itext, default, r[-1].group(2))

        return Itext


    #-----------------------------------------------------------
    def replace_english_kana(self, Itext:MessageUnit):
        text = Itext.text
        output = ""

        # 先頭から順番に英単語を検索しカタカナに変換
        while re_word := re_romaji_unit.search(text):
            word = re_word.group(2)
            word_low = word.lower()

            if re_word.start() != 0 or re_not_romaji.search(text[0]):    # 文字のスタート位置修復
                output += text[:re_word.start()+1]

            if kana := alkana.get_kana(word_low):      # 英語変換
                output += kana
            elif word_low == "i":
                output += "あい"
            elif re.search(r'[A-Z]',word):
                output += word
            else:
                output += Romaji.to_kana(word_low)   # ローマ字 → カナ 変換
            
            if re_word.end() != len(text) or re_not_romaji.search(text[-1]):    # 文字の末尾を修復
                text = text[re_word.end()-1:]
            else:
                text = ""

        Itext.text = output + text



    # ************************************************
    def replace_w(self, Itext:MessageUnit):
        text = Itext.text
        text = re.sub(r'(ww+|ｗｗ+)','わらわら', text)
        text = re.sub(r'(w|ｗ)','わら', text)
        Itext.text = text


    async def creat_voice(self, Itext:str, message:Message):
        Itext = Itext.replace('\n',' ')                                             # コマンドは読み上げない
        Itext = re_url.sub('ユーアールエルは省略するのです！ ',Itext)                    # URL省略
        Itext = re_emoji.sub('',Itext)                                              # 絵文字IDは読み上げない
        Itext = re_mention.sub('メンションは省略するのです！ ',Itext)
        Itext = self.custam_text(Itext, Config.admin_dic)                      # ユーザ登録した文字を読み替える
        Itext = self.custam_text(Itext, f'{Config.user_dic}{message.guild.id}.txt')
        out = await self.raw_create_voice(Itext, message.id)
        return out


    async def raw_create_voice(self, text:str, _id=uuid.uuid4()):
        out_wav = []
        gather_wav = []
        for num, re_text in enumerate(re_text_status.finditer(text)):
            text = re_text.group()
            out = f'{Config.output}{_id}-{num}.wav'
            gather_wav.append(self.split_voice(text, out))
            out_wav.append(out)

        await asyncio.gather(*gather_wav)
        return out_wav


    async def split_voice(self, text, out_name):
        Itext = MessageUnit(text)
        self.costom_voice(Itext)                        #voice
        self.costom_status(Itext, 'speed', re_speed)    #speed
        self.costom_status(Itext, 'a', re_a)            #AllPath
        self.costom_status(Itext, 'tone', re_tone)      #tone
        self.costom_status(Itext, 'intnation', re_int)
        Itext.text = re.sub(r'^\s+', '', Itext.text)

        self.replace_english_kana(Itext)
        self.replace_w(Itext)

        await self.engines.create_voice(Itext, out_name)

