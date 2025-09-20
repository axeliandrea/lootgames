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
yapping.register(app)
menu_utama.register(app)
dbgroup.register(app)

# ================= PRIVATE /START ================= #
async def private_start_handler(client, message):
    if message.chat.type != "private":
        return

    user = message.from_user
    user_id = user.id
    first_name = user.first_name
    last_name = user.last_name or ""
    username = user.username or first_name

    try:
        dbgroup.add_or_update_user(user_id, first_name, last_name, username)
        logger.info(f"User terupdate/baru ditambahkan: {user_id} ({username})")
    except Exception as e:
        logger.error(f"Gagal menambahkan user ke database: {e}")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Main", callback_data="menu_main")],
        [InlineKeyboardButton("📊 Poin Saya", callback_data="menu_point")],
        [InlineKeyboardButton("👥 Leaderboard", callback_data="menu_leaderboard")],
        [InlineKeyboardButton("ℹ️ Info", callback_data="menu_info")],
        [InlineKeyboardButton("✅ JOIN", callback_data="join")]
    ])

    await message.reply_text(
        f"👋 Hai **{username}**!\n\n"
        "Selamat datang di **LootGames Bot** 🎮\n\n"
        "Silakan pilih menu di bawah ini:",
        reply_markup=keyboard
    )

app.add_handler(MessageHandler(private_start_handler, filters.private & filters.command("start")))

# ================= PRIVATE .JOIN ================= #
async def private_join_handler(client, message):
    if message.chat.type != "private":
        return

    user = message.from_user
    user_id = user.id
    first_name = user.first_name
    last_name = user.last_name or ""
    username = user.username or first_name

    try:
        dbgroup.add_or_update_user(user_id, first_name, last_name, username)
        await message.reply_text("🎉 Selamat, kamu adalah **player Loot** sekarang ✅")
        logger.info(f"Player JOIN lewat .join: {user_id} | {username}")

        # notifikasi ke OWNER
        await client.send_message(
            OWNER_ID,
            f"📥 Player JOIN (.join):\nID: {user_id}\nNama: {first_name} {last_name}\nUsername: @{username}"
        )
    except Exception as e:
        await message.reply_text("❌ Gagal JOIN, coba lagi nanti.")
        logger.error(f"Gagal .join user: {e}")

app.add_handler(MessageHandler(private_join_handler, filters.private & filters.command("join", prefixes=".")))

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
        logger.info(f"User JOIN (button): {user_id} | {username}")

        await client.send_message(
            OWNER_ID,
            f"📥 User JOIN (button):\nID: {user_id}\nNama: {first_name} {last_name}\nUsername: @{username}"
        )
    except Exception as e:
        await callback_query.answer("❌ Gagal JOIN, coba lagi nanti.")
        logger.error(f"Gagal update user JOIN: {e}")

app.add_handler(CallbackQueryHandler(join_handler, filters.create(lambda _, __, q: q.data == "join")))

# ================= CALLBACK MENU ================= #
async def menu_handler(client, callback_query):
    data = callback_query.data
    user = callback_query.from_user

    if data == "menu_main":
        await callback_query.message.edit_text(
            "🎮 **Menu Main**\n\n"
            "Fitur permainan akan ditampilkan di sini.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]])
        )

    elif data == "menu_point":
        poin = menu_utama.get_user_point(user.id)
        await callback_query.message.edit_text(
            f"📊 **Poin Kamu:** {poin}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]])
        )

    elif data == "menu_leaderboard":
        board = menu_utama.get_leaderboard()
        await callback_query.message.edit_text(
            f"👥 **Leaderboard:**\n\n{board}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]])
        )

    elif data == "menu_info":
        await callback_query.message.edit_text(
            "ℹ️ **Info Bot LootGames**\n\n"
            "Bot ini dibuat untuk game dan sistem poin seru di grup.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]])
        )

    elif data == "back_main":
        await private_start_handler(client, callback_query.message)

app.add_handler(CallbackQueryHandler(menu_handler))

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

    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass

    asyncio.run(main())
