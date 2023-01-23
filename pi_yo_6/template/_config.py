class Open_Jtalk:
    '''
    Dic_utf_8 : str
    Dic_shift_jis : str
        windowsで起動するときだけ Dic_shift_jis 必須
    
    hts_path : str
        htsvoiceを入れておくファイル
    '''
    enable = True
    dic_utf_8 = './pi_yo_6/open_jtalk/dic'
    dic_shift_jis = './pi_yo_6/open_jtalk/dic'
    hts_path = './pi_yo_6/open_jtalk/voice/'


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
    enable = False
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
    enable = False
    load_all_models = False


class Config:
    '''
    ------
    output : str
        音声ファイル一時的保存場所
    '''
    prefix = '.'
    token = ''
    admin_dic = './dic/admin_dic.txt'
    user_dic = './dic/user_dic/'
    guild_config = './guild_config/'
    user_config = './user_config/'
    output = './output/'
    OJ = Open_Jtalk
    Vvox = VOICEVOX
    Coeiroink = Coeiroink
