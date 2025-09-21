# lootgames/modules/umpan.py
import json
import os
from threading import Lock
from pyrogram import Client, filters, handlers
from pyrogram.types import Message

OWNER_ID = 6395738130

# ---------------- FILE DATABASE ---------------- #
UMPAN_FILES = {
    "A": "lootgames/modules/umpan_data.json",        # Common
    "B": "lootgames/modules/umpanrare_data.json",    # Rare
    "C": "lootgames/modules/umpanlegend_data.json",  # Legend
    "D": "lootgames/modules/umpanmythic_data.json"   # Mythic
}

LOCK = Lock()

# ---------------- INIT DATABASE ---------------- #
for f in UMPAN_FILES.values():
    if not os.path.exists(f):
        with open(f, "w") as file:
            json.dump({}, file)

# ---------------- LOAD & SAVE ---------------- #
def load_db(jenis: str):
    with LOCK:
        with open(UMPAN_FILES[jenis], "r") as f:
            return json.load(f)

def save_db(db: dict, jenis: str):
    with LOCK:
        with open(UMPAN_FILES[jenis], "w") as f:
            json.dump(db, f, indent=4)

# ---------------- USER OPERATIONS ---------------- #
def init_user(user_id: int, username: str = None):
    for jenis, f in UMPAN_FILES.items():
        db = load_db(jenis)
        str_id = str(user_id)
        if str_id not in db:
            db[str_id] = {"username": username or f"user_{user_id}", "umpan": 0}
            save_db(db, jenis)
            print(f"[INIT] User baru dibuat: {str_id} ({username}) tipe {jenis}")

def get_user(user_id: int):
    """Return dict semua tipe umpan untuk user"""
    result = {}
    for jenis in ["A","B","C","D"]:
        db = load_db(jenis)
        str_id = str(user_id)
        if str_id not in db:
            init_user(user_id)
            db = load_db(jenis)
        result[jenis] = db[str_id]
    return result

def update_username(user_id: int, username: str):
    for jenis in ["A","B","C","D"]:
        db = load_db(jenis)
        str_id = str(user_id)
        if str_id not in db:
            init_user(user_id, username)
            db = load_db(jenis)
        db[str_id]["username"] = username
        save_db(db, jenis)
        print(f"[UPDATE] Username {user_id} tipe {jenis} diupdate ke {username}")

# ---------------- UMPAN OPERATIONS ---------------- #
def add_umpan(user_id: int, jenis: str, jumlah: int):
    if jenis not in ["A","B","C","D"]:
        raise ValueError("Jenis umpan harus A, B, C, atau D")
    db = load_db(jenis)
    str_id = str(user_id)
    if user_id == OWNER_ID:
        print(f"[ADD] Owner, jumlah umpan tetap unlimited")
        return
    if str_id not in db:
        init_user(user_id)
        db = load_db(jenis)
    db[str_id]["umpan"] += jumlah
    save_db(db, jenis)
    print(f"[ADD] User {user_id} +{jumlah} umpan tipe {jenis}. Total sekarang: {db[str_id]['umpan']}")

def remove_umpan(user_id: int, jenis: str, jumlah: int):
    if jenis not in ["A","B","C","D"]:
        raise ValueError("Jenis umpan harus A, B, C, atau D")
    if user_id == OWNER_ID:
        print(f"[REMOVE] Owner, jumlah umpan tetap unlimited")
        return
    db = load_db(jenis)
    str_id = str(user_id)
    if str_id not in db:
        init_user(user_id)
        db = load_db(jenis)
    if db[str_id]["umpan"] < jumlah:
        raise ValueError(f"Umpan {jenis} tidak cukup")
    db[str_id]["umpan"] -= jumlah
    save_db(db, jenis)
    print(f"[REMOVE] User {user_id} -{jumlah} umpan tipe {jenis}. Total sekarang: {db[str_id]['umpan']}")

def total_umpan(user_id: int) -> int:
    if user_id == OWNER_ID:
        return 999
    user_data = get_user(user_id)
    return sum([v["umpan"] for v in user_data.values()])

def find_user_by_username(username: str):
    for jenis in ["A","B","C","D"]:
        db = load_db(jenis)
        for uid, data in db.items():
            if data["username"].lower() == username.lower().lstrip("@"):
                return int(uid), data
    return None, None

# ---------------- COMMAND TOPUP ---------------- #
async def topup_umpan(client: Client, message: Message):
    try:
        parts = message.text.strip().split()
        if len(parts) != 4 or parts[0].lower() != ".topup":
            await message.reply("Format salah. Gunakan: .topup @username <jumlah> <type: A/B/C/D>")
            return

        target_username = parts[1].lstrip("@")
        jumlah = int(parts[2])
        jenis = parts[3].upper()
        if jenis not in ["A","B","C","D"]:
            await message.reply("Jenis umpan salah! Gunakan A/B/C/D")
            return
        if jumlah <= 0:
            await message.reply("Jumlah umpan harus > 0")
            return

        # Cari user
        user_id, _ = find_user_by_username(target_username)
        if user_id is None:
            user_id = max([int(k) for k in get_user_ids()], default=1000)+1
            init_user(user_id, target_username)

        add_umpan(user_id, jenis, jumlah)
        total = get_user(user_id)[jenis]["umpan"]
        await message.reply(f"✅ Topup {jumlah} umpan tipe {jenis} ke @{target_username} berhasil!\nTotal sekarang: {total}")
    except Exception as e:
        await message.reply(f"❌ Terjadi error: {e}")

# ---------------- REGISTER ---------------- #
def register_topup(app: Client):
    # .topup @username jumlah type
    app.add_handler(handlers.MessageHandler(topup_umpan, filters.regex(r"^\.topup\s+@\w+\s+\d+\s+[A-Da-d]$")))

# ---------------- UTILS ---------------- #
def get_user_ids():
    """Return semua user_id di database (gabungan semua tipe)"""
    ids = set()
    for jenis in ["A","B","C","D"]:
        db = load_db(jenis)
        ids.update([int(k) for k in db.keys()])
    return ids
