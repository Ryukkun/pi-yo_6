# Compatibility shim (will be removed once all modules migrate to pi_yo_6.audio)
from typing import TYPE_CHECKING

from discord import Guild

from pi_yo_6.audio.mixer import AudioMixer, AudioTrack, FFmpegReader, StreamAudioData

if TYPE_CHECKING:
    from pi_yo_6.main import DataInfo


class MultiAudioVoiceClient(AudioMixer):
    def __init__(self, guild: Guild, info: "DataInfo") -> None:
        super().__init__(vc=info.vc, loop=info.cog.bot.loop, guild_name=guild.name)


__all__ = [
    "AudioTrack",
    "FFmpegReader",
    "MultiAudioVoiceClient",
    "StreamAudioData",
]
