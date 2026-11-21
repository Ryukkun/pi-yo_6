from pathlib import Path

from pi_yo_6.config import ConfigFile, ConfigStore, GuildConfig


def test_config_file_create_and_reload(tmp_path: Path) -> None:
    cfg_path = tmp_path / "guild.json"
    cf = ConfigFile(cfg_path, GuildConfig)
    assert cfg_path.exists()
    assert cf.data.auto_join is False

    cf.data.auto_join = True
    cf.data.dic.put("テスト", "てすと")
    cf.write()

    reloaded = ConfigFile(cfg_path, GuildConfig)
    assert reloaded.data.auto_join is True
    assert reloaded.data.dic.get("テスト") == "てすと"


def test_config_file_corrupted_fallback(tmp_path: Path) -> None:
    cfg_path = tmp_path / "broken.json"
    cfg_path.write_text("{invalid json", encoding="utf-8")

    cf = ConfigFile(cfg_path, GuildConfig)
    assert cf.data.auto_join is False
    assert cf.data.max_tracks == 3


def test_config_store_cache(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path, GuildConfig)
    c1 = store.get(12345)
    c2 = store.get(12345)
    assert c1 is c2
    assert (tmp_path / "12345.json").exists()
