import json
import os
from threading import Lock
from pyrogram import Client, filters
from pyrogram.types import Message

UMPAN_FILE = "lootgames/modules/umpan_data.json"
LOCK = Lock()
OWNER_ID = 6395738130  # Owner otomatis punya 999 umpan

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
        db[str_id] = {
            "username": username or f"user_{user_id}",
            "umpan": {"A": 0, "B": 0, "C": 0}
        }
        save_db(db)

def get_user(user_id: int):
    if user_id == OWNER_ID:
        # Owner selalu punya 999 umpan total
        return {"username": "OWNER", "umpan": {"A": 999, "B": 0, "C": 0}}
    db = load_db()
    str_id = str(user_id)
    if str_id not in db:
        init_user(user_id)
        db = load_db()
    return db[str_id]

def add_umpan(user_id: int, jenis: str, jumlah: int):
    if jenis not in ["A", "B", "C"]:
        raise ValueError("Jenis umpan harus A, B, atau C")
    if user_id == OWNER_ID:
        return  # Owner tidak perlu ditambah
    user = get_user(user_id)
    user["umpan"][jenis] += jumlah
    db = load_db()
    db[str(user_id)] = user
    save_db(db)

def remove_umpan(user_id: int, jenis: str, jumlah: int):
    if jenis not in ["A", "B", "C"]:
        raise ValueError("Jenis umpan harus A, B, atau C")
    if user_id == OWNER_ID:
        return  # Owner tidak berkurang
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

# ---------------- COMMAND TOPUP ---------------- #
def register_commands(app: Client):

    @app.on_message(filters.command("topup", prefixes=".") & filters.private)
    async def topup_umpan_handler(client: Client, message: Message):
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

    # Command .umpanku untuk cek sisa umpan
    @app.on_message(filters.command("umpanku", prefixes=".") & filters.private)
    async def cek_umpan(client: Client, message: Message):
        user_id = message.from_user.id
        username = message.from_user.username or f"user_{user_id}"
        init_user(user_id, username)
        total = total_umpan(user_id)
        await message.reply(f"📊 Total UMPAN kamu: {total}")
