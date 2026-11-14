import re
from typing import TYPE_CHECKING, Callable, Optional

import alkana

from pi_yo_6 import config
from pi_yo_6.models import VoiceSetting
from pi_yo_6.text.romaji import RomajiConverter

if TYPE_CHECKING:
    import discord

_RE_USER_MENTION = re.compile(r'<@!?(\d+)>')
_RE_ROLE_MENTION = re.compile(r'<@&(\d+)>')
_RE_CHANNEL_MENTION = re.compile(r'<#(\d+)>')
_RE_EMOJI = re.compile(r'<a?:.+?:\d+>')
_RE_URL = re.compile(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+')
_RE_ENGLISH_WORD = re.compile(r'\b([a-zA-Z\-]+)\b')
_RE_CODE_BLOCK = re.compile(r'```[\s\S]*?```')
_RE_INLINE_CODE = re.compile(r'`[^`]+`')
_RE_SPOILER = re.compile(r'\|\|[\s\S]*?\|\|')

_RE_INLINE_VOICE = re.compile(r'\bvoice:\s*([^\s]+)')
_RE_INLINE_SPEED = re.compile(r'\bspeed:\s*([\d.]+)')
_RE_INLINE_TONE = re.compile(r'\btone:\s*([-\d.]+)')
_RE_INLINE_INTONATION = re.compile(r'\bintonation:\s*([-\d.]+)')

VoiceResolver = Callable[[str, str | None], VoiceSetting | None]


class TextNormalizer:
    """Discordメッセージから読み上げ用テキストとボイス設定を抽出・正規化する"""

    @staticmethod
    def extract_message_text(message: "discord.Message") -> str:
        """メッセージ本文・添付ファイル・スタンプを結合して読み上げ元テキストを生成"""
        parts: list[str] = []
        if message.content:
            parts.append(message.content)

        if message.attachments:
            attach_types: list[str] = []
            for a in message.attachments:
                ctype = a.content_type or ""
                if ctype.startswith("image/"):
                    attach_types.append("画像")
                elif ctype.startswith("video/"):
                    attach_types.append("動画")
                elif ctype.startswith("audio/"):
                    attach_types.append("音声")
                else:
                    attach_types.append("ファイル")
            if attach_types:
                parts.append(f"{'と'.join(attach_types)}が送信されました")

        if message.stickers:
            sticker_names = [s.name for s in message.stickers]
            parts.append(f"スタンプ、{', '.join(sticker_names)}")

        return " ".join(parts).strip()

    @staticmethod
    def normalize(
        text: str,
        voice: VoiceSetting,
        guild: Optional["discord.Guild"] = None,
        guild_id: int | None = None,
        voice_resolver: Optional[VoiceResolver] = None,
    ) -> tuple[str, VoiceSetting]:
        """テキストの正規化とインライン声帯パラメータの抽出を行う（元のVoiceSettingは変更しない）"""
        updated_voice = voice.model_copy()
        text = TextNormalizer._extract_inline_voice(text, updated_voice, voice_resolver)

        gid = guild.id if guild else (guild_id or 0)
        text = re.sub(r'^\s+', ' ', text)
        text = _RE_URL.sub('ユーアールエルは省略するのです！ ', text)
        text = _RE_CODE_BLOCK.sub('コードブロック省略 ', text)
        text = _RE_INLINE_CODE.sub('コード省略 ', text)
        text = _RE_SPOILER.sub('ネタバレ ', text)
        text = _RE_EMOJI.sub('', text)
        text = TextNormalizer._replace_mentions(text, guild)
        text = TextNormalizer._apply_dictionaries(text, gid)
        text = TextNormalizer._replace_english_kana(text)
        text = TextNormalizer._replace_w(text)

        limit = config.app_config.text_limit
        if len(text) > limit:
            text = text[:limit] + " 以下略"

        return text, updated_voice

    @staticmethod
    def _extract_inline_voice(
        text: str,
        voice: VoiceSetting,
        voice_resolver: Optional[VoiceResolver],
    ) -> str:
        if m := _RE_INLINE_VOICE.search(text):
            voice_spec = m.group(1)
            text = _RE_INLINE_VOICE.sub('', text)
            if '_' in voice_spec:
                speaker_name, style_name = voice_spec.split('_', 1)
            else:
                speaker_name, style_name = voice_spec, None

            if voice_resolver:
                found = voice_resolver(speaker_name, style_name)
                if found:
                    voice.type = found.type
                    voice.name = found.name
                    voice.style = found.style

        if m := _RE_INLINE_SPEED.search(text):
            try:
                spd = float(m.group(1))
                if 0.2 <= spd <= 5.0:
                    voice.speed = spd
                text = _RE_INLINE_SPEED.sub('', text)
            except ValueError:
                pass

        if m := _RE_INLINE_TONE.search(text):
            try:
                tn = float(m.group(1))
                if -50.0 <= tn <= 50.0:
                    voice.tone = tn
                text = _RE_INLINE_TONE.sub('', text)
            except ValueError:
                pass

        if m := _RE_INLINE_INTONATION.search(text):
            try:
                into = float(m.group(1))
                if 0.0 <= into <= 5.0:
                    voice.intonation = into
                text = _RE_INLINE_INTONATION.sub('', text)
            except ValueError:
                pass

        return text

    @staticmethod
    def _replace_mentions(text: str, guild: Optional["discord.Guild"]) -> str:
        if guild:

            def replace_user(m: re.Match[str]) -> str:
                mem = guild.get_member(int(m.group(1)))
                return f"アット{mem.display_name} " if mem else "メンション "

            def replace_role(m: re.Match[str]) -> str:
                role = guild.get_role(int(m.group(1)))
                return f"アット{role.name} " if role else "ロール "

            def replace_channel(m: re.Match[str]) -> str:
                ch = guild.get_channel(int(m.group(1)))
                return f"{ch.name}チャンネル " if ch else "チャンネル "

            text = _RE_USER_MENTION.sub(replace_user, text)
            text = _RE_ROLE_MENTION.sub(replace_role, text)
            text = _RE_CHANNEL_MENTION.sub(replace_channel, text)
        else:
            text = _RE_USER_MENTION.sub('メンション ', text)
            text = _RE_ROLE_MENTION.sub('ロール ', text)
            text = _RE_CHANNEL_MENTION.sub('チャンネル ', text)
        return text

    @staticmethod
    def _apply_dictionaries(text: str, gid: int) -> str:
        if gid:
            gc = config.guild_configs.get(gid)
            text = gc.data.dic.replace(text)
        if config.admin_dic.words:
            text = config.admin_dic.replace(text)
        return text

    @staticmethod
    def _replace_english_kana(text: str) -> str:
        def replacer(match: re.Match[str]) -> str:
            word = match.group()
            word_low = word.lower()
            if kana := alkana.get_kana(word_low):
                return kana
            if word_low == "i":
                return "あい"
            if re.search(r'[A-Z]', word):
                return word
            return RomajiConverter.to_kana(word_low)

        return _RE_ENGLISH_WORD.sub(replacer, text)

    @staticmethod
    def _replace_w(text: str) -> str:
        text = re.sub(r'(ww+|ｗｗ+)', 'わらわら', text)
        text = re.sub(r'(w|ｗ)', 'わら', text)
        return text
