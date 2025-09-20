# lootgames/__main__.py
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from lootgames.modules import yapping, menu_utama
from lootgames.modules import database_group as dbgroup
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID, ALLOWED_GROUP_ID, LOG_LEVEL, LOG_FORMAT

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# ================= CONFIG ================= #
API_ID = 29580121  # isi API_ID
API_HASH = "fff375a88f6546f0da2df781ca7725df"  # isi API_HASH
BOT_TOKEN = "7660904765:AAFQuSU8ShpXAzqYqAhBojjGLf7U03ityck"  # isi BOT_TOKEN
OWNER_ID = 6395738130
ALLOWED_GROUP_ID = -1002904817520

LOG_LEVEL = logging.DEBUG   # DEBUG supaya semua log masuk
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
dbgroup.register(app)       # group database / commands

# ---------------- PRIVATE /START ---------------- #
async def private_start_handler(client, message):
    user = message.from_user
    user_id = user.id
    username = user.username or user.first_name

    # masukkan user ke database global
    try:
        dbgroup.add_user(user_id, username)
        logger.info(f"User baru ditambahkan: {user_id} ({username})")
    except Exception as e:
        logger.error(f"Gagal menambahkan user ke database: {e}")

    # reply salam + tombol menu utama
    keyboard = menu_utama.make_keyboard("main", user_id)
    await message.reply(
        f"Bot sudah aktif ✅\nSalam kenal, **{username}** 👋",
        reply_markup=keyboard
    )

# register handler /start di private chat
app.add_handler(
    MessageHandler(
        private_start_handler,
        filters=filters.private & filters.command("start")
    )
)

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

    # biar bot tetap jalan
    await asyncio.Event().wait()

# ================= RUN ================= #
if __name__ == "__main__":
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass

    asyncio.run(main())
