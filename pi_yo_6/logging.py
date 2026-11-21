import logging

from discord.utils import _ColourFormatter


def setup_logger(level: int = logging.INFO) -> None:
    """pi_yo_6 および discord.player のロガーフォーマット・レベルを設定する"""
    handler = logging.StreamHandler()
    handler.setFormatter(_ColourFormatter())

    for name in ("pi_yo_6", "__main__"):
        logger = logging.getLogger(name)
        logger.setLevel(level)
        if not logger.handlers:
            logger.addHandler(handler)

    player_logger = logging.getLogger("discord.player")
    player_logger.setLevel(logging.WARNING)
    if not player_logger.handlers:
        player_logger.addHandler(handler)
