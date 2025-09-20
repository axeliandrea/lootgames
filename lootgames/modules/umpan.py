import json
import os
from threading import Lock
from pyrogram import Client, filters
from pyrogram.types import Message

UMPAN_FILE = "lootgames/modules/umpan_data.json"
LOCK = Lock()
OWNER_ID = 6395738130

# ---------------- INIT DATABASE ---------------- #
if not os.path.exists(UMPAN_FILE):
    with open(UMPAN_FILE, "w") as f:
        json.dump({}, f)

def load_db():
    with LOCK:
        with open(UMPAN_FILE, "r") as f:
            return json.load(f)

def save_db(db):
    with LOCK:
        with open(UMPAN_FILE, "w") as f:
            json.dump(db, f, indent=4)

# ---------------- USER DATA ---------------- #
def init_user(user_id: int, username: str = None):
    db = load_db()
    str_id = str(user_id)
    if str_id not in db:
        default_umpan = {"A": 999, "B": 0, "C": 0} if user_id == OWNER_ID else {"A": 0, "B": 0, "C": 0}
        db[str_id] = {
            "username": username or f"user_{user_id}",
            "umpan": default_umpan
        }
        save_db(db)

def get_user(user_id: int):
    db = load_db()
    str_id = str(user_id)
    if str_id not in db:
        init_user(user_id)
        db = load_db()
    return db[str_id]

def update_username(user_id: int, username: str):
    db = load_db()
    str_id = str(user_id)
    if str_id not in db:
        init_user(user_id, username)
        db = load_db()
    db[str_id]["username"] = username
    save_db(db)

# ---------------- UMPAN OPERATIONS ---------------- #
def add_umpan(user_id: int, jenis: str, jumlah: int):
    if jenis not in ["A", "B", "C"]:
        raise ValueError("Jenis umpan harus A, B, atau C")
    user = get_user(user_id)
    user["umpan"][jenis] += jumlah
    db = load_db()
    db[str(user_id)] = user
    save_db(db)

def remove_umpan(user_id: int, jenis: str, jumlah: int):
    if jenis not in ["A", "B", "C"]:
        raise ValueError("Jenis umpan harus A, B, atau C")
    user = get_user(user_id)
    if user["umpan"][jenis] < jumlah:
        raise ValueError(f"Umpan {jenis} tidak cukup")
    user["umpan"][jenis] -= jumlah
    db = load_db()
    db[str(user_id)] = user
    save_db(db)

def total_umpan(user_id: int) -> int:
    user = get_user(user_id)
    return sum(user["umpan"].values())

def all_users():
    return load_db()

# ---------------- COMMANDS ---------------- #
async def topup_umpan(client: Client, message: Message):
    try:
        parts = message.text.strip().split()
        if len(parts) != 3 or parts[1].lower() != "umpan":
            await message.reply("Format salah. Gunakan: .topup umpan <jumlah>")
            return

        jumlah = int(parts[2])
        if jumlah <= 0:
            await message.reply("Jumlah umpan harus lebih dari 0.")
            return

        user_id = message.from_user.id
        username = message.from_user.username or f"user_{user_id}"
        init_user(user_id, username)
        add_umpan(user_id, "A", jumlah)

        total = total_umpan(user_id)
        await message.reply(f"✅ Berhasil topup {jumlah} umpan! Total UMPAN sekarang: {total}")

    except ValueError:
        await message.reply("Jumlah umpan harus berupa angka!")
    except Exception as e:
        await message.reply(f"❌ Terjadi error: {e}")

async def umpanku(client: Client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    init_user(user_id, username)
    total = total_umpan(user_id)
    await message.reply(f"📊 UMPAN milik {username}: {total}")

# ---------------- REGISTER ---------------- #
def register_commands(app: Client):
    app.add_handler(filters.regex(r"^\.topup\s+umpan\s+\d+$")(topup_umpan))
    app.add_handler(filters.regex(r"^\.umpanku$")(umpanku))
