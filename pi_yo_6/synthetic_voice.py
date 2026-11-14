# Compatibility shim (will be removed once all modules migrate to pi_yo_6.tts)
from typing import TYPE_CHECKING

from pi_yo_6.tts.manager import TTSManager

if TYPE_CHECKING:
    from pi_yo_6.message_unit import MessageUnit


class SyntheticEngines(TTSManager):
    current: "SyntheticEngines"

    async def init_all(self) -> None:
        await super().init_all()
        SyntheticEngines.current = self

    async def create_voice(self, msg: "MessageUnit") -> None:
        msg.data = await self.synthesize(msg.text, msg.voice)

    @classmethod
    async def close(cls) -> None:  # type: ignore[override]
        if hasattr(cls, 'current'):
            await super(SyntheticEngines, cls.current).close()
