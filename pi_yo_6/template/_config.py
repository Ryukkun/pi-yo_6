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
    https://github.com/shirowanisan/voicevox_engine
    ↑これを起動しておく必要あり
    音声モデルは自分で入れてください

    -------
    ip : str
        Coeiroink Engine のip
    ''' 
    enable = False

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
