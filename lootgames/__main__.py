import importlib
import pkgutil
import logging
import asyncio
from pyrogram import Client
from lootgames.config import Config
import lootgames.modules  # supaya bisa di-scan __path__

# ---------------- LOGGING ---------------- #
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ---------------- CLIENT ---------------- #
app = Client(
    "lootgames",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN if Config.BOT_TOKEN else None,
)


# ---------------- MODULE LOADER ---------------- #
def load_modules():
    """Auto load semua modul dari lootgames/modules"""
    for _, module_name, _ in pkgutil.iter_modules(lootgames.modules.__path__):
        importlib.import_module(f"lootgames.modules.{module_name}")
        logging.info(f"✅ Loaded module: {module_name}")


# ---------------- MAIN ---------------- #
async def main():
    load_modules()
    await app.start()
    logging.info("🚀 LootGames Bot Started...")

    # Kirim notifikasi ke OWNER
    try:
        await app.send_message(
            Config.OWNER_ID,  # pastikan ini INT user ID
            "🤖 LootGames Bot sudah aktif dan siap dipakai!"
        )
        logging.info("📢 Notifikasi start terkirim ke OWNER.")
    except Exception as e:
        logging.error(f"Gagal kirim notifikasi start: {e}")

    # Biarkan bot tetap jalan
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
