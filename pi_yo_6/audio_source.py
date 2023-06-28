import asyncio
from discord import FFmpegOpusAudio, FFmpegPCMAudio

from .voice_client import _StreamAudioData


class StreamAudioData(_StreamAudioData):

    def __init__(self,url):
        super().__init__()
        self.url = url
        self.loop = asyncio.get_event_loop()



    def Url_Only(self):
        self.st_url = self.url
        self.local = True
        return self
