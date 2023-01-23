import asyncio
import re
from discord import ui, Interaction, SelectOption ,ButtonStyle, Embed, Guild

from .load_config import GC, UC
from .embeds import EmBase
from .systhetic_engines import SyntheticEngines

open_jtalk = 'open_jtalk'
voicevox = 'voicevox'
coeiroink = 'coeiroink'


async def embed(guild:Guild):
    _GC = GC(guild.id)
    g_config = _GC.Read()

    g_voice = g_config['voice']
    res = ''
    res2 = ''
    for k, v in g_voice.items():
        if v == -1: continue
        if k := await guild.fetch_member(int(k)):
            res += f'{k.name}\n'
            res2 += f'{v}\n'
    res = re.sub(r'\n$', '', res)
    res2 = re.sub(r'\n$', '', res2)
    if not res:
        res = 'N/A'
    embed = Embed(colour=EmBase.main_color())
    embed.add_field(name='みんなのボイス', value=f'```{res}```')
    if res2:
        # なんで\n必要なん？？？
        embed.add_field(name="'", value=f'```\n{res2}```')

    res = g_config.get('server_voice', -1)
    if res == -1:
        res = 'N/A'

    embed.add_field(name='サーバーボイス', value=res, inline=False)
    return embed


# Button
class CreateView(ui.View):
    def __init__(self, g_opts, engines:SyntheticEngines, _type=voicevox, voice='ずんだもん'):
        super().__init__(timeout=None)
        self.engines = engines
        self.g_opts = g_opts

        # typeが機能していなかった時のため
        if _type == open_jtalk and not engines.open_jtalk:
            _type = None
        elif _type == voicevox and not engines.voicevox:
            _type = None
        elif _type == coeiroink and not engines.coeiroink:
            _type = None

        if _type == None:
            if engines.open_jtalk:
                _type = open_jtalk
            elif engines.voicevox:
                _type = voicevox
            elif engines.coeiroink:
                _type = coeiroink

        self._type = _type

        self.select = CreateSelect(voice, self)
        self.select2 = CreateSelect2(voice, self)
        self.add_item(self.select)
        self.add_item(self.select2)
        self.add_item(CreateButtonPlay(self))
        self.add_item(CreateButtonSet(self))
        self.add_item(CreateButtonRefresh())
        self.add_item(CreateButtonDel())
        self.add_item(CreateButtonOpenJtalk(self))
        self.add_item(CreateButtonVoicevox(self))
        self.add_item(CreateButtonCoeiroink(self))




class CreateSelect(ui.Select):
    def __init__(self, voice, parent:'CreateView') -> None:
        self.parent = parent

        if parent._type == open_jtalk:
            _type = ''
            sp_list = parent.engines.open_jtalk.metas

        elif parent._type == voicevox:
            _type = 'VOICEVOX:'
            sp_list = parent.engines.voicevox.metas

        elif parent._type == coeiroink:
            _type = 'COEIROINK:'
            sp_list = parent.engines.coeiroink.metas

        select_opt:list[SelectOption] = []
        check = False
        for sp in sp_list:
            _default = False
            if sp['name'] == voice:
                check = True
                _default=True
            select_opt.append(SelectOption(label=f'{_type}{sp["name"]}', value=sp["name"], default=_default))
        if check == False:
            select_opt[0].default = True
        super().__init__(placeholder='キュー表示', options=select_opt, row=1)


    async def callback(self, interaction: Interaction):
        loop = asyncio.get_event_loop()
        loop.create_task(interaction.response.defer())
        await interaction.message.edit(view=CreateView(g_opts=self.parent.g_opts, engines=self.parent.engines, _type=self.parent._type, voice=self.values[0]))



class CreateSelect2(ui.Select):
    def __init__(self, voice, parent:'CreateView') -> None:
        if parent._type == open_jtalk:
            _type = ''
            sp_list = parent.engines.open_jtalk.metas

        elif parent._type == voicevox:
            _type = 'voicevox:'
            sp_list = parent.engines.voicevox.metas

        elif parent._type == coeiroink:
            _type = 'coeiroink:'
            sp_list = parent.engines.coeiroink.metas
        
        styles = None
        for _ in sp_list:
            if _['name'] == voice:
                styles = _['styles']
                break
        if not styles:
            voice = sp_list[0]['name']
            styles = sp_list[0]['styles']

        select_opt = [SelectOption(label=f"{_['name']}", value=f'{_type}{voice}_{_["name"]}') for _ in styles]
        select_opt[0].default = True
        self.voice_res = select_opt[0].value
        super().__init__(placeholder='キュー表示', options=select_opt, row=2)


    async def callback(self, interaction: Interaction):
        self.voice_res = self.values[0]
        await interaction.response.defer()




