# lootgames/__main__.py tester 2
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
    aquarium
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
if "LOG_LEVEL" not in globals():
    LOG_LEVEL = logging.DEBUG
if "LOG_FORMAT" not in globals():
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

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
def safe_register(module, name: str):
    try:
        module.register(app)
        logger.info(f"Module {name} registered ✅")
    except AttributeError:
        logger.warning(f"Module {name} tidak memiliki fungsi register()")

safe_register(yapping, "yapping")
safe_register(menu_utama, "menu_utama")

# Dummy register untuk user_database jika tidak ada
if not hasattr(user_database, "register"):
    def dummy_register(app):
        logger.info("[INFO] user_database register() dummy dipanggil")
    user_database.register = dummy_register
user_database.register(app)

# ================= CALLBACK FISHING ================= #
async def fishing_callback_handler(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username or f"user{user_id}"

    if data.startswith("FISH_CONFIRM_"):
        jenis = data.replace("FISH_CONFIRM_", "")
        from lootgames.modules.menu_utama import TARGET_GROUP

        try:
            await callback_query.message.edit_text(f"🎣 Kamu memancing dengan umpan {jenis}!")
            await gacha_fishing.fishing_loot(
                client,
                TARGET_GROUP,
                username,
                user_id,
                umpan_type=jenis
            )
        except Exception as e:
            logger.error(f"Gagal proses fishing_loot: {e}")

app.add_handler(CallbackQueryHandler(fishing_callback_handler))

# ================= MAIN BOT ================= #
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

    logger.info("[MAIN] Bot berjalan, tekan Ctrl+C untuk berhenti.")
    
    # Jalankan bot terus-menerus
    await asyncio.Event().wait()

# ================= ENTRY POINT ================= #
if __name__ == "__main__":
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass

    asyncio.run(main())

