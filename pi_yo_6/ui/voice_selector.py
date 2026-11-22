import asyncio
import logging
import math
from typing import TYPE_CHECKING, TypedDict

from discord import ButtonStyle, Embed, Interaction, ui

from pi_yo_6.config import user_configs
from pi_yo_6.models import EngineType, VoiceSetting
from pi_yo_6.tts.manager import TTSManager
from pi_yo_6.ui.embeds import MAIN_COLOR

if TYPE_CHECKING:
    from pi_yo_6.session import GuildVoiceSession

_log = logging.getLogger(__name__)


class _StyleOption(TypedDict):
    name: str
    id: str
    author: str


class _SpeakerGroup(TypedDict):
    name: list[str]
    styles: list[_StyleOption]


class _EngineParamLimits(TypedDict):
    speed: tuple[float, float]
    tone: tuple[float, float]
    intonation: tuple[float, float] | None


_VOICEVOX_LIMITS: _EngineParamLimits = {
    "speed": (0.5, 2.0),
    "tone": (-0.15, 0.15),
    "intonation": (0.0, 2.0),
}

_ENGINE_PARAM_LIMITS: dict[EngineType, _EngineParamLimits] = {
    EngineType.OPEN_JTALK: {
        "speed": (0.5, 100.0),
        "tone": (-50.0, 50.0),
        "intonation": None,
    },
    EngineType.VOICEVOX: _VOICEVOX_LIMITS,
    EngineType.COEIROINK: _VOICEVOX_LIMITS,
}


def _get_param_warnings(voice: VoiceSetting) -> list[str]:
    """選択中エンジンの規定値を超えているパラメーターの警告文を返す"""
    limits = _ENGINE_PARAM_LIMITS[voice.type]
    warnings: list[str] = []
    checks: list[tuple[str, float, tuple[float, float] | None]] = [
        ("Speed", voice.speed, limits["speed"]),
        ("Tone", voice.tone, limits["tone"]),
        ("Intonation", voice.intonation, limits["intonation"]),
    ]
    for label, value, bounds in checks:
        if bounds is None:
            continue
        low, high = bounds
        if not (low <= value <= high):
            warnings.append(
                f"⚠ {label} ({value}) が {voice.type.value} の規定値 [{low} ~ {high}] を超えています"
            )
    return warnings


