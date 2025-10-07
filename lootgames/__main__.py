# lootgames/__main__.py
import asyncio
import logging
import os
from pyrogram import Client
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import CallbackQuery

# ================= IMPORT MODULES ================= #
from lootgames.modules import (
    yapping,
    menu_utama,
    user_database,
    gacha_fishing,
    aquarium,
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
    LOG_LEVEL = logging.INFO
if "LOG_FORMAT" not in globals():
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Supaya log internal Pyrogram tidak terlalu ramai
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pyrogram.session").setLevel(logging.WARNING)

# ================= CLIENT ================= #
app = Client(
    "lootgames",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= STARTUP TASK ================= #
async def startup_tasks():
    try:
        if hasattr(gacha_fishing, "fishing_worker"):
            logger.info("🔹 Menjalankan startup worker fishing...")
            asyncio.create_task(gacha_fishing.fishing_worker(app))
        else:
            logger.warning("Module gacha_fishing tidak memiliki fishing_worker(), melewati startup worker.")
    except Exception as e:
        logger.exception(f"Gagal start worker fishing: {e}")

# ================= REGISTER MODULES ================= #
def safe_register(module, name: str):
    if hasattr(module, "register"):
        try:
            module.register(app)
            logger.info(f"Module {name} registered ✅")
        except Exception as e:
            logger.exception(f"Gagal register module {name}: {e}")
    else:
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
async def fishing_callback_handler(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username or f"user{user_id}"

    if data.startswith("FISH_CONFIRM_"):
        jenis = data.replace("FISH_CONFIRM_", "")
        from lootgames.modules.menu_utama import TARGET_GROUP

        try:
            await callback_query.message.edit_text(f"🎣 Kamu memancing dengan umpan {jenis}!")
            if hasattr(gacha_fishing, "fishing_loot"):
                await gacha_fishing.fishing_loot(
                    client,
                    TARGET_GROUP,
                    username,
                    user_id,
                    umpan_type=jenis
                )
            else:
                logger.warning("Module gacha_fishing tidak memiliki fungsi fishing_loot()")
        except Exception as e:
            logger.exception(f"Gagal proses fishing_loot: {e}")

app.add_handler(CallbackQueryHandler(fishing_callback_handler))

# ================= MAIN BOT ================= #
async def main():
    # Pastikan folder storage ada
    storage_dir = "storage"
    os.makedirs(storage_dir, exist_ok=True)
    logger.info(f"✅ Folder storage siap di {storage_dir}")

    # Start client
    await app.start()
    logger.info("🚀 TRIAL Bot started!")
    logger.info(f"📱 Monitoring group: {ALLOWED_GROUP_ID}")
    logger.info(f"👑 Owner ID: {OWNER_ID}")

    # Jalankan startup worker
    await startup_tasks()

    # Kirim notifikasi ke owner
    if isinstance(OWNER_ID, int):
        try:
            await app.send_message(OWNER_ID, "🤖 TRIAL Bot sudah aktif dan siap dipakai!")
            logger.info("📢 Notifikasi start terkirim ke OWNER.")
        except Exception as e:
            logger.exception(f"Gagal kirim notifikasi start: {e}")

    logger.info("[MAIN] Bot berjalan, tekan Ctrl+C untuk berhenti.")

    # Jalankan bot terus-menerus
    await asyncio.Event().wait()

# ================= ENTRY POINT ================= #
if __name__ == "__main__":
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        logger.warning("nest_asyncio tidak ditemukan, jalankan bot biasa.")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("❌ Bot dihentikan oleh user (Ctrl+C)")
    except Exception as e:
        logger.exception(f"Bot berhenti karena error: {e}")
