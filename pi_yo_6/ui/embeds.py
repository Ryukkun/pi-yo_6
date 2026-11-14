from discord import Colour, Embed

MAIN_COLOR = Colour.light_grey()


def make_failed_embed(title: str = '失敗 🤯', description: str | None = None) -> Embed:
    """失敗した時のEmbed"""
    return Embed(title=title, description=description, colour=Colour.red())


def make_info_embed(title: str, description: str | None = None) -> Embed:
    """標準通知用Embed"""
    return Embed(title=title, description=description, colour=MAIN_COLOR)
