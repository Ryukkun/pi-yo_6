import asyncio
import copy
import logging
import math
from discord import ui, Interaction, ButtonStyle, Embed
from typing import TYPE_CHECKING, TypedDict

from pi_yo_6.message_unit import MessageUnit
from pi_yo_6.utils import ENGINE_TYPE, VoiceUnit
from pi_yo_6.load_config import  UserConfig
from pi_yo_6.embeds import EmBase
from pi_yo_6.synthetic_voice import SyntheticEngines

if TYPE_CHECKING:
    from pi_yo_6.main import DataInfo


_log = logging.getLogger(__name__)


class VLStyleMeta(TypedDict):
    name:str
    id:str
    author:str

class VLSpeakerMeta(TypedDict):
    name:list[str]
    styles:list[VLStyleMeta]



'''
@ui.button(...)とかはfunctionに...のデータを埋め込むだけ
インスタンスを作る際にButtonインスタンスなどは作られる様子。
'''

class VoiceListContainer(ui.Container):
    def __init__(self, g_opts:dict[int, "DataInfo"], voice:VoiceUnit|None=None):
        super().__init__(accent_color=EmBase.main_color())
        self.g_opts = g_opts
        self.voice = copy.deepcopy(voice) if voice else VoiceUnit(ENGINE_TYPE.OPEN_JTALK, "mei", "normal")

        self.set_num()
        engines = SyntheticEngines.current
        for row in self.walk_children():
            if isinstance(row, ui.ActionRow) and len(row.children) == 0:
                row.add_item(EngineButton(self, ENGINE_TYPE.OPEN_JTALK, engines.open_jtalk != None))
                row.add_item(EngineButton(self, ENGINE_TYPE.VOICEVOX, engines.voicevox != None))
                row.add_item(EngineButton(self, ENGINE_TYPE.COEIROINK, engines.coeiroink != None))
                break
        self.res_styles:list[VLStyleMeta] = []

        self.set_new_select_options()



    def set_new_select_options(self):
        # typeが機能していなかった時のため
        engines = SyntheticEngines.current
        if self.voice.type == ENGINE_TYPE.VOICEVOX and engines.voicevox:
            _metas = copy.deepcopy(engines.voicevox.metas)
        elif self.voice.type == ENGINE_TYPE.COEIROINK and engines.coeiroink:
            _metas = copy.deepcopy(engines.coeiroink.metas)
        else:
            self.voice.type = ENGINE_TYPE.OPEN_JTALK
            _metas = copy.deepcopy(engines.open_jtalk.metas)


        """
        25人以上のボイスに対応する都合上、注意事項が何個か
        - Speakerのnameには複数の名前が含まれることがある (list[str])
        - Styleにauthor追加 そのスタイルの声の主
        """
        for s in _metas:
            for st in s['styles']:
                st['id'] = s['name']

        # 25以上の場合圧縮処理
        metas: list[VLSpeakerMeta] = []
        booking = math.ceil(len(_metas) / 25)
        for i in range(0, len(_metas), booking):
            parts = _metas[i:i+booking]
            flat_style:list[VLStyleMeta] = []
            for part in parts:
                for style in part['styles']:
                    flat_style.append({
                        "author": part['name'],
                        "name": style['name'],
                        "id": style["id"]
                    })
            merged:VLSpeakerMeta = {
                "name" : [_['name'] for _ in parts],
                "styles" : flat_style
            }
            metas.append(merged)
            
        # voiceAuthorsの選択肢生成
        self.voice_authors_selection.options.clear()
        has_default = False
        for i in range(min(len(metas), 25)):
            meta = metas[i]
            if (default := (self.voice.name in meta['name'] and not has_default)): has_default = True
            self.voice_authors_selection.add_option(label=", ".join(meta["name"]), value=meta["name"][0], default=default)
        ### どれ一つヒットしなかった場合初期値に指定
        if not has_default:
            self.voice.name = metas[0]['styles'][0]['author']
            self.voice_authors_selection.options[0].default = True


        # voiceStylesの選択肢生成
        self.voice_styles_selection.options.clear()
        self.res_styles.clear()
        has_default = False
        styles:list[VLStyleMeta] = []
        for meta in metas:
            if self.voice.name in meta['name']:
                styles = meta['styles']
                break
        for i in range(min(len(styles), 25)):
            style = styles[i]
            self.res_styles.append(style)
            if (default := (self.voice.style == style['name'] and self.voice.name == style['author'] and not has_default)): has_default = True
            self.voice_styles_selection.add_option(label=f"{style['author']}_{style['name']}", value=str(i), default=default)
        ### どれ一つヒットしなかった場合初期値に指定
        if not has_default: 
            self.voice.style = styles[0]['name']
            self.voice_styles_selection.options[0].default = True
    
    row_1 = ui.TextDisplay("## ボイス設定")

    row0 = ui.ActionRow()

    row1 = ui.ActionRow()
    @row1.select(placeholder='キャラクター選択')
    async def voice_authors_selection(self, interaction: Interaction, select: ui.Select):
        if interaction.message:
            self.voice.name = self.voice_authors_selection.values[0]
            self.set_new_select_options()
            await interaction.response.edit_message(view=self.view)
    

    row2 = ui.ActionRow()
    @row2.select(placeholder='スタイル選択')
    async def voice_styles_selection(self, interaction: Interaction, select: ui.Select):
        try:
            style = self.res_styles[int(self.voice_styles_selection.values[0])]
            self.voice.name = style['author']
            self.voice.style = style['name']
            self.set_new_select_options()
            await interaction.response.edit_message(view=self.view)
            return
        except Exception as e:
            _log.error("スタイルの取得に失敗しました", e)
        await interaction.response.defer()



    row3 = ui.ActionRow()
    @row3.button(style=ButtonStyle.blurple)
    async def speed_button(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_modal(SpeedPitchModal(self))


    def set_num(self, speed:float|None = None, tone:float|None = None, intonation:float|None = None):
        if speed != None: self.voice.speed = speed
        if tone != None: self.voice.tone = tone
        if intonation != None: self.voice.intonation = intonation
        self.speed_button.label = f"Speed: {self.voice.speed},  Tone: {self.voice.tone}, Intonation: {self.voice.intonation}"


    @row3.button(label='Play', style=ButtonStyle.green)
    async def text_play_button(self, interaction: Interaction, button: ui.Button):
        asyncio.create_task(interaction.response.defer())
        if not interaction.guild: return
        if data := self.g_opts.get(interaction.guild.id):
            msg = MessageUnit("テストなのだ")
            msg.voice = self.voice
            await data.voice.play_message(msg)


    @row3.button(label='ボイスをセット', style=ButtonStyle.green)
    async def set_voice_button(self, interaction: Interaction, button: ui.Button):
        uc = UserConfig.get(interaction.user.id)
        uc.data.voice = self.voice
        uc.write()
        await interaction.response.send_message(embed=Embed(title='反映完了!', description=self.voice, colour=EmBase.main_color()), ephemeral=True)


    @row3.button(label='Delete', style=ButtonStyle.red)
    async def delete_button(_, interaction: Interaction, button:ui.Button):
        await interaction.response.defer()
        if interaction.message:
            await interaction.message.delete()



class EngineButton(ui.Button):
    def __init__(self, root: VoiceListContainer, type: ENGINE_TYPE, enable: bool):
        self.root = root
        self.engine_type = type
        super().__init__(style=ButtonStyle.green if enable else ButtonStyle.gray, label=type, disabled=not enable, row=0)
        
    async def callback(self, interaction: Interaction):
        if interaction.message:
            self.root.voice.type = self.engine_type
            self.root.voice.name = ""
            self.root.voice.style = ""
            self.root.set_new_select_options()
            await interaction.message.edit(view=self.view)
        


class SpeedPitchModal(ui.Modal):
    def __init__(self, root:"VoiceListContainer") -> None:
        super().__init__(title="詳細設定")
        self.root = root
        self.speed = ui.TextInput(
            label="speed [0.5~100.0]",
            placeholder="1.2",
            default=str(root.voice.speed)
            )
        self.add_item(self.speed)

        self.tone = ui.TextInput(
            label="tone [-100.0~100.0]",
            placeholder="0.0",
            default=str(root.voice.tone)
            )
        self.add_item(self.tone)

        self.intonation = None
        if root.voice.type != ENGINE_TYPE.OPEN_JTALK:
            self.intonation = ui.TextInput(
                label="intonation [-100.0~100.0]",
                placeholder="0.0",
                default=str(root.voice.intonation)
            )
            self.add_item(self.intonation)


    async def on_submit(self, interaction: Interaction) -> None:
        try:
            speed = float(self.speed.value)
            tone = float(self.tone.value)
            intonation = float(self.intonation.value) if self.intonation != None else None
            if (speed < 0.5):
                await interaction.response.send_message("⚠⚠ speedは0.5以上にしてください ⚠⚠", delete_after=5.0, ephemeral=True)
                return
            
            if (-100 <= speed <= 100 and -100 <= tone <= 100 and (intonation == None or -100 <= intonation <= 100)):
                self.root.set_num(speed, tone, intonation)
                await interaction.response.edit_message(view=self.root.view)
                return
            
            await interaction.response.send_message("⚠⚠ -100以上100以下でおねがい ⚠⚠", delete_after=5.0, ephemeral=True)

        except Exception:
            await interaction.response.send_message("⚠⚠ 数値を入力してください ⚠⚠", delete_after=5.0, ephemeral=True)