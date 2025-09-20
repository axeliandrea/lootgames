import json
import os
from pyrogram import Client, filters

DBGROUP_FILE = "lootgames/modules/database_group.json"

# ================== Helper Functions ================== #
def load_db():
    if not os.path.exists(DBGROUP_FILE):
        return {}
    with open(DBGROUP_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_db(db):
    with open(DBGROUP_FILE, "w") as f:
        json.dump(db, f, indent=4)

def add_user(user_id: int, username: str):
    db = load_db()
    if str(user_id) not in db:
        db[str(user_id)] = {"username": username}
        save_db(db)

def get_user_id_by_username(username: str):
    db = load_db()
    for uid, data in db.items():
        if data.get("username", "").lower() == username.lower().lstrip("@"):
            return int(uid)
    return None

# ================== /start Handler ================== #
def register_start_handler(app: Client):
    @app.on_message(filters.private & filters.command("start"))
    async def start_bot(client, message):
        user_id = message.from_user.id
        username = message.from_user.username or f"user{user_id}"

        # Tambahkan ke database jika belum ada
        add_user(user_id, username)

        # Kirim pesan sambutan
        await message.reply(
            f"Hi {username}, salam kenal.. Bot sudah aktif ✅\n\n"
            "Sekarang kamu sudah terdaftar untuk transfer global."
        )

# ================== Untuk dipanggil dari main ================== #
def register(app: Client):
    register_start_handler(app)
