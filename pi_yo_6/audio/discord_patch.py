from typing import IO

import discord


def _patch_pipe_reader(self: discord.FFmpegAudio, dest: IO[bytes]) -> None:
    while self._process:
        if self._stderr is None:
            return
        try:
            data: bytes = self._stderr.readline()
        except Exception:
            discord.player._log.debug("Read error for %s, this is probably not a problem", self, exc_info=True)
            return
        if not data:
            return
        try:
            dest.write(data)
        except Exception:
            discord.player._log.exception("Write error for %s", self)
            try:
                self._stderr.close()
            except Exception:
                pass
            return


def apply_discord_patch() -> None:
    """discord.py の FFmpegAudio._pipe_reader に終了・読込エラー耐性パッチを適用する"""
    discord.FFmpegOpusAudio._pipe_reader = _patch_pipe_reader  # type: ignore[method-assign]
    discord.FFmpegPCMAudio._pipe_reader = _patch_pipe_reader  # type: ignore[method-assign]