class CreateButtonPlay(ui.Button):
    def __init__(self, parent:'CreateView') -> None:
        try:
            from ..main import DataInfo
            self.g_opts:dict[int, DataInfo]
        except Exception: pass
        self.g_opts = parent.g_opts
        self.parent = parent
        super().__init__(label='Play', style=ButtonStyle.blurple, row=3)


    async def callback(self, interaction: Interaction):
        loop = asyncio.get_event_loop()
        loop.create_task(interaction.response.defer())

        if Voice := self.g_opts.get(interaction.guild.id):
            Voice = Voice.Voice
            Voice.Queue.append([interaction.id, 0])

            try: source = await Voice.creat_voice(f'voice:{self.parent.select2.voice_res} テストなのだ', interaction)
            except Exception as e:                                              # Error
                print(f"Error : 音声ファイル作成に失敗 {e}")
                Voice.Queue.remove([interaction.id, 0])
                return

            i = Voice.Queue.index([interaction.id, 0])
            Voice.Queue[i:i+1] = [[_,1] for _ in source]

            # 再生されるまでループ
            if not Voice.Vvc.is_playing():
                await Voice.play_loop()



class CreateButtonText(ui.Button):
    def __init__(self, parent:'CreateView') -> None:
        self.parent = parent
        super().__init__(label='読むテキスト', style=ButtonStyle.green, row=3)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        _GC = GC(gid=interaction.guild.id)
        g_config = _GC.Read()
        g_config['voice'][str(interaction.user.id)] = self.parent.select2.voice_res
        _GC.Write(g_config)



class CreateButtonSet(ui.Button):
    def __init__(self, parent:'CreateView') -> None:
        self.parent = parent
        super().__init__(label='ボイスをセット', style=ButtonStyle.grey, row=3)

    async def callback(self, interaction: Interaction):
        new_message = EditVoiceMessage(self.parent.select2.voice_res)
        await interaction.response.send_message(embed=new_message.who_embed, view=new_message.who_view, ephemeral=True)



class CreateButtonRefresh(ui.Button):
    def __init__(self) -> None:
        super().__init__(label='↺', style=ButtonStyle.grey, row=3)

    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(embed=await embed(interaction.guild))



class CreateButtonDel(ui.Button):
    def __init__(self) -> None:
        super().__init__(label='Delete', style=ButtonStyle.red, row=3)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        await interaction.message.delete()



class CreateButtonOpenJtalk(ui.Button):
    def __init__(self, parent:'CreateView') -> None:
        self.parent = parent
        if parent.engines.open_jtalk:
            super().__init__(label='Open_Jtalk', style=ButtonStyle.green, row=0)
        else:
            super().__init__(label='Open_Jtalk', style=ButtonStyle.gray, disabled=True, row=0)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        await interaction.message.edit(view=CreateView(g_opts=self.parent.g_opts, engines=self.parent.engines, _type=open_jtalk))


class CreateButtonVoicevox(ui.Button):
    def __init__(self, parent:'CreateView') -> None:
        self.parent = parent
        if parent.engines.voicevox:
            super().__init__(label='VoiceVox', style=ButtonStyle.green, row=0)
        else:
            super().__init__(label='VoiceVox', style=ButtonStyle.gray, disabled=True, row=0)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        await interaction.message.edit(view=CreateView(g_opts=self.parent.g_opts, engines=self.parent.engines, _type=voicevox))

class CreateButtonCoeiroink(ui.Button):
    def __init__(self, parent:'CreateView') -> None:
        self.parent = parent
        if parent.engines.coeiroink:
            super().__init__(label='Coeiroink', style=ButtonStyle.green, row=0)
        else:
            super().__init__(label='Coeiroink', style=ButtonStyle.gray, disabled=True, row=0)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        await interaction.message.edit(view=CreateView(g_opts=self.parent.g_opts, engines=self.parent.engines, _type=coeiroink))



