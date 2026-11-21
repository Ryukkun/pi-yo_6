import io
from typing import Protocol

from pi_yo_6.models import SpeakerMeta, VoiceSetting


class TTSEngine(Protocol):
    """音声合成エンジンの共通インターフェース"""

    metas: list[SpeakerMeta]

    async def synthesize(self, text: str, voice: VoiceSetting) -> io.BytesIO | None:
        """テキストとボイス設定からWAVデータのBytesIOを生成する"""
        ...

    def to_speaker_id(self, voice: VoiceSetting) -> str | int | None:
        """ボイス設定に対応するスピーカーIDを返す"""
        ...
