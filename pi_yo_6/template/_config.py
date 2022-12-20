class Open_Jtalk:
    Dic = '/var/lib/mecab/dic/open-jtalk/naist-jdic'
    Voice = './Voice/'
    Output = './Output/'

class VOICEVOX:
    # https://github.com/VOICEVOX/voicevox_core/releases
    core_windows = './pi_yo_6/voicevox/voicevox_core-windows-x64-cpu/core.dll'
    core_linux = './pi_yo_6/voicevox/voicevox_core-linux-x64-cpu/libcore.so'

class Config:
    Prefix = '.'
    Token = ''
    Admin_dic = './dic/admin_dic.txt'
    User_dic = './dic/user_dic/'
    Guild_Config = './guild_config/'
    OJ = Open_Jtalk
    VVOX = VOICEVOX