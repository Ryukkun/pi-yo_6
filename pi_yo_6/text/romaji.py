import logging

from pi_yo_6.text.romaji_table import ROMAJI_TREE

_log = logging.getLogger(__name__)


class RomajiConverter:
    VOWELS = 'aiueon'
    CONSONANTS = 'bcdfghjklmnpqrstvwxyz'

    @staticmethod
    def to_kana(text: str) -> str:
        text_list = list(text)
        out: list[str] = []
        try:
            while text_list:
                char = text_list[0]

                if RomajiConverter._is_nn(text_list, char):
                    out.append('ん')
                    text_list.pop(0)
                    continue

                if RomajiConverter._is_sokuon(text_list, char):
                    out.append('っ')
                    text_list.pop(0)
                    continue

                current_tree: dict[str, str | dict] | str | None = ROMAJI_TREE
                match_len = 0
                found_str: str | None = None

                for i in range(len(text_list)):
                    next_char = text_list[i]
                    if not isinstance(current_tree, dict):
                        break
                    current_tree = current_tree.get(next_char)

                    if current_tree is None:
                        break

                    if isinstance(current_tree, str):
                        found_str = current_tree
                        match_len = i + 1
                        break

                if found_str:
                    out.append(found_str)
                    del text_list[:match_len]
                else:
                    out.append(text_list.pop(0))
            return ''.join(out)
        except Exception as e:
            _log.error(e)
            return ''.join(out) + ''.join(text_list)

    @staticmethod
    def _is_nn(text_list: list[str], char: str) -> bool:
        """nの後に母音・y・n以外が来るパターンを検出"""
        return char == 'n' and len(text_list) >= 2 and text_list[1] not in "aiueoyn"

    @staticmethod
    def _is_sokuon(text_list: list[str], first_unit: str) -> bool:
        """子音重複による促音（っ）を検出"""
        if first_unit in 'bcdfghjklmpqrstvwxyz' and len(text_list) >= 3:
            if text_list[1] == first_unit:
                return text_list[2] in RomajiConverter.VOWELS
        return False
