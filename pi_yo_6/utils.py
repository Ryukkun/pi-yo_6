import enum
from typing import TypedDict

from pydantic import BaseModel


class NoMetas(Exception):
    pass


class StyleMeta(TypedDict):
    name: str
    id: str


class SpeakerMeta(TypedDict):
    name: str
    styles: list[StyleMeta]


class ENGINE_TYPE(str, enum.Enum):
    OPEN_JTALK = 'open_jtalk'
    VOICEVOX = 'voicevox'
    COEIROINK = 'coeiroink'


class VoiceUnit(BaseModel):
    type: ENGINE_TYPE = ENGINE_TYPE.OPEN_JTALK
    name: str = ""
    style: str = ""
    speed: float = 1.2
    tone: float = 0.0
    """= pitch"""
    intonation: float = 0.0

    def __str__(self) -> str:
        return (
            f"**Engine**: `{self.type.value}`\n"
            f"**Voice**: `{self.name}` (`{self.style}`)\n"
            f"**Speed**: `{self.speed}` / **Tone**: `{self.tone}` / **Intonation**: `{self.intonation}`"
        )
