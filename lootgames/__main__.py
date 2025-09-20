import asyncio
import logging
from pyrogram import Client
from lootgames.modules import yapping, menu_utama
from lootgames.modules import database_group as dbgroup

# ================= CONFIG ================= #
API_ID = 29580121      # isi API_ID
API_HASH = "fff375a88f6546f0da2df781ca7725df"  # isi API_HASH
BOT_TOKEN = "7660904765:AAFQuSU8ShpXAzqYqAhBojjGLf7U03ityck" # isi BOT_TOKEN
OWNER_ID = 6395738130
ALLOWED_GROUP_ID = -1002904817520
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# ================= CLIENT ================= #
app = Client(
    "lootgames",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= REGISTER MODULES ================= #
yapping.register(app)       # chat point system
menu_utama.register(app)    # menu interaktif
dbgroup.register(app)       # start handler aktif

# ================= MAIN ================= #
async def main():
    await app.start()
    logger.info("🚀 Bot started!")
    logger.info(f"📱 Monitoring group: {ALLOWED_GROUP_ID}")
    logger.info(f"👑 Owner ID: {OWNER_ID}")

    try:
        await app.send_message(OWNER_ID, "🤖 LootGames Bot sudah aktif dan siap dipakai!")
        logger.info("📢 Notifikasi start terkirim ke OWNER.")
    except Exception as e:
        logger.error(f"Gagal kirim notifikasi start: {e}")

    # bot tetap jalan
    await asyncio.Event().wait()

# ================= RUN ================= #
if __name__ == "__main__":
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass

    asyncio.run(main())

