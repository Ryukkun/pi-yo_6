import asyncio
from discord import ui, Interaction, SelectOption ,ButtonStyle, Embed, Guild

from .voicevox.speaker_id import speaker_list, speaker_id
from .load_config import GC
from .embeds import EmBase


async def embed(guild:Guild):
    _GC = GC(guild.id)
    g_config = _GC.Read()

    g_voice = g_config['voice']
    res = res2 = ''
    for k, v in g_voice.items():
        if v == -1: continue
        if k := await guild.fetch_member(int(k)):
            res += f'{k.name}\n'
            res2 += f'{v}\n'
    res = res.removesuffix('\n')
    res2 = res2.removesuffix('\n')
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
    def __init__(self, g_opts, voice='ずんだもん'):
        super().__init__(timeout=None)
        self.g_opts = g_opts
        self.select = CreateSelect(voice, self)
        self.select2 = CreateSelect2(voice)
        self.add_item(self.select)
        self.add_item(self.select2)
        self.add_item(CreateButtonPlay(self))
        self.add_item(CreateButtonSet(self))
        self.add_item(CreateButtonRefresh())
        self.add_item(CreateButtonDel())






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
        self.voice_res = select_opt[0].value
        super().__init__(placeholder='キュー表示', options=select_opt, row=1)


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
        super().__init__(label='Play', style=ButtonStyle.blurple, row=2)


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
        super().__init__(label='読むテキスト', style=ButtonStyle.green, row=2)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        _GC = GC(gid=interaction.guild.id)
        g_config = _GC.Read()
        g_config['voice'][str(interaction.user.id)] = self.parent.select2.voice_res
        _GC.Write(g_config)



class CreateButtonSet(ui.Button):
    def __init__(self, parent:'CreateView') -> None:
        self.parent = parent
        super().__init__(label='自分の声にセット', style=ButtonStyle.grey, row=2)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        _GC = GC(interaction.guild.id)
        g_config = _GC.Read()
        g_config['voice'][str(interaction.user.id)] = self.parent.select2.voice_res
        _GC.Write(g_config)
        await interaction.message.edit(embed=await embed(interaction.guild))



class CreateButtonRefresh(ui.Button):
    def __init__(self) -> None:
        super().__init__(label='↺', style=ButtonStyle.grey, row=2)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        await interaction.message.edit(embed=await embed(interaction.guild))



class CreateButtonDel(ui.Button):
    def __init__(self) -> None:
        super().__init__(label='Delete', style=ButtonStyle.red, row=2)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        await interaction.message.delete()