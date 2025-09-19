# lootgames/lootgames/__main__.py
import importlib
import pkgutil
import logging
import asyncio
from pyrogram import Client
from .config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID, ALLOWED_GROUP_ID, LOG_LEVEL, LOG_FORMAT

import lootgames.modules
from lootgames.modules import chat_point  # gunakan yapping sebagai modul chat point

# ================= LOGGING ================= #
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
    """
    Load semua modul di folder modules dan register handler jika ada fungsi register().
    """
    for _, module_name, _ in pkgutil.iter_modules(lootgames.modules.__path__):
        try:
            mod = importlib.import_module(f"lootgames.modules.{module_name}")
            logger.info(f"✅ Loaded module: {module_name}")
            if hasattr(mod, "register"):
                mod.register(app)
                logger.info(f"🔌 Registered handlers for module: {module_name}")
        except Exception as e:
            logger.error(f"❌ Gagal load/register handler {module_name}: {e}")

# ================= MAIN BOT START ================= #
async def main():
    logger.info("Starting LootGames Telegram Bot...")

    # Load semua modul
    load_modules()

    # Register yapping manual agar chat point selalu jalan
    try:
        yapping.register(app)
        logger.info("🔌 Registered yapping handler manually")
    except Exception as e:
        logger.error(f"❌ Failed to register yapping: {e}")

    # Start bot
    await app.start()
    logger.info("🚀 Bot started successfully!")
    logger.info(f"📱 Monitoring group: {ALLOWED_GROUP_ID}")
    logger.info(f"👑 Owner ID: {OWNER_ID}")

    # Kirim notifikasi ke owner
    try:
        await app.send_message(OWNER_ID, "🤖 LootGames Bot sudah aktif dan siap dipakai!")
        logger.info("📢 Notifikasi start terkirim ke OWNER.")
    except Exception as e:
        logger.error(f"Gagal kirim notifikasi start: {e}")

    # ================= SUPERDEBUG ================= #
    print("[SUPERDEBUG] Bot is running. Chat points will log in terminal for messages ≥5 chars.")

    # Bot tetap jalan
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass
    asyncio.run(main())

