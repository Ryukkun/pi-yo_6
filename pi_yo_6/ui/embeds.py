from discord import Colour, Embed

MAIN_COLOR = Colour.light_grey()


def make_no_perm_embed() -> Embed:
    """権限がない時のEmbed"""
    return Embed(title='権限がありません 🥲', colour=Colour.red())


def make_failed_embed() -> Embed:
    """失敗した時のEmbed"""
    return Embed(title='失敗 🤯', colour=Colour.red())


def make_info_embed(title: str, description: str | None = None) -> Embed:
    """標準通知用Embed"""
    return Embed(title=title, description=description, colour=MAIN_COLOR)
