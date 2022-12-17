try: from translation import tree
except ModuleNotFoundError:
    from .translation import tree

class MainSys:
    @classmethod
    def to_kana(self, text: str):
        self.text = ReadText(text.lower())
        out = ''
        #文字がなくなるまで LOOP
        while self.text.text:
            self.first_unit = self.text.read()
            ltu = None

            # 異端変換 
            if self._nn(self):
                out += 'ん'
                continue
            
            if ltu := self._ltu(self):
                '''
                この先変換候補があったら out の語尾を "っ" を入れ変える
                無かったらこのまま 
                '''
                out += self.first_unit
                self.first_unit = self.text.read()

            # 通常変換
            if _tree := tree.get(self.first_unit):
                '''
                dcit => 変換候補あり
                str => Answer
                None => 候補なし
                '''
                temp_unit = ''
                while type(_tree) == dict:
                    unit = self.text.read()
                    _tree = _tree.get(unit)
                    temp_unit += unit
                if _tree:
                    if ltu:
                        out = out[:-1]
                        out += 'っ'
                    out += _tree
                else:
                    self.text.text = temp_unit + self.text.text
                    out += self.first_unit
            else:
                out += self.first_unit
        return out

    def _nn(self):
        boin_n = 'aiueon'
        if self.first_unit == 'n':
            if not self.text.read_only() in boin_n:
                return True

    def _ltu(self):
        siin_n = 'bcdfghjklmpqrstvwxyz'
        if self.first_unit in siin_n:
            if self.text.read_only() == self.first_unit:
                if self.text.read_only(indent=2) != self.first_unit:
                    return True




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
        ti = time.perf_counter()
        print(ts+'\n'+MainSys.to_kana(ts))
        print(time.perf_counter()-ti)
        print('\n')