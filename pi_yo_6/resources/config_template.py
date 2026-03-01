from dataclasses import dataclass
from pathlib import Path

@dataclass
class Open_Jtalk_Config:
    hts_path = Path('./pi_yo_6/open_jtalk/voice/')
    """htsvoiceを入れておくフォルダ"""
    dictionary_path = Path('./pi_yo_6/open_jtalk/dic')
    """フォルダ指定"""


@dataclass
class VOICEVOX_Engine_Config:
    enable: bool = False
    core_path: str = ''
    text_limit: int = 100
    ip: str = 'localhost:50021'



class Config:
    prefix = '.'
    token = ''
    admin_dic = Path('./dic/admin_dic.txt')
    user_dic = Path('./dic/user_dic/')
    guild_config = Path('./guild_config/')
    user_config = Path('./user_config/')
    output = Path('./output/')
    """音声ファイル一時的保存場所"""

    OpenJtalk = Open_Jtalk_Config()
    VOICEVOX = VOICEVOX_Engine_Config()
    '''
    https://github.com/VOICEVOX/voicevox_engine
    ↑これを起動しておく必要あり
    -------
    core_path : str
        voicevox_coreがあるPath

    ip : str
        VOICEVOX Engine のip
    ''' 

    Coeiroink = VOICEVOX_Engine_Config(
        enable=False,
        text_limit=100,
        ip='localhost:50031'
        )
    '''
    https://coeiroink.com/
    https://github.com/shirowanisan/voicevox_engine
    ↑これを起動しておく必要あり
    音声モデルは自分で入れてください

    -------
    ip : str
        Coeiroink Engine のip
    ''' 