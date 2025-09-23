# lootgames/__main__.py
import asyncio
import logging
import os
from pyrogram import Client
from pyrogram.handlers import CallbackQueryHandler

# Import semua modules
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
yapping.register(app)
menu_utama.register(app)
user_database.register(app)
treasure_chest.register(app)
register_topup(app)
# Jika mau, aktifkan modul lain:
# aquarium.register(app)
# gacha_fishing.register(app)

# ================= CALLBACK FISHING ================= #
async def fishing_callback_handler(client, cq):
    """
    Handler untuk callback FISH_CONFIRM_ dari menu fishing.
    """
    data = cq.data
    user_id = cq.from_user.id

    if data.startswith("FISH_CONFIRM_"):
        jenis = data.replace("FISH_CONFIRM_", "")
        username = cq.from_user.username or f"user{user_id}"

        # Ambil TARGET_GROUP dari menu_utama
        from lootgames.modules.menu_utama import TARGET_GROUP

        # Panggil fungsi fishing loot
        await gacha_fishing.fishing_loot(
            client,
            TARGET_GROUP,
            username,
            user_id,
            umpan_type=jenis
        )

        # Edit pesan callback untuk memberi feedback ke user
        await cq.message.edit_text(f"🎣 Kamu memancing dengan umpan {jenis}!")

# Daftarkan handler callback query untuk fishing
app.add_handler(CallbackQueryHandler(fishing_callback_handler), group=1)

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
    # Apply nest_asyncio jika dijalankan di Jupyter / environment yang butuh
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass

    asyncio.run(main())
