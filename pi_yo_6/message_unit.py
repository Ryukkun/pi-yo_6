from datetime import datetime
from io import BufferedIOBase
from typing import TYPE_CHECKING, Optional

from pi_yo_6.models import VoiceSetting
from pi_yo_6.synthetic_voice import SyntheticEngines
from pi_yo_6.text.normalizer import TextNormalizer

if TYPE_CHECKING:
    import discord


class MessageUnit:
    """Compatibility wrapper until ChatReader migrates to SpeechItem + TextNormalizer"""

    def __init__(self, text: str, time: Optional[datetime] = None) -> None:
        self.time = time or datetime.now()
        self.text: str = text
        self.voice = VoiceSetting()
        self.data: Optional[BufferedIOBase] = None
        self.generated = False

    async def normalize_text(
        self, guild_id: int | None = None, guild: Optional["discord.Guild"] = None
    ) -> None:
        resolver = SyntheticEngines.current.find_voice if hasattr(SyntheticEngines, 'current') else None
        self.text, self.voice = TextNormalizer.normalize(
            self.text,
            self.voice,
            guild=guild,
            guild_id=guild_id,
            voice_resolver=resolver,
        )

    async def create_voice(self) -> None:
        if not self.text.strip():
            self.generated = False
            return
        await SyntheticEngines.current.create_voice(self)
        self.generated = self.data is not None
