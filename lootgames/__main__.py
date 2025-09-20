# lootgames/__main__.py
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from lootgames.modules import yapping, menu_utama
from lootgames.modules import database_group as dbgroup
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
yapping.register(app)       # chat point system
menu_utama.register(app)    # menu interaktif
dbgroup.register(app)       # group database / commands

# ================= PRIVATE /START ================= #
async def private_start_handler(client, message):
    user = message.from_user
    user_id = user.id
    first_name = user.first_name
    last_name = user.last_name or ""
    username = user.username or first_name

    # masukkan atau update user di database
    try:
        dbgroup.add_or_update_user(user_id, first_name, last_name, username)
        logger.info(f"User terupdate/baru ditambahkan: {user_id} ({username})")
    except Exception as e:
        logger.error(f"Gagal menambahkan user ke database: {e}")

    # buat keyboard menu utama + tombol JOIN
    keyboard = menu_utama.make_keyboard("main", user_id)
    join_button = InlineKeyboardButton("JOIN", callback_data="join")
    keyboard.inline_keyboard.append([join_button])

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

# ================= CALLBACK JOIN ================= #
async def join_handler(client, callback_query):
    user = callback_query.from_user
    user_id = user.id
    first_name = user.first_name
    last_name = user.last_name or ""
    username = user.username or first_name

    try:
        dbgroup.add_or_update_user(user_id, first_name, last_name, username)
        await callback_query.answer("✅ Kamu berhasil JOIN dan data diperbarui!")
        logger.info(f"User JOIN: {user_id} | {username} | {first_name} {last_name}")

        # kirim notifikasi ke OWNER
        await client.send_message(
            OWNER_ID,
            f"📥 User JOIN:\nID: {user_id}\nNama: {first_name} {last_name}\nUsername: @{username}"
        )
    except Exception as e:
        await callback_query.answer("❌ Gagal JOIN, coba lagi nanti.")
        logger.error(f"Gagal update user JOIN: {e}")

# register callback handler JOIN
app.add_handler(
    CallbackQueryHandler(join_handler, filters=filters.create(lambda _, __, query: query.data == "join"))
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
