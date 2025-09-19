# lootgames/__main__.py

import importlib
import pkgutil
import logging

from pyrogram import Client
from lootgames.config import Config

# Logging biar keliatan error/debug
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Session name (kalau ubot, pakai session string, kalau bot pakai BOT_TOKEN)
app = Client(
    "lootgames",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN if Config.BOT_TOKEN else None,
)

# Auto load semua module di folder modules
def load_modules():
    for _, module_name, _ in pkgutil.iter_modules(["lootgames/modules"]):
        importlib.import_module(f"lootgames.modules.{module_name}")
        logging.info(f"✅ Loaded module: {module_name}")

if __name__ == "__main__":
    load_modules()
    logging.info("🚀 LootGames Bot Started...")
    app.run()
