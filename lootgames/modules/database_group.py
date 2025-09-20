import json
import os
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

DB_FILE = "lootgames/modules/database_group.json"

# pastikan file database ada
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({}, f, indent=2)

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

def get_user_id_by_username(username: str):
    username = username.lower().replace("@", "")
    data = load_db()
    for uid, info in data.items():
        if info.get("username","").lower() == username:
            return int(uid)
    return None

# ---------------- HANDLER START ---------------- #
async def start_handler(client: Client, message: Message):
    user = message.from_user
    add_user(user.id, user.username)
    await message.reply("Hi, salam kenal.. Bot sudah aktif ✅")

# ---------------- REGISTER ---------------- #
def register(app: Client):
    # gunakan MessageHandler di Pyrogram v2+
    handler = MessageHandler(
        start_handler,
        filters=filters.private & filters.command("start")
    )
    app.add_handler(handler)
