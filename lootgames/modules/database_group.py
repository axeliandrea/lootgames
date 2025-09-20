import json
import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

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

def add_user(user_id: int, username: str):
    data = load_db()
    uid_str = str(user_id)
    if uid_str not in data:
        data[uid_str] = {"username": username or f"user{user_id}"}
        save_db(data)
        logger.info(f"[DB] User {user_id} ({username}) ditambahkan ke database")

def get_user_id_by_username(username: str):
    username = username.lower().replace("@", "")
    data = load_db()
    for uid, info in data.items():
        if info.get("username","").lower() == username:
            return int(uid)
    return None

# ---------------- KEYBOARD ---------------- #
def main_menu_keyboard():
    from lootgames.modules import menu_utama  # pastikan import menu_utama
    return menu_utama.make_keyboard("main")

# ---------------- HANDLER START ---------------- #
async def start_handler(client: Client, message: Message):
    user = message.from_user
    add_user(user.id, user.username)
    keyboard = main_menu_keyboard()
    await message.reply(
        f"Hi {user.first_name}, salam kenal! Bot sudah aktif ✅\n\n📋 Gunakan menu di bawah untuk navigasi.",
        reply_markup=keyboard
    )
    logger.debug(f"[START] User {user.id} membuka bot, menu utama ditampilkan")

# ---------------- REGISTER ---------------- #
def register(app: Client):
    """
    Register handler untuk private chat bot
    """
    app.add_handler(
        app.add_handler(
            handlers.MessageHandler(start_handler, filters.private & filters.command("start"))
        )
    )
