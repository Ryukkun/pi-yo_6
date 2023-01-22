class Open_Jtalk:
    '''
    Dic_utf_8 : str
    Dic_shift_jis : str
        windowsで起動するときだけ Dic_shift_jis 必須
    
    Voice : str
        htsvoiceを入れておくファイル
    
    Output : str
        音声ファイル一時的保存場所
    '''
    Dic_utf_8 = '/var/lib/mecab/dic/open-jtalk/naist-jdic'
    Dic_shift_jis = '/var/lib/mecab/dic/open-jtalk/naist-jdic'
    Voice = './Voice/'
    Output = './Output/'


class VOICEVOX:
    '''
    https://github.com/VOICEVOX/voicevox_core/releases
    onnxruntimeを同じフォルダに入れてください https://github.com/microsoft/onnxruntime/releases
    
    -------
    use_gpu : bool
        voicevox core の注意点を読んでください https://github.com/VOICEVOX/voicevox_core/tree/main

    load_all_models : bool
        今のところは True にしておかないと動きません。いつかメモリ使用を抑制するために修正するかも
    ''' 
    core_windows = './pi_yo_6/voicevox/voicevox_core-windows/core.dll'
    core_linux = './pi_yo_6/voicevox/voicevox_core-linux/libcore.so'
    core_darwin = './pi_yo_6/voicevox/voicevox_core-darwin/libcore.dylib'

    use_gpu = False
    load_all_models = True


class Coeiroink:
    '''
    https://coeiroink.com/
    音声モデルは自分で入れてください pi_yo_6/coeiroink/speaker_info

    -------
    load_all_models : bool
        False 激推しです。　Trueにしたらメモリ不足で仮想メモリまで侵食します
        モデル量にもよりますが、自分は 20GB弱くらい取られました
    ''' 
    load_all_models = False


class Config:
    Prefix = '.'
    Token = ''
    Admin_dic = './dic/admin_dic.txt'
    User_dic = './dic/user_dic/'
    Guild_Config = './guild_config/'
    User_Config = './user_config/'
    OJ = Open_Jtalk
    VVOX = VOICEVOX
    Coeiroink = Coeiroink
