import logging
import os
from pathlib import Path

from pydantic import BaseModel, Field

from pi_yo_6.models import VoiceSetting
from pi_yo_6.text.dictionary import DictionaryManager

_log = logging.getLogger(__name__)


class GuildConfig(BaseModel):
    auto_join: bool = False
    announce_join_leave: bool = False
    overlap_mode: bool = False
    max_tracks: int = 3
    dic: DictionaryManager = Field(default_factory=DictionaryManager)


class UserConfig(BaseModel):
    voice: VoiceSetting = Field(default_factory=VoiceSetting)


class OpenJTalkConfig(BaseModel):
    hts_path: Path = Path('./pi_yo_6/open_jtalk/voice/')
    dictionary_path: Path = Path('./pi_yo_6/open_jtalk/dic')


class VoicevoxConfig(BaseModel):
    enable: bool = False
    text_limit: int = 100
    ip: str = 'localhost:50021'


class AppConfig(BaseModel):
    prefix: str = '.'
    token: str = ''
    text_limit: int = 100
    admin_dic: Path = Path('./dic/admin_dic.txt')
    user_dic: Path = Path('./dic/user_dic/')
    guild_config: Path = Path('./guild_config/')
    user_config: Path = Path('./user_config/')
    output: Path = Path('./output/')

    # 既存 config.json との互換性のためフィールド名を維持
    OpenJtalk: OpenJTalkConfig = Field(default_factory=OpenJTalkConfig)
    VOICEVOX: VoicevoxConfig = Field(
        default_factory=lambda: VoicevoxConfig(ip='localhost:50021')
    )
    Coeiroink: VoicevoxConfig = Field(
        default_factory=lambda: VoicevoxConfig(ip='localhost:50031')
    )


class ConfigFile[T: BaseModel]:
    """1つのJSON設定ファイルの読み込み・アトミック保存を管理する"""

    def __init__(self, path: Path, cls: type[T]) -> None:
        self.cls = cls
        self.path = path
        self.data: T = self._read()

    def _read(self) -> T:
        if not self.path.exists() or self.path.stat().st_size == 0:
            _log.info(f"Config file {self.path} not found or empty. Creating default.")
            default_data = self.cls()
            self.write(default_data)
            return default_data

        try:
            content = self.path.read_text(encoding='utf-8')
            return self.cls.model_validate_json(content)
        except Exception as e:
            _log.warning(f"Warning: {self.path} is corrupted. Using default. Error: {e}")
            default_data = self.cls()
            self.write(default_data)
            return default_data

    def write(self, data: T | None = None) -> None:
        """現在のデータ（または渡されたデータ）をアトミックにファイルへ保存"""
        target = data or self.data
        self.path.parent.mkdir(parents=True, exist_ok=True)
        json_str = target.model_dump_json(indent=2)
        temp_path = self.path.with_suffix(self.path.suffix + '.tmp')
        temp_path.write_text(json_str, encoding='utf-8')
        os.replace(temp_path, self.path)


class ConfigStore[T: BaseModel]:
    """IDごとにJSON設定ファイルをキャッシュ・管理するストア"""

    def __init__(self, folder_path: Path, data_cls: type[T]) -> None:
        self.cache: dict[int, ConfigFile[T]] = {}
        self.folder_path = folder_path
        self.data_cls = data_cls

    def get(self, key: int = 0) -> ConfigFile[T]:
        if key not in self.cache:
            file_path = self.folder_path / f'{key}.json'
            self.cache[key] = ConfigFile(file_path, self.data_cls)
        return self.cache[key]


def load_text_dictionary(path: Path) -> DictionaryManager:
    """テキスト形式の共通辞書ファイルを読み込む"""
    dm = DictionaryManager()
    if path.exists() and path.stat().st_size > 0:
        try:
            content = path.read_text(encoding='utf-8')
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    dm.put(parts[0], parts[1])
            _log.info(f"Loaded {len(dm.words)} words from admin_dic ({path})")
        except Exception as e:
            _log.warning(f"Failed to load admin_dic from {path}: {e}")
    return dm


# --- Initialization ---
_app_config_file = ConfigFile(Path("./config.json"), AppConfig)
app_config = _app_config_file.data
admin_dic = load_text_dictionary(app_config.admin_dic)
user_configs = ConfigStore(app_config.user_config, UserConfig)
guild_configs = ConfigStore(app_config.guild_config, GuildConfig)
