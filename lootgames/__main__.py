# lootgames/lootgames/__main__.py
import importlib
import pkgutil
import logging
import asyncio
from pyrogram import Client
from .config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID, ALLOWED_GROUP_ID, LOG_LEVEL, LOG_FORMAT

import lootgames.modules
from lootgames.modules import yapping  # pastikan yapping diimport

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# ================= CREATE APP ================= #
app = Client(
    "lootgames",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN if BOT_TOKEN else None,
)

# ================= LOAD ALL MODULES ================= #
def load_modules():
    for _, module_name, _ in pkgutil.iter_modules(lootgames.modules.__path__):
        mod = importlib.import_module(f"lootgames.modules.{module_name}")
        logger.info(f"✅ Loaded module: {module_name}")
        # jika modul punya fungsi register, panggil register(app)
        if hasattr(mod, "register"):
            try:
                mod.register(app)
                logger.info(f"🔌 Registered handlers for module: {module_name}")
            except Exception as e:
                logger.error(f"❌ Gagal register handler {module_name}: {e}")

# ================= MAIN BOT START ================= #
async def main():
    logger.info("Starting LootGames Telegram Bot...")

    # load modul dulu
    load_modules()

    # pastikan yapping juga register manual (jika belum otomatis)
    try:
        yapping.register(app)
        logger.info("🔌 Registered yapping handler manually")
    except Exception as e:
        logger.error(f"❌ Failed to register yapping: {e}")

    # start bot
    await app.start()
    logger.info("🚀 Bot started successfully!")
    logger.info(f"📱 Monitoring group: {ALLOWED_GROUP_ID}")
    logger.info(f"👑 Owner ID: {OWNER_ID}")
    logger.info("🎮 Use /menufish command to show menu")

    # notif ke owner
    try:
        await app.send_message(OWNER_ID, "🤖 LootGames Bot sudah aktif dan siap dipakai!")
        logger.info("📢 Notifikasi start terkirim ke OWNER.")
    except Exception as e:
        logger.error(f"Gagal kirim notifikasi start: {e}")

    await asyncio.Event().wait()  # biar bot tetap jalan

if __name__ == "__main__":
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass
    asyncio.run(main())
