# lootgames/__main__.py
import asyncio
import logging
import os
from pyrogram import Client
from pyrogram.handlers import CallbackQueryHandler

# ================= IMPORT MODULES ================= #
from lootgames.modules import (
    yapping,
    menu_utama,
    user_database,
    gacha_fishing,
    aquarium,
    treasure_chest
)

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
yapping.register(app)
menu_utama.register(app)
user_database.register(app)
treasure_chest.register(app)  # <<< REGISTER TREASURE CHEST MODULE

# ================= CALLBACK FISHING ================= #
async def fishing_callback_handler(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    if data.startswith("FISH_CONFIRM_"):
        jenis = data.replace("FISH_CONFIRM_", "")
        username = callback_query.from_user.username or f"user{user_id}"

        from lootgames.modules.menu_utama import TARGET_GROUP
        await callback_query.message.edit_text(f"🎣 Kamu memancing dengan umpan {jenis}!")

        try:
            await gacha_fishing.fishing_loot(client, TARGET_GROUP, username, user_id, umpan_type=jenis)
        except Exception as e:
            logger.error(f"Gagal proses fishing_loot: {e}")

app.add_handler(CallbackQueryHandler(fishing_callback_handler))

# ================= MAIN BOT ================= #
async def main():
    os.makedirs("storage", exist_ok=True)
    await app.start()
    logger.info("🚀 LootGames Bot started!")
    logger.info(f"📱 Monitoring group: {ALLOWED_GROUP_ID}")
    logger.info(f"👑 Owner ID: {OWNER_ID}")

    try:
        await app.send_message(OWNER_ID, "🤖 LootGames Bot sudah aktif dan siap dipakai!")
        logger.info("📢 Notifikasi start terkirim ke OWNER.")
    except Exception as e:
        logger.error(f"Gagal kirim notifikasi start: {e}")

    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass

    asyncio.run(main())
