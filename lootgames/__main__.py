# lootgames/__main__.py
import asyncio
import logging
from pyrogram import Client, filters
from lootgames.modules import yapping, menu_utama, user_database
from lootgames.config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID, ALLOWED_GROUP_ID, LOG_LEVEL, LOG_FORMAT

# ================= LOGGING ================= #
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# ================= CLIENT ================= #
app = Client(
    "lootgames",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir="./"
)

# ================= REGISTER MODULES ================= #
logger.info("📌 Registering modules...")
yapping.register(app)
menu_utama.register(app)
user_database.register(app)
logger.info("✅ Modules registered successfully.")

# ================= DEBUG HANDLER SEMUA CHAT ================= #
@app.on_message(filters.group | filters.private)
async def debug_all_messages(client, message):
    user = message.from_user
    uname = user.username if user else "Unknown"
    logger.debug(f"📩 [{message.chat.id}] @{uname} ({message.from_user.id if user else 'N/A'}): {message.text}")

# ================= MAIN ================= #
async def main():
    await app.start()
    logger.info("🚀 LootGames Bot started!")
    logger.info(f"📱 Monitoring group: {ALLOWED_GROUP_ID}")
    logger.info(f"👑 Owner ID: {OWNER_ID}")

    # Kirim notifikasi start ke OWNER
    try:
        await app.send_message(OWNER_ID, "🤖 LootGames Bot sudah aktif dan siap dipakai!")
        logger.info("📢 Notifikasi start terkirim ke OWNER.")
    except Exception as e:
        logger.error(f"❌ Gagal kirim notifikasi start: {e}")

    # Bot akan terus berjalan
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        import nest_asyncio
        nest_asyncio.apply()
        logger.info("🔄 Applied nest_asyncio")
    except ImportError:
        logger.warning("⚠️ nest_asyncio tidak tersedia, skip")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped manually.")
    except Exception as e:
        logger.exception(f"❌ Unexpected error: {e}")
