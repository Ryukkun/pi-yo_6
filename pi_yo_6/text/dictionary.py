import ahocorasick
from pydantic import BaseModel, Field, PrivateAttr


class DictionaryManager(BaseModel):
    words: dict[str, str] = Field(default_factory=dict)
    _automaton: ahocorasick.Automaton | None = PrivateAttr(default=None)

    def _build_automaton(self) -> ahocorasick.Automaton:
        automaton = ahocorasick.Automaton()
        for key, value in self.words.items():
            automaton.add_word(key, (key, value))
        automaton.make_automaton()
        return automaton

    def replace(self, text: str) -> str:
        if not self.words:
            return text

        if self._automaton is None:
            self._automaton = self._build_automaton()
        automaton = self._automaton

        # Aho-Corasickでマッチした箇所を取得
        matches: list[tuple[int, int, str]] = []
        for end_index, (key, value) in automaton.iter(text):
            start_index = end_index - len(key) + 1
            matches.append((start_index, end_index, value))

        if not matches:
            return text

        # 重なり（東京都 と 東京）がある場合、長い方を優先して抽出
        matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))

        filtered_matches: list[tuple[int, int, str]] = []
        last_end = -1
        for start, end, val in matches:
            if start > last_end:
                filtered_matches.append((start, end, val))
                last_end = end

        # 文字列のズレを防ぐため、後ろから置換
        result = list(text)
        for start, end, val in reversed(filtered_matches):
            result[start : end + 1] = list(val)

        return "".join(result)

    def get(self, key: str, default: str | None = None) -> str | None:
        return self.words.get(key, default)

    def put(self, key: str, value: str) -> None:
        self.words[key] = value
        self._automaton = None

    def remove(self, key: str) -> None:
        if key in self.words:
            del self.words[key]
            self._automaton = None

    def contains(self, key: str) -> bool:
        return key in self.words
