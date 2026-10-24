from datetime import datetime
from io import BufferedIOBase
import re
from typing import TYPE_CHECKING, Optional

import alkana

from pi_yo_6.load_config import AdminDic, Config, GuildConfig
from pi_yo_6.romaji.to_kana import Romaji
from pi_yo_6.synthetic_voice import SyntheticEngines
from pi_yo_6.utils import VoiceUnit

if TYPE_CHECKING:
    import discord

re_user_mention = re.compile(r'<@!?(\d+)>')
re_role_mention = re.compile(r'<@&(\d+)>')
re_channel_mention = re.compile(r'<#(\d+)>')
re_emoji = re.compile(r'<a?:.+?:\d+>')
re_url = re.compile(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+')
re_romaji_unit = re.compile(r'\b([a-zA-Z\-]+)\b')  # (単語境界)(英単語)(単語境界)
re_code_block = re.compile(r'```[\s\S]*?```')
re_inline_code = re.compile(r'`[^`]+`')
re_spoiler = re.compile(r'\|\|[\s\S]*?\|\|')
re_inline_voice = re.compile(r'\bvoice:\s*([^\s]+)')
re_inline_speed = re.compile(r'\bspeed:\s*([\d.]+)')
re_inline_tone = re.compile(r'\btone:\s*([-\d.]+)')
re_inline_intonation = re.compile(r'\bintonation:\s*([-\d.]+)')


class MessageUnit:
    def __init__(self, text: str, time: Optional[datetime] = None) -> None:
        self.time = time or datetime.now()
        self.text: str = text
        self.voice = VoiceUnit()
        self.data: Optional[BufferedIOBase] = None
        self.generated = False

    def _custom_text(self, gid: int) -> None:
        if gid:
            gc = GuildConfig.get(gid)
            self.text = gc.data.dic.replace(self.text)
        if AdminDic.words:
            self.text = AdminDic.replace(self.text)

    # -----------------------------------------------------------
    def _replace_english_kana(self) -> None:
        def replacer(match: re.Match[str]) -> str:
            word: str = match.group()
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
    def _replace_w(self) -> None:
        self.text = re.sub(r'(ww+|ｗｗ+)', 'わらわら', self.text)
        self.text = re.sub(r'(w|ｗ)', 'わら', self.text)

    def _replace_mentions(self, guild: Optional["discord.Guild"]) -> None:
        if guild:

            def replace_user(m: re.Match[str]) -> str:
                uid = int(m.group(1))
                mem = guild.get_member(uid)
                return f"アット{mem.display_name} " if mem else "メンション "

            def replace_role(m: re.Match[str]) -> str:
                rid = int(m.group(1))
                role = guild.get_role(rid)
                return f"アット{role.name} " if role else "ロール "

            def replace_channel(m: re.Match[str]) -> str:
                cid = int(m.group(1))
                ch = guild.get_channel(cid)
                return f"{ch.name}チャンネル " if ch else "チャンネル "

            self.text = re_user_mention.sub(replace_user, self.text)
            self.text = re_role_mention.sub(replace_role, self.text)
            self.text = re_channel_mention.sub(replace_channel, self.text)
        else:
            self.text = re_user_mention.sub('メンション ', self.text)
            self.text = re_role_mention.sub('ロール ', self.text)
            self.text = re_channel_mention.sub('チャンネル ', self.text)

    def _extract_inline_voice(self) -> None:
        # voice:xxx_yyy or voice:xxx
        if m := re_inline_voice.search(self.text):
            voice_spec = m.group(1)
            self.text = re_inline_voice.sub('', self.text)
            if '_' in voice_spec:
                speaker_name, style_name = voice_spec.split('_', 1)
            else:
                speaker_name, style_name = voice_spec, None

            found = SyntheticEngines.current.find_voice(speaker_name, style_name)
            if found:
                self.voice.type = found.type
                self.voice.name = found.name
                self.voice.style = found.style

        # speed:xxx
        if m := re_inline_speed.search(self.text):
            try:
                spd = float(m.group(1))
                if 0.2 <= spd <= 5.0:
                    self.voice.speed = spd
                self.text = re_inline_speed.sub('', self.text)
            except ValueError:
                pass

        # tone:xxx
        if m := re_inline_tone.search(self.text):
            try:
                tn = float(m.group(1))
                if -50.0 <= tn <= 50.0:
                    self.voice.tone = tn
                self.text = re_inline_tone.sub('', self.text)
            except ValueError:
                pass

        # intonation:xxx
        if m := re_inline_intonation.search(self.text):
            try:
                into = float(m.group(1))
                if 0.0 <= into <= 5.0:
                    self.voice.intonation = into
                self.text = re_inline_intonation.sub('', self.text)
            except ValueError:
                pass

    async def normalize_text(
        self, guild_id: int | None = None, guild: Optional["discord.Guild"] = None
    ) -> None:  # コマンドは読み上げない
        self._extract_inline_voice()
        gid = guild.id if guild else (guild_id or 0)
        self.text = re.sub(r'^\s+', ' ', self.text)
        self.text = re_url.sub('ユーアールエルは省略するのです！ ', self.text)  # URL省略
        self.text = re_code_block.sub('コードブロック省略 ', self.text)  # コードブロック省略
        self.text = re_inline_code.sub('コード省略 ', self.text)  # インラインコード省略
        self.text = re_spoiler.sub('ネタバレ ', self.text)  # スポイラー
        self.text = re_emoji.sub('', self.text)  # 絵文字IDは読み上げない
        self._replace_mentions(guild)  # メンション名前解決
        self._custom_text(gid)  # ユーザ登録した文字を読み替える
        self._replace_english_kana()
        self._replace_w()

        # 文字数上限
        limit = Config.text_limit
        if len(self.text) > limit:
            self.text = self.text[:limit] + " 以下略"

    async def create_voice(self) -> None:
        await SyntheticEngines.current.create_voice(self)
        self.generated = self.data is not None
