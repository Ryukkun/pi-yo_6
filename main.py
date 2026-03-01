import os
import asyncio
import shutil
import discord
from discord.ext import commands

from pi_yo_6.synthetic_voice import SyntheticEngines


IS_MAIN_PROCESS = __name__ == "__main__"

async def main():
    try: from pi_yo_6.config import Config
    except Exception:
        shutil.copy("./pi_yo_6/resources/config_template.py", "./pi_yo_6/config.py")
        raise Exception('Config ファイルを生成しました')
    
    from pi_yo_6.main import MyCog
    from pi_yo_6.utils import set_logger


    try:shutil.rmtree(Config.output)
    except Exception:pass
    os.makedirs(Config.user_dic, exist_ok=True)
    os.makedirs(Config.guild_config, exist_ok=True)
    os.makedirs(Config.user_config, exist_ok=True)
    os.makedirs(Config.output, exist_ok=True)
    os.makedirs(Config.OpenJtalk.hts_path, exist_ok=True)
    os.makedirs(Config.OpenJtalk.dictionary_path, exist_ok=True)
    with open(Config.admin_dic,'a'):pass


    ####  起動準備 And 初期設定
    intents = discord.Intents.default()
    intents.message_content = True
    intents.reactions = True
    intents.voice_states = True
    bot = commands.Bot(command_prefix=Config.prefix,intents=intents)
    set_logger()

    engines = SyntheticEngines()
    await engines.init_all()

    async with bot:
        await bot.add_cog(MyCog(bot, engines))
        await bot.start(Config.token)

if IS_MAIN_PROCESS:
    asyncio.run(main())