# lootgames/__main__.py
import asyncio
import logging
import os
from pyrogram import Client

# ================= IMPORT MODULES ================= #
from lootgames.modules import (
    yapping,
    menu_utama,
    user_database,
    gacha_fishing,
    aquarium,
    treasure_chest
)

# Import register_topup langsung dari umpan
from lootgames.modules.umpan import register_topup

from lootgames.config import (
    API_ID,
    API_HASH,
    BOT_TOKEN,
    OWNER_ID,
    ALLOWED_GROUP_ID,
    LOG_LEVEL,
    LOG_FORMAT,
)

# ================= LOGGING ================= #
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
logger.info("Mendaftarkan module...")
yapping.register(app)
menu_utama.register(app)
user_database.register(app)
treasure_chest.register(app)
register_topup(app)
logger.info("Semua module terdaftar ✅")
# aquarium.register(app)
# gacha_fishing.register(app)

# ================= MAIN ================= #
async def main():
    # Pastikan folder storage ada
    os.makedirs("storage", exist_ok=True)

    # Start client
    await app.start()
    logger.info("🚀 LootGames Bot started!")
    logger.info(f"📱 Monitoring group: {ALLOWED_GROUP_ID}")
    logger.info(f"👑 Owner ID: {OWNER_ID}")

    # Kirim notifikasi ke owner
    try:
        await app.send_message(OWNER_ID, "🤖 LootGames Bot sudah aktif dan siap dipakai!")
        logger.info("📢 Notifikasi start terkirim ke OWNER.")
    except Exception as e:
        logger.error(f"Gagal kirim notifikasi start: {e}")

    # Bot berjalan terus
    await asyncio.Event().wait()

# ================= RUN BOT ================= #
if __name__ == "__main__":
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass

    asyncio.run(main())
