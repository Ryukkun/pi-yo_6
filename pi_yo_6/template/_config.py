class Open_Jtalk:
    '''
    hts_path : str
        htsvoiceを入れておくファイル
    '''
    enable = True
    hts_path = './pi_yo_6/open_jtalk/voice/'


class VOICEVOX:
    '''
    https://github.com/VOICEVOX/voicevox_engine
    ↑これを起動しておく必要あり
    -------
    core_path : str
        voicevox_coreがあるPath

    ip : str
        VOICEVOX Engine のip
    ''' 
    enable = False
    core_path = ''

    text_limit = 100
    ip = 'localhost:50021'


class Coeiroink:
    '''
    https://coeiroink.com/
    音声モデルは自分で入れてください
    Path : ./pi_yo_6/coeiroink/speaker_info

    -------
    use_gpu : bool
        True でも あんまり意味ないかも

    load_all_models : bool
        False 激推しです。　Trueにしたらメモリ不足で仮想メモリまで侵食します
        モデル量にもよりますが、自分は 20GB弱くらい取られました
    ''' 
    enable = False
    use_gpu = False
    load_all_models = False

    text_limit = 100
    ip = 'localhost:50031'


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