class VoiceSelectorContainer(ui.Container):
    """話者・スタイル・速度・ピッチを設定するためのインタラクティブUI"""

    def __init__(
        self,
        sessions: dict[int, "GuildVoiceSession"],
        tts: TTSManager,
        voice: VoiceSetting | None = None,
    ) -> None:
        super().__init__(accent_color=MAIN_COLOR)
        self.sessions = sessions
        self.tts = tts
        self.voice = (
            voice.model_copy()
            if voice
            else VoiceSetting(type=EngineType.OPEN_JTALK, name="mei", style="normal")
        )

        self._update_params_button_label()
        self.row0.add_item(
            EngineButton(self, EngineType.OPEN_JTALK, self.tts.open_jtalk is not None)
        )
        self.row0.add_item(
            EngineButton(self, EngineType.VOICEVOX, self.tts.voicevox is not None)
        )
        self.row0.add_item(
            EngineButton(self, EngineType.COEIROINK, self.tts.coeiroink is not None)
        )
        self.res_styles: list[_StyleOption] = []

        self.refresh_select_options()

    def refresh_select_options(self) -> None:
        engine = self.tts.get_engine(self.voice.type)
        if engine is None:
            self.voice.type = EngineType.OPEN_JTALK
            engine = self.tts.open_jtalk
        raw_metas = engine.metas

        # Discord Select の上限(25件)に収めるためのグルーピング処理
        groups: list[_SpeakerGroup] = []
        booking = max(1, math.ceil(len(raw_metas) / 25))
        for i in range(0, len(raw_metas), booking):
            parts = raw_metas[i : i + booking]
            flat_style: list[_StyleOption] = []
            for part in parts:
                for style in part['styles']:
                    flat_style.append(
                        {
                            "author": part['name'],
                            "name": style['name'],
                            "id": str(style["id"]),
                        }
                    )
            groups.append(
                {
                    "name": [_['name'] for _ in parts],
                    "styles": flat_style,
                }
            )

        # キャラクター選択オプション構築
        self.voice_authors_selection.options.clear()
        has_default = False
        for group in groups[:25]:
            default = self.voice.name in group['name'] and not has_default
            if default:
                has_default = True
            self.voice_authors_selection.add_option(
                label=", ".join(group["name"]),
                value=group["name"][0],
                default=default,
            )
        if not has_default and groups:
            self.voice.name = groups[0]['styles'][0]['author']
            self.voice_authors_selection.options[0].default = True

        # スタイル選択オプション構築
        self.voice_styles_selection.options.clear()
        self.res_styles.clear()
        has_default = False
        styles: list[_StyleOption] = []
        for group in groups:
            if self.voice.name in group['name']:
                styles = group['styles']
                break
        for i, style in enumerate(styles[:25]):
            self.res_styles.append(style)
            default = (
                self.voice.style == style['name']
                and self.voice.name == style['author']
                and not has_default
            )
            if default:
                has_default = True
            self.voice_styles_selection.add_option(
                label=f"{style['author']}_{style['name']}",
                value=str(i),
                default=default,
            )
        if not has_default and styles:
            self.voice.style = styles[0]['name']
            self.voice_styles_selection.options[0].default = True

    row_1 = ui.TextDisplay("## ボイス設定")
    row0 = ui.ActionRow()
    row1 = ui.ActionRow()

    @row1.select(placeholder='キャラクター選択')
    async def voice_authors_selection(self, interaction: Interaction, select: ui.Select) -> None:
        if interaction.message:
            self.voice.name = self.voice_authors_selection.values[0]
            self.refresh_select_options()
            asyncio.create_task(self.tts.warmup_voice(self.voice.model_copy()))
            await interaction.response.edit_message(view=self.view)

    row2 = ui.ActionRow()

    @row2.select(placeholder='スタイル選択')
    async def voice_styles_selection(self, interaction: Interaction, select: ui.Select) -> None:
        try:
            style = self.res_styles[int(self.voice_styles_selection.values[0])]
            self.voice.name = style['author']
            self.voice.style = style['name']
            self.refresh_select_options()
            asyncio.create_task(self.tts.warmup_voice(self.voice.model_copy()))
            await interaction.response.edit_message(view=self.view)
            return
        except Exception as e:
            _log.error(f"スタイルの取得に失敗しました: {e}")
        await interaction.response.defer()

    row3 = ui.ActionRow()

    @row3.button(style=ButtonStyle.blurple)
    async def speed_button(self, interaction: Interaction, button: ui.Button) -> None:
        await interaction.response.send_modal(VoiceParamsModal(self))

    def update_params(
        self,
        speed: float | None = None,
        tone: float | None = None,
        intonation: float | None = None,
    ) -> None:
        if speed is not None:
            self.voice.speed = speed
        if tone is not None:
            self.voice.tone = tone
        if intonation is not None:
            self.voice.intonation = intonation
        self._update_params_button_label()

    def _update_params_button_label(self) -> None:
        warnings = _get_param_warnings(self.voice)
        base_label = (
            f"Speed: {self.voice.speed},  Tone: {self.voice.tone}, Intonation: {self.voice.intonation}"
        )
        if warnings:
            self.speed_button.style = ButtonStyle.red
            self.speed_button.label = f"⚠ {base_label}"[:80]
            self.row_1.content = "## ボイス設定\n" + "\n".join(warnings)
        else:
            self.speed_button.style = ButtonStyle.blurple
            self.speed_button.label = base_label[:80]
            self.row_1.content = "## ボイス設定"

    @row3.button(label='Play', style=ButtonStyle.green)
    async def text_play_button(self, interaction: Interaction, button: ui.Button) -> None:
        await interaction.response.defer()
        if not interaction.guild:
            return
        if session := self.sessions.get(interaction.guild.id):
            await session.enqueue_speech(
                "テストなのだ",
                self.voice.model_copy(),
                guild=interaction.guild,
            )

    @row3.button(label='ボイスをセット', style=ButtonStyle.green)
    async def set_voice_button(self, interaction: Interaction, button: ui.Button) -> None:
        uc = user_configs.get(interaction.user.id)
        uc.data.voice = self.voice.model_copy()
        uc.write()
        await interaction.response.send_message(
            embed=Embed(
                title='反映完了!', description=str(self.voice), colour=MAIN_COLOR
            ),
            ephemeral=True,
        )

    @row3.button(label='Delete', style=ButtonStyle.red)
    async def delete_button(self, interaction: Interaction, button: ui.Button) -> None:
        await interaction.response.defer()
        if interaction.message:
            await interaction.message.delete()


