import asyncio
import copy
import logging
import math
from discord import Member, ui, Interaction, ButtonStyle, Embed
from typing import TYPE_CHECKING, TypedDict

from pi_yo_6.message_unit import MessageUnit
from pi_yo_6.utils import ENGINE_TYPE, VoiceUnit

from .load_config import  UserConfig
from .embeds import EmBase
from .synthetic_voice import SyntheticEngines

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


# Button
class VoiceListContainer(ui.Container):
    def __init__(self, g_opts:dict[int, "DataInfo"], voice:VoiceUnit|None=None):
        super().__init__(accent_color=EmBase.main_color())
        self.g_opts = g_opts
        self.voice = copy.deepcopy(voice) if voice else VoiceUnit(ENGINE_TYPE.OPEN_JTALK, "mei", "normal")
        self.res_styles:list[VLStyleMeta] = []

        engines = SyntheticEngines.current
        self.add_item(ui.ActionRow(
            EngineButton(self, ENGINE_TYPE.OPEN_JTALK, engines.open_jtalk != None),
            EngineButton(self, ENGINE_TYPE.VOICEVOX, engines.voicevox != None),
            EngineButton(self, ENGINE_TYPE.COEIROINK, engines.coeiroink != None)
        ))
        self.voice_authors_selection = ui.Select(placeholder='キャラクター選択', row=1)
        self.voice_authors_selection.callback = self._voice_authors_selection_callback
        self.add_item(ui.ActionRow(self.voice_authors_selection))
        self.voice_styles_selection = ui.Select(placeholder='スタイル選択', row=2)
        self.voice_styles_selection.callback = self._voice_styles_selection_callback
        self.add_item(ui.ActionRow(self.voice_styles_selection))
        self.add_item(ControllerRow(self))
    
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


    async def _voice_authors_selection_callback(self, interaction: Interaction):
        asyncio.create_task(interaction.response.defer())
        if interaction.message:
            self.voice.name = self.voice_authors_selection.values[0]
            self.set_new_select_options()
            await interaction.message.edit(view=self.view)
    

    async def _voice_styles_selection_callback(self, interaction: Interaction):
        try:
            style = self.res_styles[int(self.voice_styles_selection.values[0])]
            self.voice.name = style['author']
            self.voice.style = style['name']
        except Exception as e:
            _log.error("スタイルの取得に失敗しました", e)
        await interaction.response.defer()



'''
@ui.button(...)とかはfunctionに...のデータを埋め込むだけ
インスタンスを作る際にButtonクラスなどは作られる様子。
'''

class ControllerRow(ui.ActionRow):
    def __init__(self, root:VoiceListContainer) -> None:
        super().__init__()
        self.root = root

    @ui.button(label='Play', style=ButtonStyle.blurple)
    async def text_play_button(self, interaction: Interaction, button: ui.Button, row=3):
        asyncio.create_task(interaction.response.defer())

        if not interaction.guild: return
        if data := self.root.g_opts.get(interaction.guild.id):
            msg = MessageUnit("テストなのだ")
            msg.voice = self.root.voice
            await data.voice.play_message(msg)



    @ui.button(label='ボイスをセット', style=ButtonStyle.blurple)
    async def set_voice_button(self, interaction: Interaction, button: ui.Button):
        if isinstance(interaction.user, Member) and interaction.user.guild_permissions.administrator:
            new_message = EditVoiceMessage(self.root.voice)
            await interaction.response.send_message(embed=new_message.who_embed, view=new_message.who_view, ephemeral=True)
        else:
            uc = UserConfig.get(interaction.user.id)
            uc.data.voice = self.root.voice
            uc.write()
            await interaction.response.send_message(embed=Embed(title='反映完了!', description=self.root.voice, colour=EmBase.main_color()), ephemeral=True)


    @ui.button(label='Delete', style=ButtonStyle.red)
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
        







class EditVoiceMessage:
    def __init__(self, voice) -> None:

        # ネストclass 閉じるの推奨 ------------------------------------------
        class WhoView(ui.View):
            def __init__(self, parent:'EditVoiceMessage'):
                self.parent = parent
                super().__init__(timeout=None)


            @ui.button(label='自分', style=ButtonStyle.green)
            async def my_voice(self, interaction:Interaction, button:ui.Button):
                if not interaction.guild: return 

                uc = UserConfig.get(interaction.user.id)
                uc.data.voice = voice
                uc.write()
                
                await interaction.response.edit_message(embed=self.parent.success_embed, view=None)
                

            @ui.button(label='他人', style=ButtonStyle.green)
            async def another_voice(self, interaction:Interaction, button:ui.Button):
                if not interaction.guild: return 
                if not isinstance(interaction.user, Member): return
                
                if interaction.user.guild_permissions.administrator:
                    await interaction.response.edit_message(embed=self.parent.who_other_embed, view=self.parent.who_other_view)
                else:
                    await interaction.response.edit_message(embed=EmBase.no_perm(), view=None)



        class WhoOtherView(ui.View):
            def __init__(self, parent:'EditVoiceMessage'):
                self.parent = parent
                super().__init__(timeout=None)

            @ui.select(cls=ui.UserSelect, placeholder='ターゲットを選ぼう！')
            async def my_voice(self, interaction:Interaction, select:ui.UserSelect):
                user = select.values[0]
                uc = UserConfig.get(user.id)
                uc.data.voice = voice
                uc.write()
                embed = Embed(title='反映完了!', description=f'{user.name} : {voice}', colour=EmBase.main_color())

                await interaction.response.edit_message(embed=embed, view=None)



        self.voice = voice
        self.who_embed = Embed(title=voice, description='誰のボイスを変更しますか？', colour=EmBase.main_color())
        self.who_other_embed = Embed(title=voice, description='誰のボイスを変更しますか？\n※このサーバーにだけ反映されます', colour=EmBase.main_color())
        self.success_embed = Embed(title='反映完了!', description=voice, colour=EmBase.main_color())
        self.who_view = WhoView(self)
        self.who_other_view = WhoOtherView(self)




