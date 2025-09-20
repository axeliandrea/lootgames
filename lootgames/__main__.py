import json
import os
from threading import Lock
from pyrogram import Client, filters, handlers
from pyrogram.types import Message

OWNER_ID = 6395738130
UMPAN_FILE = "lootgames/modules/umpan_data.json"
LOCK = Lock()

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
        db[str_id] = {"username": username or f"user_{user_id}", "umpan": {"A": 0, "B": 0, "C": 0}}
        save_db(db)
        print(f"[INIT] User baru dibuat: {str_id} ({username})")

def get_user(user_id: int):
    db = load_db()
    str_id = str(user_id)
    if str_id not in db:
        init_user(user_id)
        db = load_db()
    return db[str_id]

def find_user_by_username(username: str):
    db = load_db()
    for uid, data in db.items():
        if data["username"].lower() == username.lower().lstrip("@"):
            return int(uid), data
    return None, None

def update_username(user_id: int, username: str):
    db = load_db()
    str_id = str(user_id)
    if str_id not in db:
        init_user(user_id, username)
        db = load_db()
    db[str_id]["username"] = username
    save_db(db)
    print(f"[UPDATE] Username user {str_id} diupdate menjadi {username}")

# ---------------- UMPAN OPERATIONS ---------------- #
def add_umpan(user_id: int, jenis: str, jumlah: int):
    if jenis not in ["A", "B", "C"]:
        raise ValueError("Jenis umpan harus A, B, atau C")
    user = get_user(user_id)
    user["umpan"][jenis] += jumlah
    db = load_db()
    db[str(user_id)] = user
    save_db(db)
    print(f"[ADD] User {user_id} tambah {jumlah} umpan {jenis}. Total sekarang: {total_umpan(user_id)}")

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
    print(f"[REMOVE] User {user_id} kurangi {jumlah} umpan {jenis}. Total sekarang: {total_umpan(user_id)}")

def total_umpan(user_id: int) -> int:
    if user_id == OWNER_ID:
        return 999
    user = get_user(user_id)
    return sum(user["umpan"].values())

def all_users():
    return load_db()

# ---------------- COMMAND TOPUP ---------------- #
async def topup_umpan(client: Client, message: Message):
    try:
        parts = message.text.strip().split()
        if len(parts) != 3 or parts[0].lower() != ".topup":
            await message.reply("Format salah. Gunakan: .topup @username <jumlah>")
            return

        target_username = parts[1].lstrip("@")
        jumlah = int(parts[2])
        if jumlah <= 0:
            await message.reply("Jumlah umpan harus lebih dari 0.")
            return

        # Cari user berdasarkan username
        user_id, user_data = find_user_by_username(target_username)
        if user_id is None:
            # Kalau tidak ada, buat user baru dengan nama username
            user_id = max([int(k) for k in load_db().keys()], default=1000) + 1
            init_user(user_id, target_username)
            print(f"[INFO] User baru dibuat untuk topup: {user_id} ({target_username})")

        add_umpan(user_id, "A", jumlah)
        total = total_umpan(user_id)
        await message.reply(f"✅ Berhasil topup {jumlah} umpan untuk @{target_username}! Total UMPAN sekarang: {total}")
        print(f"[TOPUP] User {user_id} ({target_username}) ditopup {jumlah} umpan. Total: {total}")

    except ValueError:
        await message.reply("Jumlah umpan harus berupa angka!")
    except Exception as e:
        await message.reply(f"❌ Terjadi error: {e}")
        print(f"[ERROR] topup_umpan: {e}")

# ---------------- COMMAND CEK UMPAN ---------------- #
async def check_umpanku(client: Client, message: Message):
    try:
        user_id = message.from_user.id
        total = total_umpan(user_id)
        await message.reply(f"🎣 Total UMPAN Anda: {total}")
        print(f"[CEK] User {user_id} cek umpan. Total: {total}")
    except Exception as e:
        await message.reply(f"❌ Terjadi error: {e}")
        print(f"[ERROR] check_umpanku: {e}")

# ---------------- REGISTER ---------------- #
def register_topup(app: Client):
    # regex: .topup @username jumlah
    app.add_handler(handlers.MessageHandler(topup_umpan, filters.regex(r"^\.topup\s+@\w+\s+\d+$")))
    app.add_handler(handlers.MessageHandler(check_umpanku, filters.regex(r"^\.umpanku$")))
