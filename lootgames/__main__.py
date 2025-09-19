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

# Init client
app = Client(
    "lootgames",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN if Config.BOT_TOKEN else None,
)

# Auto load modules
def load_modules():
    for _, module_name, _ in pkgutil.iter_modules(["lootgames/modules"]):
        importlib.import_module(f"lootgames.modules.{module_name}")
        logging.info(f"✅ Loaded module: {module_name}")

async def main():
    # Start bot
    await app.start()
    logging.info("🚀 LootGames Bot Starting...")

    # Notifikasi ke owner
    try:
        await app.send_message(
            Config.OWNER_ID,
            "🤖 LootGames Bot sudah aktif dan siap dipakai!"
        )
        logging.info("📢 Notifikasi start terkirim ke OWNER.")
    except Exception as e:
        logging.error(f"Gagal kirim notifikasi start: {e}")

    # Biar bot tetap jalan
    await app.idle()

if __name__ == "__main__":
    load_modules()
    asyncio.run(main())
