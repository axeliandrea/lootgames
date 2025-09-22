lootgames/__main__.py
import asyncio
import logging
import os
from pyrogram import Client
from pyrogram.handlers import CallbackQueryHandler
from lootgames.modules import (
    yapping,
    menu_utama,
    user_database,
    autorespon,
    gacha_fishing
)
from lootgames.config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID, ALLOWED_GROUP_ID, LOG_LEVEL, LOG_FORMAT

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
autorespon.setup(app)

# ================= CALLBACK FISHING ================= #
async def fishing_callback_handler(client, callback_query):
    """
    Handler untuk callback FISH_CONFIRM_ dari menu fishing.
    """
    data = callback_query.data
    user_id = callback_query.from_user.id

    if data.startswith("FISH_CONFIRM_"):
        jenis = data.replace("FISH_CONFIRM_", "")
        username = callback_query.from_user.username or f"user{user_id}"

        # Ambil TARGET_GROUP dari menu_utama
        from lootgames.modules.menu_utama import TARGET_GROUP

        # Panggil fungsi fishing loot
        try:
            await gacha_fishing.fishing_loot(
                client,
                TARGET_GROUP,
                username,
                user_id,
                umpan_type=jenis
            )
            # Edit pesan callback untuk memberi feedback ke user
            await callback_query.message.edit_text(f"🎣 Kamu memancing dengan umpan {jenis}!")
        except Exception as e:
            logger.error(f"Error saat memancing: {e}")
            await callback_query.message.edit_text("❌ Terjadi kesalahan saat memancing. Coba lagi nanti.")

# Daftarkan handler callback query
app.add_handler(CallbackQueryHandler(fishing_callback_handler))

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

if __name__ == "__main__":
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass

    asyncio.run(main())

