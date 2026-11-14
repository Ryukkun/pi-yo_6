# Compatibility shim (will be removed once all modules migrate to pi_yo_6.config)
from pi_yo_6.config import (
    AppConfig as MainConfigData,
    ConfigFile as ConfigUnit,
    ConfigStore as ConfigLoader,
    GuildConfig as GuildConfigData,
    OpenJTalkConfig as Open_Jtalk_Config,
    UserConfig as UserConfigData,
    VoicevoxConfig as VOICEVOX_Engine_Config,
    admin_dic as AdminDic,
    app_config as Config,
    guild_configs as GuildConfig,
    user_configs as UserConfig,
)

__all__ = [
    "AdminDic",
    "Config",
    "ConfigLoader",
    "ConfigUnit",
    "GuildConfig",
    "GuildConfigData",
    "MainConfigData",
    "Open_Jtalk_Config",
    "UserConfig",
    "UserConfigData",
    "VOICEVOX_Engine_Config",
]
