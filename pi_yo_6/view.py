import asyncio
from discord import ui, Interaction, SelectOption ,ButtonStyle

from .voicevox.speaker_id import speaker_list, speaker_id



# Button
class CreateView(ui.View):
    def __init__(self, g_opts, voice='ずんだもん'):
        super().__init__(timeout=None)
        self.g_opts = g_opts
        self.select = CreateSelect(voice, self)
        self.select2 = CreateSelect2(voice)
        self.add_item(self.select)
        self.add_item(self.select2)
        self.add_item(CreateButton(g_opts, self))






class CreateSelect(ui.Select):
    def __init__(self, voice, parent:'CreateView') -> None:
        self.parent = parent
        sp_list = speaker_list()
        select_opt = []
        for sp in sp_list:
            if sp[0] == voice:
                select_opt.append(SelectOption(label=sp[0], value=sp[0], default=True))
            else:
                select_opt.append(SelectOption(label=sp[0], value=sp[0]))
        super().__init__(placeholder='キュー表示', options=select_opt, row=0)


    async def callback(self, interaction: Interaction):
        loop = asyncio.get_event_loop()
        loop.create_task(interaction.response.defer())
        await interaction.message.edit(view=CreateView(g_opts=self.parent.g_opts, voice=self.values[0]))



class CreateSelect2(ui.Select):
    def __init__(self, voice) -> None:
        for _ in speaker_id:
            if _['name'] == voice:
                styles = _['styles']
                break
        
        select_opt = [SelectOption(label=f"{_['name']} [{_['id']}]", value=_['id']) for _ in styles]
        select_opt[0].default = True
        self._value = select_opt[0].value
        super().__init__(placeholder='キュー表示', options=select_opt, row=1)


    async def callback(self, interaction: Interaction):
        self._value = self.values[0]
        await interaction.response.defer()




class CreateButton(ui.Button):
    def __init__(self, g_opts, parent:'CreateView') -> None:
        try:
            from ..main import DataInfo
            self.g_opts:dict[int, DataInfo]
        except Exception: pass
        self.g_opts = g_opts
        self.parent = parent
        super().__init__(label='Play', style=ButtonStyle.blurple, row=2)


    async def callback(self, interaction: Interaction):
        loop = asyncio.get_event_loop()
        loop.create_task(interaction.response.defer())

        if Voice := self.g_opts.get(interaction.guild.id):
            Voice = Voice.Voice
            Voice.Queue.append([interaction.id, 0])

            try: source = await Voice.creat_voice(f'voice:{self.parent.select2._value} テストなのだ', interaction)
            except Exception as e:                                              # Error
                print(f"Error : 音声ファイル作成に失敗 {e}")
                Voice.Queue.remove([interaction.id, 0])
                return

            i = Voice.Queue.index([interaction.id, 0])
            Voice.Queue[i:i+1] = [[_,1] for _ in source]

            # 再生されるまでループ
            if not Voice.Vvc.is_playing():
                await Voice.play_loop()