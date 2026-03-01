from dataclasses import dataclass, field
from typing import Optional

import ahocorasick

@dataclass
class DictionaryManager:
    words: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self.automaton:Optional[ahocorasick.Automaton] = None

    def new_automaton(self) -> ahocorasick.Automaton:
        automaton = ahocorasick.Automaton()
        for key, value in self.words.items():
            automaton.add_word(key, (key, value))
        automaton.make_automaton()
        return automaton

    def replace(self, text: str) -> str:
        if not self.words:
            return text
        
        automaton: ahocorasick.Automaton = self.automaton
        if self.automaton is None:
            self.automaton = self.new_automaton()
            automaton = self.automaton
            
        # Aho-Corasickでマッチした箇所を取得
        matches = []
        for end_index, (key, value) in automaton.iter(text):
            start_index = end_index - len(key) + 1
            matches.append((start_index, end_index, value))
        
        if not matches:
            return text

        # 重なり（東京都 と 東京）がある場合、長い方を優先して抽出
        matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))
        
        filtered_matches = []
        last_end = -1
        for start, end, val in matches:
            if start > last_end:
                filtered_matches.append((start, end, val))
                last_end = end
        
        # 文字列のズレを防ぐため、後ろから置換
        result = list(text)
        for start, end, val in reversed(filtered_matches):
            result[start:end+1] = list(val)
        
        return "".join(result)

    def get(self, key, default=None):
        return self.words.get(key, default)

    def put(self, key, value):
        self.words[key] = value
        self.automaton = None  # 変更があったらオートマトンを再構築する必要があることを示す

    def remove(self, key):
        if key in self.words:
            del self.words[key]
            self.automaton = None  # 変更があったらオートマトンを再構築する必要があることを示す

    def contains(self, key):
        return key in self.words


if __name__ == "__main__":
    dm = DictionaryManager()
    dm.put("東京", "Tokyoooooo")
    dm.put("東京都", "Tokyo Metropolis")
    dm.put("大阪", "Osaka")
    
    text = "私は東京都に住んでいます。大阪も好きです。大阪"
    replaced_text = dm.replace(text)
    print(replaced_text)  # 私はTokyo Metropolisに住んでいます。Osakaも好きです。