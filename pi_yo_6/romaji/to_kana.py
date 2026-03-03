import logging
from typing import Union

try: from translation import tree
except ModuleNotFoundError:
    from .translation import tree

_log = logging.getLogger(__file__)

class Romaji:
    BOIN = 'aiueon'
    SIIN = 'bcdfghjklmnpqrstvwxyz'
    @staticmethod
    def to_kana(text: str) -> str:
        text_list = list(text)
        out:list[str] = []
        try:
            #文字がなくなるまで LOOP
            while text_list:
                char = text_list[0]

                # 異端変換 
                if Romaji.is_nn(text_list, char):
                    "nの後に母音以外が来るパターンを検出"
                    out += 'ん'
                    text_list.pop(0)
                    continue
                
                if Romaji.is_ltu(text_list, char):
                    '''
                    この先変換候補があったら out の語尾を "っ" を入れ変える
                    無かったらこのまま
                    '''
                    # ただし 'nn' は上で処理済みなのでここでは子音の連続＝「っ」
                    out += 'っ'
                    text_list.pop(0)
                    continue

                # 3. Tree(辞書)を使った変換
                current_tree: Union[dict[str, str | dict], str, None] = tree
                match_len = 0
                found_str = None
                
                # どこまで深くマッチするか探索
                for i in range(len(text_list)):
                    next_char = text_list[i]
                    current_tree = current_tree.get(next_char)
                    
                    if current_tree is None:
                        break
                    
                    if isinstance(current_tree, str):
                        found_str = current_tree
                        match_len = i + 1
                        break # マッチ確定
                    # dictの場合はさらにループ継続
                
                if found_str:
                    out += found_str
                    del text_list[:match_len]
                else:
                    # 変換不能な文字はそのまま通す
                    out += text_list.pop(0) if text_list else char
            return ''.join(out)
        
        except Exception as e:
            _log.error(e)
            return ''.join(out) + ''.join(text_list)


    @staticmethod
    def is_nn(text_list:list[str], char:str) -> bool:
        "nの後に母音以外が来るパターンを検出"
        if char == 'n':
            if len(text_list) >= 2 and text_list[1] not in "aiueoyn":
                return True
        return False

    @staticmethod
    def is_ltu(text_list:list[str], first_unit:str) -> bool:
        if first_unit in 'bcdfghjklmpqrstvwxyz' and len(text_list) >= 3:
            if text_list[1] == first_unit:
                return text_list[2] in Romaji.BOIN
        return False



if __name__ == '__main__':
    import time
    while True:
        ts = input('なんか書きたまえ いい子だから さあ:')
        ti = time.perf_counter()
        print(ts+'\n'+Romaji.to_kana(ts))
        print(time.perf_counter()-ti)
        print('\n')