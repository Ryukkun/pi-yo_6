import asyncio
from discord import Member, ui, Interaction, SelectOption ,ButtonStyle, Embed, Guild
from typing import TYPE_CHECKING

from pi_yo_6.message_unit import MessageUnit
from pi_yo_6.utils import ENGINE_TYPE, VoiceUnit

from .load_config import  UserConfig
from .embeds import EmBase
from .synthetic_voice import SyntheticEngines

if TYPE_CHECKING:
    from pi_yo_6.main import DataInfo


# Button
class CreateView(ui.View):
    def __init__(self, g_opts:dict[int, "DataInfo"], engines:SyntheticEngines, _type:ENGINE_TYPE=ENGINE_TYPE.OPEN_JTALK, voice='mei_normal'):
        super().__init__(timeout=None)
        self.engines = engines
        self.g_opts = g_opts

        # typeが機能していなかった時のため
        if _type == ENGINE_TYPE.VOICEVOX and not engines.voicevox:
            _type = ENGINE_TYPE.OPEN_JTALK
        if _type == ENGINE_TYPE.COEIROINK and not engines.coeiroink:
            _type = ENGINE_TYPE.OPEN_JTALK

        self._type = _type

        self.select = VoiceAuthorSelect(voice, self)
        self.select2 = VoiceStyleSelect(voice, self)
        self.add_item(self.select)
        self.add_item(self.select2)
        self.add_item(TextPlayButton(self))
        self.add_item(SetVoiceButton(self))
        self.add_item(DeleteButton())
        self.add_item(OpenJtalkButton(self))
        self.add_item(VoicevoxButton(self))
        self.add_item(CoeiroinkButton(self))




class VoiceAuthorSelect(ui.Select):
    def __init__(self, voice, parent_view:'CreateView') -> None:
        self.parent_view = parent_view
        engine_name = ''
        sp_list = []
        if parent_view._type == ENGINE_TYPE.OPEN_JTALK and parent_view.engines.open_jtalk:
            sp_list = parent_view.engines.open_jtalk.metas

        elif parent_view._type == ENGINE_TYPE.VOICEVOX and parent_view.engines.voicevox:
            engine_name = 'VOICEVOX:'
            sp_list = parent_view.engines.voicevox.metas

        elif parent_view._type == ENGINE_TYPE.COEIROINK and parent_view.engines.coeiroink:
            engine_name = 'COEIROINK:'
            sp_list = parent_view.engines.coeiroink.metas

        select_opt:list[SelectOption] = []
        check = False
        for sp in sp_list:
            _default = False
            if sp['name'] == voice:
                check = True
                _default=True
            if len(select_opt) < 25:
                select_opt.append(SelectOption(label=f'{engine_name}{sp["name"]}', value=sp["name"], default=_default))
        if check == False:
            select_opt[0].default = True
        super().__init__(placeholder='キュー表示', options=select_opt, row=1)


    async def callback(self, interaction: Interaction):
        loop = asyncio.get_event_loop()
        loop.create_task(interaction.response.defer())
        if interaction.message:
            await interaction.message.edit(view=CreateView(g_opts=self.parent_view.g_opts, engines=self.parent_view.engines, _type=self.parent_view._type, voice=self.values[0]))



class VoiceStyleSelect(ui.Select):
    def __init__(self, voice, parent_view:'CreateView') -> None:
        self.parent_view = parent_view
        sp_list = []
        if parent_view._type == ENGINE_TYPE.OPEN_JTALK and parent_view.engines.open_jtalk:
            sp_list = parent_view.engines.open_jtalk.metas

        elif parent_view._type == ENGINE_TYPE.VOICEVOX and parent_view.engines.voicevox:
            sp_list = parent_view.engines.voicevox.metas

        elif parent_view._type == ENGINE_TYPE.COEIROINK and parent_view.engines.coeiroink:
            sp_list = parent_view.engines.coeiroink.metas
        
        styles = None
        for _ in sp_list:
            if _['name'] == voice:
                styles = _['styles']
                break
        if not styles:
            voice = sp_list[0]['name']
            styles = sp_list[0]['styles']

        select_opt = [SelectOption(label=f"{_['name']}", value=_['id']) for _ in styles]
        select_opt[0].default = True
        self.voice_res = VoiceUnit(type=parent_view._type, id=select_opt[0].value)
        super().__init__(placeholder='キュー表示', options=select_opt, row=2)


    async def callback(self, interaction: Interaction):
        self.voice_res = VoiceUnit(type=self.parent_view._type, id=self.values[0])
        await interaction.response.defer()




