import asyncio
import discord
from discord.ext import commands
from discord.interactions import Interaction
from faster_whisper import WhisperModel

from pi_yo_6.discord.voice_client import MyVoiceClient
from pi_yo_6.chatgpt import ChatGPTThread
from pi_yo_6.voice import ChatReader



class WhisperModelWrapper:
    def __init__(self):
        self.model_size_or_path = "medium"
        self.model = WhisperModel(
            self.model_size_or_path, device="cuda", compute_type="int8"
        )

    def get_segment(self, audio):
        segments, _ = self.model.transcribe(
            audio=audio, beam_size=2, language="ja", without_timestamps=True 
        )
        return segments



class SiriMessage:
    embed = discord.Embed(title='文字起こし')
    whisper = WhisperModelWrapper()

    def __init__(self, vc:MyVoiceClient, voice:ChatReader, message:discord.Message = None) -> None:
        self.message = message
        self.vc = vc
        self.loop = vc.client.loop
        self.chatgpt = ChatGPTThread()
        self.voice = voice

    @classmethod
    async def from_ctx(cls, ctx:commands.Context, voice:ChatReader):
        self = SiriMessage(ctx.voice_client, voice)
        message = await ctx.send(embed=cls.embed, view=SiriView(self))
        self.message = message
        return self


    async def start_transcribe(self):
        self.vc.record_start()
        await self.update_view()
        ROMA = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
        text = []
        user = {}

        async def fin():
            await asyncio.sleep(20)
            if self.vc.is_recording:
                self.vc.record_fin()

        def transcribe(ssrc, adata):
            segments = self.whisper.get_segment(adata)
            for segment in segments:
                _text = segment.text
                if not 'ご視聴ありがとうございました' in _text:
                    text.append({"ssrc":ssrc, "text":_text})
                    self.loop.create_task(generate_embed())

        async def generate_embed():
            res_text = ''
            last_ssrc = None
            for _text in text:
                if last_ssrc != _text['ssrc']:
                    last_ssrc = _text['ssrc']
                    if name := user.get(last_ssrc):
                        pass
                    else:
                        name = ROMA[len(user.keys())]
                        user[last_ssrc] = name
                    
                    res_text += f'\n{name} : {_text["text"]}'

                else:
                    res_text += f' {_text["text"]}'
            
            _em = self.embed.copy()
            _em.description = res_text
            await self.message.edit(embed=_em)


        self.loop.create_task(fin())
        while True:
            _, adata = await self.vc.buffer.get_speaking_chunk()
            if _ == None:
                break
            
            await self.loop.run_in_executor(None, transcribe,_,adata)

        # ssrc_text = defaultdict(str)
        # for _ in text:
        #     ssrc_text[_['ssrc']] += _['text']
        
        # ssrc_text = list(ssrc_text.values())
        # ssrc_text.sort(key=lambda x:len(x))
        # ssrc_text = ssrc_text[-1]
        self.loop.create_task(self.update_view())
        ssrc_text = ''
        for _ in text:
            ssrc_text += f" {_['text']}"

        _res:str = self.chatgpt.ask(ssrc_text)
        print(_res)
        res = _res.split('。')
        for _ in res:
            if _.strip():
                await self.voice.on_message_from_str(f'voice:VOICEVO:ずんだもん {_}')


    async def stop_transcribe(self):
        self.vc.record_fin()

        
    async def update_view(self):
        await self.message.edit(view=SiriView(self))



class SiriView(discord.ui.View):
    def __init__(self, msg:SiriMessage):
        super().__init__(timeout=None)
        self.msg = msg
        if msg.vc.is_recording:
            self.add_item(SiriStopButton(msg))
        else:
            self.add_item(SiriStartButton(msg))
    

class SiriStopButton(discord.ui.Button):
    def __init__(self, msg:SiriMessage):
        self.msg = msg
        super().__init__(style=discord.ButtonStyle.red, label='Stop Record')

    async def callback(self, interaction: Interaction):
        self.msg.vc.client.loop.create_task(interaction.response.defer())
        await self.msg.stop_transcribe()


class SiriStartButton(discord.ui.Button):
    def __init__(self, msg:SiriMessage):
        self.msg = msg
        super().__init__(style=discord.ButtonStyle.green, label='Start Record')

    async def callback(self, interaction: Interaction):
        self.msg.vc.client.loop.create_task(interaction.response.defer())
        await self.msg.start_transcribe()





# async def record(ctx:commands.Context, arg=30):
    # #print(ctx.author.id)
    # vc:MyVoiceClient = ctx.voice_client
    # vc.record_start()
    # ROMA = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
    # text = []
    # user = {}
    # embed = discord.Embed(title='文字起こし')
    # msg = await ctx.send(embed=embed)
    # last_update = time.time()
    # loop = asyncio.get_event_loop()

    # async def fin():
    #     await asyncio.sleep(arg)
    #     vc.record_fin()

    # def transcribe(ssrc, adata):
    #     segments = whisper.get_segment(adata)
    #     for segment in segments:
    #         _text = segment.text
    #         if not 'ご視聴ありがとうございました' in _text:
    #             text.append({"ssrc":ssrc, "text":_text})
    #             loop.create_task(generate_embed())

    # async def generate_embed():
    #     if time.time() < last_update + 1:
    #         await asyncio.sleep(1)
    #     if time.time() < last_update + 1:
    #         return
        
    #     res_text = ''
    #     last_ssrc = None
    #     for _text in text:
    #         if last_ssrc != _text['ssrc']:
    #             last_ssrc = _text['ssrc']
    #             if name := user.get(last_ssrc):
    #                 pass
    #             else:
    #                 name = ROMA[len(user.keys())]
    #                 user[last_ssrc] = name
                
    #             res_text += f'\n{name} : {_text["text"]}'

    #         else:
    #             res_text += f' {_text["text"]}'
        
    #     _em = embed.copy()
    #     _em.description = res_text
    #     await msg.edit(embed=_em)


    
    # loop.create_task(fin())
    # while True:
    #     _, adata = await vc.buffer.get_speaking_chunk()
    #     if _ == None:
    #         break
        
    #     await loop.run_in_executor(None, transcribe,_,adata)

    # ssrc_text = defaultdict(str)
    # for _ in text:
    #     ssrc_text[_['ssrc']] += _['text']
    
    # ssrc_text = list(ssrc_text.values())
    # ssrc_text.sort(key=lambda x:len(x))
    # ssrc_text = ssrc_text[-1]

    # res = chatgpt.ask(ssrc_text)
    # print(res)