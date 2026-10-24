import logging
import os
from pathlib import Path
from typing import Type
from pydantic import BaseModel, Field

from pi_yo_6.dictionary_manager import DictionaryManager
from pi_yo_6.utils import VoiceUnit

_log = logging.getLogger(__name__)

# --- Data Models (Pydantic版) ---


class GuildConfigData(BaseModel):
    auto_join: bool = False
    announce_join_leave: bool = False
    # PydanticはネストしたBaseModelも自動でパースします
    dic: DictionaryManager = Field(default_factory=DictionaryManager)


class UserConfigData(BaseModel):
    voice: VoiceUnit = Field(default_factory=VoiceUnit)


class Open_Jtalk_Config(BaseModel):
    hts_path: Path = Path('./pi_yo_6/open_jtalk/voice/')
    dictionary_path: Path = Path('./pi_yo_6/open_jtalk/dic')


class VOICEVOX_Engine_Config(BaseModel):
    enable: bool = False
    text_limit: int = 100
    ip: str = 'localhost:50021'


class MainConfigData(BaseModel):
    prefix: str = '.'
    token: str = ''
    text_limit: int = 100
    admin_dic: Path = Path('./dic/admin_dic.txt')
    user_dic: Path = Path('./dic/user_dic/')
    guild_config: Path = Path('./guild_config/')
    user_config: Path = Path('./user_config/')
    output: Path = Path('./output/')

    OpenJtalk: Open_Jtalk_Config = Field(default_factory=Open_Jtalk_Config)
    VOICEVOX: VOICEVOX_Engine_Config = Field(
        default_factory=lambda: VOICEVOX_Engine_Config(ip='localhost:50021')
    )
    Coeiroink: VOICEVOX_Engine_Config = Field(
        default_factory=lambda: VOICEVOX_Engine_Config(ip='localhost:50031')
    )


# --- Logic (Pydantic版) ---


class ConfigUnit[T: BaseModel]:
    def __init__(self, path: Path, cls: Type[T]) -> None:
        self.cls = cls
        self.path = path
        self.data: T = self.__read()

    def __read(self) -> T:
        # ファイルが存在しない、あるいは中身が空(0バイト)の場合
        if not self.path.exists() or self.path.stat().st_size == 0:
            _log.info(f"Config file {self.path} not found or empty. Creating default.")
            default_data = self.cls()
            self.write(default_data)
            return default_data

        try:
            content = self.path.read_text(encoding='utf-8')
            return self.cls.model_validate_json(content)
        except Exception as e:
            # ここでファイルが壊れている（JSONとして不正）場合の処理
            _log.warning(f"Warning: {self.path} is corrupted. Using default. Error: {e}")
            default_data = self.cls()
            # 壊れたファイルを上書きして修復
            self.write(default_data)
            return default_data

    def write(self, data: T | None = None) -> None:
        """現在のデータ（または渡されたデータ）をファイルに保存（アトミック書き込み）"""
        target = data or self.data
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # model_dump_json で Path も自動的に文字列になり、ネストも辞書化される
        json_str = target.model_dump_json(indent=2)
        temp_path = self.path.with_suffix(self.path.suffix + '.tmp')
        temp_path.write_text(json_str, encoding='utf-8')
        os.replace(temp_path, self.path)


class ConfigLoader[T: BaseModel]:
    def __init__(self, folder_path: Path, data_cls: Type[T]) -> None:
        self.cache: dict[int, ConfigUnit[T]] = {}
        self.folder_path = folder_path
        self.data_cls = data_cls

    def get(self, key: int = 0) -> ConfigUnit[T]:
        if key not in self.cache:
            file_path = self.folder_path / f'{key}.json'
            self.cache[key] = ConfigUnit(file_path, self.data_cls)
        return self.cache[key]


# --- Initialization ---

# メイン設定
_main_unit = ConfigUnit(Path("./config.json"), MainConfigData)
Config = _main_unit.data

# ユーザー・ギルド設定ローダー
UserConfig = ConfigLoader(Config.user_config, UserConfigData)
GuildConfig = ConfigLoader(Config.guild_config, GuildConfigData)
