import logging
import os
import json
from dataclasses import dataclass, field, asdict
from dacite import from_dict
from dacite import Config as DConfig

from pi_yo_6.config import Config
from pi_yo_6.dictionary_manager import DictionaryManager
from pi_yo_6.message_unit import ENGINE_TYPE, VoiceUnit



_log = logging.getLogger(__name__)

@dataclass
class GuildConfigData:
    auto_join:bool = False
    dic:DictionaryManager = field(default_factory=DictionaryManager)
    """guildごとの辞書"""


class GuildConfig:
    cache:dict[int, "GuildConfig"] = {}
    @staticmethod
    def get(gid:int) -> "GuildConfig":
        if not GuildConfig.cache.get(gid):
            GuildConfig.cache[gid] = GuildConfig(gid)
        return GuildConfig.cache[gid]


    def __init__(self, gid:int) -> None:
        self.gid = gid
        self.path = Config.guild_config / f'{gid}.json'
        self.data = self.__read()


    def __read(self) -> GuildConfigData:
        # 1. ファイルが存在するかチェック
        if not os.path.exists(self.path):
            # ファイルがなければデフォルトのデータを作成して返す
            # ついでに新規ファイルとして保存しておくと親切
            default_data = GuildConfigData()
            self.__write(default_data) 
            return default_data

        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                return from_dict(data_class=GuildConfigData, data=json.load(f))
        except (json.JSONDecodeError, KeyError):
            # ファイルが壊れていた場合のフォールバック
            print(f"Warning: {self.path} is corrupted. Using default.")
            default_data = GuildConfigData()
            self.__write(default_data) 
            return default_data


    def write(self):
        self.__write(self.data)


    def __write(self, gc:GuildConfigData):
        with open(self.path,'w') as f:
            json.dump(asdict(gc), f, indent=2)




@dataclass
class UserConfigData:
    voice:VoiceUnit = field(default_factory=VoiceUnit) #TODO: デフォルト値をランダムに


class UserConfig:
    cache:dict[int, "UserConfig"] = {}
    @staticmethod
    def get(uid:int) -> "UserConfig":
        if not UserConfig.cache.get(uid):
            UserConfig.cache[uid] = UserConfig(uid)
        return UserConfig.cache[uid]


    def __init__(self, uid:int) -> None:
        self.uid = uid
        self.path = Config.user_config / f'{uid}.json'
        self.data = self.__read()


    def __read(self) -> UserConfigData:
        # 1. ファイルが存在するかチェック
        if not os.path.exists(self.path):
            # ファイルがなければデフォルトのデータを作成して返す
            # ついでに新規ファイルとして保存しておくと親切
            default_data = UserConfigData()
            self.__write(default_data) 
            return default_data
        
        config = DConfig(
            type_hooks={ENGINE_TYPE: lambda x: ENGINE_TYPE(x) if isinstance(x, str) else x}
        )
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                return from_dict(data_class=UserConfigData, data=json.load(f), config=config)
        except Exception as e:
            # ファイルが壊れていた場合のフォールバック
            _log.warning(f"UserConfig {self.path} is corrupted. Using default. Error: {e}")
            default_data = UserConfigData()
            self.__write(default_data) 
            return default_data


    def write(self):
        self.__write(self.data)


    def __write(self, gc:UserConfigData):
        with open(self.path,'w') as f:
            json.dump(asdict(gc), f, indent=2)