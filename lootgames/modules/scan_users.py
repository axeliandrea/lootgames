# lootgames/modules/scan_users.py
import logging
import asyncio
from pyrogram import Client
from lootgames.config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID
from lootgames.modules import database_group as db

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ================= CLIENT ================= #
app = Client(
    "lootgames_scan",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= FUNCTION SCAN ================= #
async def scan_users():
    """
    Scan semua user yang pernah chat /start di bot
    dan pastikan ada di database global.
    """
    await app.start()
    logger.info("🔍 Mulai scan users di bot...")

    try:
        async for dialog in app.get_dialogs():
            if dialog.chat.type == "private":
                user = dialog.chat
                user_id = user.id
                username = user.username or user.first_name

                # tambahkan user ke database jika belum ada
                db.add_user(user_id, username)
                logger.info(f"✅ User terdaftar: {user_id} ({username})")
    except Exception as e:
        logger.error(f"❌ Gagal scan user: {e}")

    logger.info("🎯 Scan users selesai!")
    await app.stop()

# ================= RUN ================= #
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(scan_users())
