import json
import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from lootgames.modules import menu_utama
from lootgames.config import OWNER_ID

logger = logging.getLogger(__name__)

DB_FILE = "lootgames/modules/database_group.json"

# pastikan file database ada
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({}, f, indent=2)

# ---------------- DATABASE ---------------- #
def load_db() -> dict:
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data: dict):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def add_or_update_user(user_id: int, first_name: str, last_name: str, username: str):
    data = load_db()
    uid_str = str(user_id)
    username = username or f"user{user_id}"
    first_name = first_name or ""
    last_name = last_name or ""

    if uid_str in data:
        updated = False
        if data[uid_str].get("username") != username:
            data[uid_str]["username"] = username
            updated = True
        if data[uid_str].get("first_name") != first_name:
            data[uid_str]["first_name"] = first_name
            updated = True
        if data[uid_str].get("last_name") != last_name:
            data[uid_str]["last_name"] = last_name
            updated = True
        if updated:
            logger.info(f"[DB] User {user_id} diperbarui: {username}, {first_name} {last_name}")
    else:
        data[uid_str] = {
            "username": username,
            "first_name": first_name,
            "last_name": last_name
        }
        logger.info(f"[DB] User baru ditambahkan: {user_id} ({username})")

    save_db(data)

def get_user_id_by_username(username: str):
    username = username.lower().replace("@", "")
    data = load_db()
    for uid, info in data.items():
        if info.get("username", "").lower() == username:
            return int(uid)
    return None

# ---------------- KEYBOARD ---------------- #
def main_menu_keyboard(user_id: int = None):
    keyboard = menu_utama.make_keyboard("main", user_id)
    # tambahkan tombol JOIN di bawah
    keyboard.inline_keyboard.append([InlineKeyboardButton("JOIN", callback_data="join")])
    return keyboard

# ---------------- HANDLER START ---------------- #
async def start_handler(client: Client, message: Message):
    user = message.from_user
    add_or_update_user(user.id, user.first_name, user.last_name or "", user.username or "")
    keyboard = main_menu_keyboard(user.id)
    await message.reply(
        f"Hi {user.first_name}, salam kenal! Bot sudah aktif ✅\n\n📋 Gunakan menu di bawah untuk navigasi.",
        reply_markup=keyboard
    )
    logger.debug(f"[START] User {user.id} membuka bot, menu utama ditampilkan")

# ---------------- CALLBACK JOIN ---------------- #
async def join_callback(client: Client, callback_query):
    user = callback_query.from_user
    add_or_update_user(user.id, user.first_name, user.last_name or "", user.username or "")
    await callback_query.answer("✅ Kamu berhasil JOIN dan data diperbarui!")
    logger.info(f"[JOIN] User {user.id} ({user.username}) JOIN")
    # notif ke owner
    try:
        await client.send_message(
            OWNER_ID,
            f"📥 User JOIN:\nID: {user.id}\nNama: {user.first_name} {user.last_name or ''}\nUsername: @{user.username or ''}"
        )
    except Exception as e:
        logger.error(f"Gagal kirim notif JOIN ke OWNER: {e}")

# ---------------- REGISTER ---------------- #
def register(app: Client):
    """
    Register handler untuk private chat bot
    """
    app.add_handler(
        MessageHandler(start_handler, filters.private & filters.command("start"))
    )
    app.add_handler(
        CallbackQueryHandler(join_callback, filters=filters.create(lambda _, __, query: query.data == "join"))
    )
