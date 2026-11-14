from dataclasses import dataclass, field
from datetime import datetime
import enum
from typing import TypedDict

from pydantic import BaseModel


class NoMetasError(Exception):
    """再生可能な音声メタデータが見つからない場合の例外"""


class StyleMeta(TypedDict):
    name: str
    id: str


class SpeakerMeta(TypedDict):
    name: str
    styles: list[StyleMeta]


class EngineType(str, enum.Enum):
    OPEN_JTALK = 'open_jtalk'
    VOICEVOX = 'voicevox'
    COEIROINK = 'coeiroink'


class VoiceSetting(BaseModel):
    type: EngineType = EngineType.OPEN_JTALK
    name: str = ""
    style: str = ""
    speed: float = 1.2
    tone: float = 0.0
    """ピッチ (OpenJTalk: 半音単位, VOICEVOX/Coeiroink: pitchScale)"""
    intonation: float = 0.0

    def __str__(self) -> str:
        return (
            f"**Engine**: `{self.type.value}`\n"
            f"**Voice**: `{self.name}` (`{self.style}`)\n"
            f"**Speed**: `{self.speed}` / **Tone**: `{self.tone}` / **Intonation**: `{self.intonation}`"
        )


@dataclass
class SpeechItem:
    """読み上げキューに投入される1件のテキストとボイス設定"""

    text: str
    voice: VoiceSetting = field(default_factory=VoiceSetting)
    created_at: datetime = field(default_factory=datetime.now)
