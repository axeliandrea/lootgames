# lootgames/__main__.py
import importlib, pkgutil, logging, asyncio
from pyrogram import Client
from lootgames.config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID, ALLOWED_GROUP_ID, LOG_LEVEL, LOG_FORMAT
import lootgames.modules

# ---------------- Logging ---------------- #
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# ---------------- Init Client ---------------- #
app = Client(
    "lootgames",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN if BOT_TOKEN else None,
)

# ---------------- Load Modules ---------------- #
def load_modules():
    for _, module_name, _ in pkgutil.iter_modules(lootgames.modules.__path__):
        mod = importlib.import_module(f"lootgames.modules.{module_name}")
        logger.info(f"✅ Loaded module: {module_name}")
        if hasattr(mod, "register_commands"):
            try:
                mod.register_commands(app)
                logger.info(f"🔌 Registered handlers for module: {module_name}")
            except Exception as e:
                logger.error(f"❌ Gagal register handler {module_name}: {e}")

# ---------------- Main Async ---------------- #
async def main():
    logger.info("Starting LootGames Telegram Bot...")
    load_modules()
    await app.start()
    logger.info("🚀 Bot started successfully!")
    logger.info(f"📱 Monitoring group: {ALLOWED_GROUP_ID}")
    logger.info(f"👑 Owner ID: {OWNER_ID}")

    try:
        await app.send_message(OWNER_ID, "🤖 LootGames Bot sudah aktif dan siap dipakai!")
        logger.info("📢 Notifikasi start terkirim ke OWNER.")
    except Exception as e:
        logger.error(f"Gagal kirim notifikasi start: {e}")

    # keep running
    await asyncio.Event().wait()

# ---------------- Run ---------------- #
if __name__ == "__main__":
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass
    asyncio.run(main())
