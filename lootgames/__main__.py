# lootgames/__main__.py

import importlib
import pkgutil
import logging
import asyncio

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


async def send_start_message():
    try:
        await app.send_message(
            Config.TARGET_GROUP or Config.OWNER_ID,
            "✅ LootGames Bot sudah aktif dan siap digunakan 🚀"
        )
        logging.info("📢 Notifikasi bot aktif terkirim.")
    except Exception as e:
        logging.error(f"Gagal kirim notifikasi start: {e}")


if __name__ == "__main__":
    load_modules()
    logging.info("🚀 LootGames Bot Starting...")

    async def main():
        await app.start()
        await send_start_message()
        logging.info("🤖 Bot sedang berjalan. Tekan CTRL+C untuk stop.")
        await app.idle()  # biar tetap jalan

    asyncio.run(main())
