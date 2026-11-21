import argparse
import asyncio
import logging
import os

import discord
from discord.ext import commands

# configを読み込む前にプロジェクトのモジュールを読み込まないこと
_log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="読み上げBotの起動スクリプト")
    parser.add_argument("--debug", action="store_true", help="デバッグモードを有効にする")
    return parser.parse_args()


async def main(debug: bool = False) -> None:
    from pi_yo_6.audio.discord_patch import apply_discord_patch
    from pi_yo_6.cog import TTSCog
    from pi_yo_6.config import app_config
    from pi_yo_6.logging import setup_logger
    from pi_yo_6.tts import TTSManager

    setup_logger(logging.DEBUG if debug else logging.INFO)
    apply_discord_patch()

    os.makedirs(app_config.guild_config, exist_ok=True)
    os.makedirs(app_config.user_config, exist_ok=True)
    os.makedirs(app_config.OpenJtalk.hts_path, exist_ok=True)
    os.makedirs(app_config.OpenJtalk.dictionary_path, exist_ok=True)

    ####  起動準備 And 初期設定
    intents = discord.Intents.default()
    intents.message_content = True
    intents.reactions = True
    intents.voice_states = True
    bot = commands.Bot(command_prefix=app_config.prefix, intents=intents)

    tts = TTSManager()
    await tts.init_all()

    try:
        async with bot:
            await bot.add_cog(TTSCog(bot, tts))
            await bot.start(app_config.token)
    finally:
        await tts.close()


if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(main(debug=args.debug), debug=args.debug)
    except KeyboardInterrupt:
        _log.info("Bot has stopped (Ctrl+C).")
