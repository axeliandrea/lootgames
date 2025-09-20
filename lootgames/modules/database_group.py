import json
import os
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler

DB_FILE = "lootgames/modules/database_group.json"

# Pastikan file database ada
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({}, f)

def load_db():
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def add_user(user_id: int, username: str):
    data = load_db()
    if str(user_id) not in data:
        data[str(user_id)] = {"username": username}
        save_db(data)

def get_user_id_by_username(username: str):
    data = load_db()
    for uid, info in data.items():
        if info.get("username", "").lower() == username.lower().replace("@",""):
            return int(uid)
    return None

# ---------------- HANDLER ---------------- #
async def start_handler(client: Client, message):
    user = message.from_user
    add_user(user.id, user.username or f"user{user.id}")
    await message.reply("Hi, salam kenal.. Bot sudah aktif ✅")

# ---------------- REGISTER ---------------- #
def register(app: Client):
    app.add_handler(MessageHandler(start_handler, filters.private & filters.command("start")))
