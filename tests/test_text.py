from pathlib import Path
from unittest.mock import patch

from pi_yo_6.config import ConfigStore, GuildConfig
from pi_yo_6.models import VoiceSetting
from pi_yo_6.text.dictionary import DictionaryManager
from pi_yo_6.text.normalizer import TextNormalizer


def test_dictionary_replace_longest_match() -> None:
    dm = DictionaryManager()
    dm.put("東京", "とうきょう")
    dm.put("東京都", "とうきょうと")

    assert dm.replace("東京都に行く") == "とうきょうとに行く"
    assert dm.contains("東京")
    dm.remove("東京都")
    assert not dm.contains("東京都")
    assert dm.replace("東京都に行く") == "とうきょう都に行く"


def test_text_normalizer_url_code_and_voice_params(tmp_path: Path) -> None:
    temp_store = ConfigStore(tmp_path, GuildConfig)
    voice = VoiceSetting(name="mei", style="normal", speed=1.2)

    with patch("pi_yo_6.text.normalizer.config.guild_configs", temp_store):
        text, out_voice = TextNormalizer.normalize(
            "speed:1.5 https://example.com `code` ||secret||",
            voice=voice,
            guild_id=1,
        )

    assert "ユーアールエルは省略するのです" in text
    assert "コード省略" in text
    assert "ネタバレ" in text
    assert out_voice.speed == 1.5
    # 元のVoiceSettingは変更されないこと
    assert voice.speed == 1.2
