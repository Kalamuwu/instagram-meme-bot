#!/usr/bin/env python3

import src.config as config

from src.bot_standalone import Bot as SBot
from src.bot_webcontrol import Bot as WBot

bot = WBot() if config.USE_WEBSERVER else SBot()
bot.login()

bot.main_loop()
