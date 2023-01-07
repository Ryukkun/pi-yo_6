class Open_Jtalk:
    # windowsで起動するときだけ Dic_shift_jis 必須
    Dic_utf_8 = '/var/lib/mecab/dic/open-jtalk/naist-jdic'
    Dic_shift_jis = '/var/lib/mecab/dic/open-jtalk/naist-jdic'
    # htsvoiceを入れておくファイル
    Voice = './Voice/'
    Output = './Output/'

class VOICEVOX:
    # https://github.com/VOICEVOX/voicevox_core/releases
    # onnxruntimeを同じフォルダに入れてください https://github.com/microsoft/onnxruntime/releases
    core_windows = './pi_yo_6/voicevox/voicevox_core-windows/core.dll'
    core_linux = './pi_yo_6/voicevox/voicevox_core-linux/libcore.so'
    core_darwin = './pi_yo_6/voicevox/voicevox_core-darwin/libcore.dylib'
    # use_gpuをオンにする場合は、voicevox core の注意点を読んでください https://github.com/VOICEVOX/voicevox_core/tree/main
    use_gpu = False

class Config:
    Prefix = '.'
    Token = ''
    Admin_dic = './dic/admin_dic.txt'
    User_dic = './dic/user_dic/'
    Guild_Config = './guild_config/'
    User_Config = './user_config/'
    OJ = Open_Jtalk
    VVOX = VOICEVOX
