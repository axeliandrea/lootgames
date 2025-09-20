import json
import os
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.handlers import MessageHandler
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

DBGROUP_FILE = "lootgames/modules/database_group.json"

# ==================== DATABASE ==================== #
if not os.path.exists(DBGROUP_FILE):
    with open(DBGROUP_FILE, "w") as f:
        json.dump({}, f)

def load_db():
    with open(DBGROUP_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DBGROUP_FILE, "w") as f:
        json.dump(data, f, indent=2)

def add_user(user_id, username):
    db = load_db()
    if str(user_id) not in db:
        db[str(user_id)] = {"username": username}
        save_db(db)
        logger.debug(f"User {username} ({user_id}) ditambahkan ke database")
    else:
        logger.debug(f"User {username} ({user_id}) sudah ada di database")

def get_user_id_by_username(username):
    db = load_db()
    username_clean = username.lstrip("@").lower()
    for uid, data in db.items():
        if data.get("username","").lower() == username_clean:
            return int(uid)
    return None

# ==================== HANDLER /START ==================== #
async def start_handler(client: Client, message: Message):
    user = message.from_user
    if not user:
        return
    add_user(user.id, user.username or f"user{user.id}")
    await message.reply(f"Hi @{user.username or 'User'}, salam kenal.. Bot sudah aktif ✅")

# ==================== REGISTER ==================== #
def register(app: Client):
    app.add_handler(MessageHandler(start_handler, filters.private & filters.command("start")))
