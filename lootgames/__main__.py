# lootgames/__main__.py

import importlib
import pkgutil
import logging
import asyncio
from pyrogram import Client
from lootgames.config import Config

# Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

app = Client(
    "lootgames",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN if Config.BOT_TOKEN else None,
)


def load_modules():
    for _, module_name, _ in pkgutil.iter_modules(["lootgames/modules"]):
        importlib.import_module(f"lootgames.modules.{module_name}")
        logging.info(f"✅ Loaded module: {module_name}")


@app.on_connected()
async def notify_start(client: Client):
    logging.info("🚀 LootGames Bot Starting...")
    try:
        await client.send_message(
            Config.OWNER_ID,  # isi dengan user ID kamu (angka), bukan username
            "🤖 LootGames Bot sudah aktif dan siap dipakai!"
        )
        logging.info("📢 Notifikasi start terkirim ke OWNER.")
    except Exception as e:
        logging.error(f"Gagal kirim notifikasi start: {e}")


if __name__ == "__main__":
    load_modules()
    app.run()
