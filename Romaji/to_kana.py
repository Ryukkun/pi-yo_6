try: from translation import tree
except ModuleNotFoundError:
    from .translation import tree


def to_kana(text: str):
    siin_n = 'bcdfghjklmpqrstvwxyz'
    boin_n = 'aiueon'

    def _nn():
        if first_unit == 'n':
            if not text.read_only() in boin_n:
                return True

    def _ltu():
        if first_unit in siin_n:
            if text.read_only() == first_unit:
                if text.read_only(indent=2) != first_unit:
                    return True

    text = ReadText(text.lower())
    out = ''
    while text.text:
        first_unit = text.read()
        if _nn():
            out += 'ん'
            continue
        
        if _ltu():
            out += 'っ'
            continue

        if _tree := tree.get(first_unit):
            '''
            dcit => 変換候補あり
            str => Answer
            None => 候補なし
            '''
            temp_unit = ''
            while type(_tree) == dict:
                unit = text.read()
                _tree = _tree.get(unit)
                temp_unit += unit
            if _tree:
                out += _tree
            else:
                text.text = temp_unit + text.text
                out += first_unit
        else:
            out += first_unit
    return out



class ReadText():

    def __init__(self, text):
        self.text = text

    def read_only(self, indent=1):
        return self.text[indent-1:indent]
    
    def delete(self):
        self.text = self.text[1:]

    def read(self):
        text = self.text[:1]
        self.delete()
        return text



if __name__ == '__main__':
    import time
    while True:
        ts = input('なんか書きたまえ いい子だから さあ:')
        ti = time.time()
        print(ts+'\n'+to_kana(ts))
        print(time.time()-ti)
        print('\n')