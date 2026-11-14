import math
from typing import TYPE_CHECKING
import discord
from discord import ButtonStyle, Interaction, ui

from pi_yo_6.embeds import EmBase
from pi_yo_6.load_config import GuildConfig
from pi_yo_6.text.dictionary import DictionaryManager

PAGE_SIZE = 10


class DictionaryView(ui.View):
    def __init__(self, guild_id: int, dic: DictionaryManager, page: int = 0) -> None:
        super().__init__(timeout=180.0)
        self.guild_id = guild_id
        self.dic = dic
        self.page = page
        self._update_components()

    @property
    def words_list(self) -> list[tuple[str, str]]:
        return list(self.dic.words.items())

    @property
    def max_page(self) -> int:
        return max(1, math.ceil(len(self.words_list) / PAGE_SIZE))

    def _update_components(self) -> None:
        self.clear_items()
        max_p = self.max_page

        # ページネーションボタン
        prev_btn = ui.Button(
            label="◀ 前へ",
            style=ButtonStyle.secondary,
            disabled=(self.page <= 0),
            custom_id="prev_page",
        )
        prev_btn.callback = self.on_prev  # type: ignore[assignment]
        self.add_item(prev_btn)

        page_indicator = ui.Button(
            label=f"{self.page + 1} / {max_p}",
            style=ButtonStyle.gray,
            disabled=True,
            custom_id="page_num",
        )
        self.add_item(page_indicator)

        next_btn = ui.Button(
            label="次へ ▶",
            style=ButtonStyle.secondary,
            disabled=(self.page >= max_p - 1),
            custom_id="next_page",
        )
        next_btn.callback = self.on_next  # type: ignore[assignment]
        self.add_item(next_btn)

        # 現在のページの単語削除セレクトメニュー
        start = self.page * PAGE_SIZE
        page_items = self.words_list[start : start + PAGE_SIZE]
        if page_items:
            select = ui.Select(
                placeholder="削除する単語を選択...",
                min_values=1,
                max_values=1,
                custom_id="delete_select",
            )
            for word, reading in page_items:
                label = word[:50]
                desc = f"→ {reading}"[:100]
                select.add_option(label=label, value=word, description=desc)
            select.callback = self.on_delete_select  # type: ignore[assignment]
            self.add_item(select)

    def create_embed(self, guild_name: str) -> discord.Embed:
        embed = discord.Embed(
            title=f"📖 辞書一覧 ({guild_name})",
            colour=EmBase.main_color(),
        )
        items = self.words_list
        if not items:
            embed.description = (
                "登録されている単語はありません。\n"
                "`.register (単語) (読み)` で単語を登録できます！"
            )
            return embed

        start = self.page * PAGE_SIZE
        page_items = items[start : start + PAGE_SIZE]
        lines = [f"`{word}` → `{reading}`" for word, reading in page_items]
        embed.description = "\n".join(lines)
        embed.set_footer(
            text=f"全 {len(items)} 件 | ページ {self.page + 1}/{self.max_page} | 下のメニューから直接削除も可能"
        )
        return embed

    async def on_prev(self, interaction: Interaction) -> None:
        if self.page > 0:
            self.page -= 1
        self._update_components()
        await interaction.response.edit_message(
            embed=self.create_embed(interaction.guild.name if interaction.guild else ""),
            view=self,
        )

    async def on_next(self, interaction: Interaction) -> None:
        if self.page < self.max_page - 1:
            self.page += 1
        self._update_components()
        await interaction.response.edit_message(
            embed=self.create_embed(interaction.guild.name if interaction.guild else ""),
            view=self,
        )

    async def on_delete_select(self, interaction: Interaction) -> None:
        if not interaction.data or "values" not in interaction.data:
            return
        selected_word = interaction.data["values"][0]  # type: ignore[index]
        gc = GuildConfig.get(self.guild_id)
        if gc.data.dic.contains(selected_word):
            gc.data.dic.remove(selected_word)
            gc.write()
            self.dic = gc.data.dic

        # ページ調整
        if self.page >= self.max_page and self.page > 0:
            self.page = self.max_page - 1

        self._update_components()
        await interaction.response.edit_message(
            embed=self.create_embed(interaction.guild.name if interaction.guild else ""),
            view=self,
        )
