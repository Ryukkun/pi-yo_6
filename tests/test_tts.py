import io

from pi_yo_6.models import EngineType, VoiceSetting
from pi_yo_6.tts.manager import TTSManager


async def test_open_jtalk_synthesize() -> None:
    tts = TTSManager()
    await tts.init_all()
    try:
        oj = tts.get_engine(EngineType.OPEN_JTALK)
        assert oj is not None
        assert len(oj.metas) > 0

        first = oj.metas[0]
        voice = VoiceSetting(
            type=EngineType.OPEN_JTALK,
            name=first["name"],
            style=first["styles"][0]["name"],
        )
        wav = await tts.synthesize("テスト音声です", voice)
        assert isinstance(wav, io.BytesIO)
        assert len(wav.getvalue()) > 0
    finally:
        await tts.close()
