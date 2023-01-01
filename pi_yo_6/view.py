import asyncio
import time
from discord import ui, Interaction, SelectOption ,ButtonStyle, Message
import glob

from .voicevox.speaker_id import speaker_list, speaker_id
from .audio_source import StreamAudioData as SAD
from .load_config import GC, UC



# Button
class CreateView(ui.View):
    def __init__(self,voice='ずんだもん'):
        super().__init__(timeout=None)
        self.add_item(CreateSelect())
        self.add_item(CreateSelect2(voice))
        self.add_item(CreateTextInput())
        self.add_item(CreateButton())






class CreateSelect(ui.Select):
    def __init__(self) -> None:
        sp_list = speaker_list()
        sp_list = [SelectOption(label=_[0], value=_[0]) for _ in sp_list]
        super().__init__(placeholder='キュー表示', options=sp_list, row=0)


    async def callback(self, interaction: Interaction):
        #await interaction.response.send_message(f'{interaction.user.name}は{self.values[0]}を選択しました')
        loop = asyncio.get_event_loop()
        loop.create_task(interaction.response.defer())
        await interaction.message.edit(view=CreateView(voice=self.values[0]))
        #print(f'{interaction.user.name}は{self.values[0]}を選択しました')



class CreateSelect2(ui.Select):
    def __init__(self, voice) -> None:
        for _ in speaker_id:
            if _['name'] == voice:
                styles = _['styles']
                break
        
        select_opt = [SelectOption(label=_['name'], value=_['id']) for _ in styles]
        super().__init__(placeholder='キュー表示', options=select_opt, row=0)


    async def callback(self, interaction: Interaction):
        #await interaction.response.send_message(f'{interaction.user.name}は{self.values[0]}を選択しました')
        loop = asyncio.get_event_loop()
        loop.create_task(interaction.response.defer())
        await interaction.message.edit(view=CreateView(voice=self.values[0]))
        #print(f'{interaction.user.name}は{self.values[0]}を選択しました')


class CreateTextInput(ui.TextInput):
    def __init__(self) -> None:
        super().__init__(placeholder='読むテキスト', required=True, default='テストでーす', row=0)


    # async def callback(self, interaction: Interaction):
    #     #await interaction.response.send_message(f'{interaction.user.name}は{self.values[0]}を選択しました')
    #     loop = asyncio.get_event_loop()
    #     loop.create_task(interaction.response.defer())
    #     #print(f'{interaction.user.name}は{self.values[0]}を選択しました')




class CreateButton(ui.Button):
    def __init__(self) -> None:
        super().__init__(label='Play', style=ButtonStyle.blurple, row=0)


    async def callback(self, interaction: Interaction):
        loop = asyncio.get_event_loop()
        loop.create_task(interaction.response.defer())

        # 音声ファイル ファイル作成
        try: source = await self.creat_voice(text, message)
        except Exception as e:                                              # Error
            print(f"Error : 音声ファイル作成に失敗 {e}")
            self.Queue.remove([message.id, 0])
            return

        print(f'生成時間 : {time.perf_counter()-now_time}')
        i = self.Queue.index([message.id, 0])
        self.Queue[i:i+1] = [[_,1] for _ in source]

        # 再生されるまでループ
        if not self.Vvc.is_playing():
            await self.play_loop()