class TextPlayButton(ui.Button):
    def __init__(self, parent_view:'CreateView') -> None:
        self.g_opts = parent_view.g_opts
        self.parent_view = parent_view
        super().__init__(label='Play', style=ButtonStyle.blurple, row=3)


    async def callback(self, interaction: Interaction):
        loop = asyncio.get_event_loop()
        loop.create_task(interaction.response.defer())

        if not interaction.guild: return
        if data := self.g_opts.get(interaction.guild.id):
            msg = MessageUnit("テストなのだ", self.parent_view.engines)
            msg.voice = self.parent_view.select2.voice_res
            await data.voice.play_message(msg)



class SetVoiceButton(ui.Button):
    def __init__(self, parent_view:'CreateView') -> None:
        self.parent_view = parent_view
        super().__init__(label='ボイスをセット', style=ButtonStyle.blurple, row=3)

    async def callback(self, interaction: Interaction):
        voice = self.parent_view.select2.voice_res
        if isinstance(interaction.user, Member) and interaction.user.guild_permissions.administrator:
            new_message = EditVoiceMessage(voice)
            await interaction.response.send_message(embed=new_message.who_embed, view=new_message.who_view, ephemeral=True)

        else:
            uc = UserConfig.get(interaction.user.id)
            uc.data.voice = voice
            uc.write()
            await interaction.response.send_message(embed=Embed(title='反映完了!', description=voice, colour=EmBase.main_color()), ephemeral=True)



class DeleteButton(ui.Button):
    def __init__(self) -> None:
        super().__init__(label='Delete', style=ButtonStyle.red, row=3)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        if interaction.message:
            await interaction.message.delete()



class OpenJtalkButton(ui.Button):
    def __init__(self, parent_view:'CreateView') -> None:
        self.parent_view = parent_view
        if parent_view.engines.open_jtalk:
            super().__init__(label='Open_Jtalk', style=ButtonStyle.green, row=0)
        else:
            super().__init__(label='Open_Jtalk', style=ButtonStyle.gray, disabled=True, row=0)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        if interaction.message:
            await interaction.message.edit(view=CreateView(g_opts=self.parent_view.g_opts, engines=self.parent_view.engines, _type=ENGINE_TYPE.OPEN_JTALK))


class VoicevoxButton(ui.Button):
    def __init__(self, parent_view:'CreateView') -> None:
        self.parent_view = parent_view
        if parent_view.engines.voicevox:
            super().__init__(label='VoiceVox', style=ButtonStyle.green, row=0)
        else:
            super().__init__(label='VoiceVox', style=ButtonStyle.gray, disabled=True, row=0)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        if interaction.message:
            await interaction.message.edit(view=CreateView(g_opts=self.parent_view.g_opts, engines=self.parent_view.engines, _type=ENGINE_TYPE.VOICEVOX))

class CoeiroinkButton(ui.Button):
    def __init__(self, parent_view:'CreateView') -> None:
        self.parent_view = parent_view
        if parent_view.engines.coeiroink:
            super().__init__(label='Coeiroink', style=ButtonStyle.green, row=0)
        else:
            super().__init__(label='Coeiroink', style=ButtonStyle.gray, disabled=True, row=0)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        if interaction.message:
            await interaction.message.edit(view=CreateView(g_opts=self.parent_view.g_opts, engines=self.parent_view.engines, _type=ENGINE_TYPE.COEIROINK))



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
                gid = interaction.guild_id
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