class EngineButton(ui.Button):
    def __init__(self, root: VoiceSelectorContainer, engine_type: EngineType, enable: bool) -> None:
        self.root = root
        self.engine_type = engine_type
        super().__init__(
            style=ButtonStyle.green if enable else ButtonStyle.gray,
            label=engine_type.value,
            disabled=not enable,
            row=0,
        )

    async def callback(self, interaction: Interaction) -> None:
        if interaction.message:
            self.root.voice.type = self.engine_type
            self.root.voice.name = ""
            self.root.voice.style = ""
            self.root.refresh_select_options()
            self.root._update_params_button_label()
            asyncio.create_task(self.root.tts.warmup_voice(self.root.voice.model_copy()))
            await interaction.response.edit_message(view=self.view)
        else:
            await interaction.response.defer()


class VoiceParamsModal(ui.Modal):
    def __init__(self, root: VoiceSelectorContainer) -> None:
        super().__init__(title="詳細設定")
        self.root = root
        self.limits = _ENGINE_PARAM_LIMITS[root.voice.type]
        speed_min, speed_max = self.limits["speed"]
        tone_min, tone_max = self.limits["tone"]

        self.speed = ui.TextInput(
            label=f"speed [{speed_min}~{speed_max}]",
            placeholder="1.2" if root.voice.type == EngineType.OPEN_JTALK else "1.0",
            default=str(root.voice.speed),
        )
        self.add_item(self.speed)

        self.tone = ui.TextInput(
            label=f"tone [{tone_min}~{tone_max}]",
            placeholder="0.0",
            default=str(root.voice.tone),
        )
        self.add_item(self.tone)

        self.intonation = None
        if (intonation_limits := self.limits["intonation"]) is not None:
            int_min, int_max = intonation_limits
            self.intonation = ui.TextInput(
                label=f"intonation [{int_min}~{int_max}]",
                placeholder="1.0",
                default=str(root.voice.intonation),
            )
            self.add_item(self.intonation)

    async def on_submit(self, interaction: Interaction) -> None:
        try:
            speed = float(self.speed.value)
            tone = float(self.tone.value)
            intonation = float(self.intonation.value) if self.intonation is not None else None
            speed_min, speed_max = self.limits["speed"]
            tone_min, tone_max = self.limits["tone"]
            intonation_limits = self.limits["intonation"]

            if not (speed_min <= speed <= speed_max):
                await interaction.response.send_message(
                    f"⚠⚠ speedは {speed_min} ~ {speed_max} の範囲で入力してください ⚠⚠",
                    delete_after=5.0,
                    ephemeral=True,
                )
                return

            if not (tone_min <= tone <= tone_max):
                await interaction.response.send_message(
                    f"⚠⚠ toneは {tone_min} ~ {tone_max} の範囲で入力してください ⚠⚠",
                    delete_after=5.0,
                    ephemeral=True,
                )
                return

            if intonation_limits is not None and intonation is not None:
                int_min, int_max = intonation_limits
                if not (int_min <= intonation <= int_max):
                    await interaction.response.send_message(
                        f"⚠⚠ intonationは {int_min} ~ {int_max} の範囲で入力してください ⚠⚠",
                        delete_after=5.0,
                        ephemeral=True,
                    )
                    return

            self.root.update_params(speed, tone, intonation)
            await interaction.response.edit_message(view=self.root.view)
        except Exception:
            await interaction.response.send_message(
                "⚠⚠ 数値を入力してください ⚠⚠", delete_after=5.0, ephemeral=True
            )


class VoiceSelectorView(ui.LayoutView):
    """VoiceSelectorContainer を保持する LayoutView"""

    def __init__(
        self,
        sessions: dict[int, "GuildVoiceSession"],
        tts: TTSManager,
        voice: VoiceSetting | None = None,
    ) -> None:
        super().__init__()
        self.container = VoiceSelectorContainer(sessions, tts, voice=voice)
        self.add_item(self.container)