class EditVoiceMessage:
    def __init__(self, voice) -> None:

        # ネストclass 閉じるの推奨 ------------------------------------------
        class WhoView(ui.View):
            def __init__(self, parent:'EditVoiceMessage'):
                self.parent = parent
                super().__init__(timeout=None)

            @ui.button(label='自分', style=ButtonStyle.blurple)
            async def my_voice(self, interaction:Interaction, button:ui.Button):
                gid = interaction.guild_id
                _GC = GC(gid)
                g_config = _GC.Read()
                
                if interaction.user.guild_permissions.administrator or not g_config['admin_only'].setdefault('my_voice',False):
                    await interaction.response.edit_message(embed=self.parent.my_embed, view=self.parent.my_view)
                else:
                    await interaction.response.edit_message(embed=EmBase.failed(), view=None)

                _GC.Write(g_config)
                

            @ui.button(label='他人', style=ButtonStyle.blurple)
            async def another_voice(self, interaction:Interaction, button:ui.Button):
                gid = interaction.guild_id
                _GC = GC(gid)
                g_config = _GC.Read()
                
                if interaction.user.guild_permissions.administrator or not g_config['admin_only'].setdefault('another_voice',True):
                    await interaction.response.edit_message(embed=self.parent.who_other_embed, view=self.parent.who_other_view)
                else:
                    await interaction.response.edit_message(embed=EmBase.failed(), view=None)

                _GC.Write(g_config)



        class MyView(ui.View):
            def __init__(self, parent:'EditVoiceMessage'):
                self.parent = parent
                super().__init__(timeout=None)

            @ui.button(label='このサーバーのみ反映', style=ButtonStyle.blurple)
            async def server_voice(self, interaction:Interaction, button:ui.Button):
                gid = interaction.guild_id
                uid = interaction.user.id
                _GC = GC(gid)
                g_config = _GC.Read()
                g_config['voice'][str(uid)] = self.parent.voice
                _GC.Write(g_config)
                await interaction.response.edit_message(embed=self.parent.success_embed, view=None)


            @ui.button(label='自分の初期ボイス', style=ButtonStyle.blurple)
            async def my_voice(self, interaction:Interaction, button:ui.Button):
                uid = interaction.user.id
                u_config = UC.Read(uid)
                u_config['voice'] = self.parent.voice
                UC.Write(uid, u_config)
                await interaction.response.edit_message(embed=self.parent.success_embed, view=None)



        class WhoOtherView(ui.View):
            def __init__(self, parent:'EditVoiceMessage'):
                self.parent = parent
                super().__init__(timeout=None)

            @ui.select(cls=ui.UserSelect, placeholder='ターゲットを選ぼう！')
            async def my_voice(self, interaction:Interaction, select:ui.UserSelect):
                user = select.values[0]
                gid = interaction.guild_id
                _GC = GC(gid)
                g_config = _GC.Read()
                g_config['voice'][str(user.id)] = self.parent.voice
                _GC.Write(g_config)
                embed = Embed(title='反映完了!', description=f'{user.name} : {voice}', colour=EmBase.main_color())

                await interaction.response.edit_message(embed=embed, view=None)



        self.voice = voice
        self.who_embed = Embed(title=voice, description='誰のボイスを変更しますか？', colour=EmBase.main_color())
        self.who_other_embed = Embed(title=voice, description='誰のボイスを変更しますか？\n※このサーバーにだけ反映されます', colour=EmBase.main_color())
        self.my_embed = Embed(title=voice, description='どちらにしますか？', colour=EmBase.main_color())
        self.my_embed.add_field(name='このサーバーのみ反映', value='サーバー毎に設定できます。どちらもボイスが指定されてた場合、こっちの方が優先されます')
        self.my_embed.add_field(name='自分の初期ボイス', value='1人1つ指定できます。他のサーバーと同期しています。')
        self.success_embed = Embed(title='反映完了!', description=voice, colour=EmBase.main_color())
        self.who_view = WhoView(self)
        self.who_other_view = WhoOtherView(self)
        self.my_view = MyView(self)




