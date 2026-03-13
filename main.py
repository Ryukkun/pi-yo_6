import argparse
import logging
import os
import asyncio
import shutil
import discord
from discord.ext import commands
from discord.utils import setup_logging

# configを読み込む前にプロジェクトのモジュールを読み込まないこと


IS_MAIN_PROCESS = __name__ == "__main__"



def parse_args():
    parser = argparse.ArgumentParser(description="読み上げBotの起動スクリプト")
    # 引数の設定
    parser.add_argument("--debug", action="store_true", help="デバッグモードを有効にする")
    return parser.parse_args()

args = parse_args()



async def main():
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    from pi_yo_6.load_config import Config
    from pi_yo_6.main import MyCog
    #from pi_yo_6.utils import set_logger
    from pi_yo_6.synthetic_voice import SyntheticEngines


    try:shutil.rmtree(Config.output)
    except Exception:pass
    os.makedirs(Config.guild_config, exist_ok=True)
    os.makedirs(Config.user_config, exist_ok=True)
    os.makedirs(Config.output, exist_ok=True)
    os.makedirs(Config.OpenJtalk.hts_path, exist_ok=True)
    os.makedirs(Config.OpenJtalk.dictionary_path, exist_ok=True)


    ####  起動準備 And 初期設定
    intents = discord.Intents.default()
    intents.message_content = True
    intents.reactions = True
    intents.voice_states = True
    bot = commands.Bot(command_prefix=Config.prefix,intents=intents)
    #set_logger()
    setup_logging()
    

    engines = SyntheticEngines()
    await engines.init_all()

    async with bot:
        await bot.add_cog(MyCog(bot, engines))
        await bot.start(Config.token)

if IS_MAIN_PROCESS:
    asyncio.run(main(), debug=args.debug)