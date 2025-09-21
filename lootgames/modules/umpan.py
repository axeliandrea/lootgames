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

# Ensure files exist
for f in UMPAN_FILES.values():
    d = os.path.dirname(f)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
    if not os.path.exists(f):
        with open(f, "w") as file:
            json.dump({}, file)

# ---------------- LOAD & SAVE ---------------- #
def load_db(jenis: str):
    if jenis not in UMPAN_FILES:
        raise ValueError("Jenis umpan invalid")
    with LOCK:
        with open(UMPAN_FILES[jenis], "r") as f:
            try:
                return json.load(f)
            except Exception:
                return {}

def save_db(db: dict, jenis: str):
    if jenis not in UMPAN_FILES:
        raise ValueError("Jenis umpan invalid")
    with LOCK:
        with open(UMPAN_FILES[jenis], "w") as f:
            json.dump(db, f, indent=4)

# ---------------- USER OPERATIONS ---------------- #
def init_user(user_id: int, username: str = None):
    """Create user entry in all jenis if missing."""
    str_id = str(user_id)
    for jenis in ["A","B","C","D"]:
        db = load_db(jenis)
        if str_id not in db:
            db[str_id] = {"username": (username or f"user_{user_id}").lstrip("@"), "umpan": 0}
            save_db(db, jenis)
            print(f"[INIT] User baru dibuat: {str_id} ({username}) tipe {jenis}")

def init_user_if_missing(user_id: int, username: str = None):
    """Same as init_user but won't print duplicates (keamanan)."""
    init_user(user_id, username)

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
    uname = username.lstrip("@")
    for jenis in ["A","B","C","D"]:
        db = load_db(jenis)
        str_id = str(user_id)
        if str_id not in db:
            init_user(user_id, uname)
            db = load_db(jenis)
        db[str_id]["username"] = uname
        save_db(db, jenis)
        print(f"[UPDATE] Username {user_id} tipe {jenis} diupdate ke {uname}")

# ---------------- UMPAN OPERATIONS ---------------- #
def add_umpan(user_id: int, jenis: str, jumlah: int):
    """Add umpan (and save). Raises on invalid input."""
    if jenis not in ["A","B","C","D"]:
        raise ValueError("Jenis umpan harus A, B, C, atau D")
    if jumlah <= 0:
        raise ValueError("Jumlah harus > 0")
    if user_id == OWNER_ID:
        # owner unlimited, don't store changes
        print(f"[ADD] Owner, jumlah umpan tetap unlimited (ignored add request)")
        return
    with LOCK:
        db = load_db(jenis)
        str_id = str(user_id)
        if str_id not in db:
            init_user(user_id)
            db = load_db(jenis)
        db[str_id]["umpan"] = db[str_id].get("umpan", 0) + jumlah
        save_db(db, jenis)
        print(f"[ADD] User {user_id} +{jumlah} umpan tipe {jenis}. Total sekarang: {db[str_id]['umpan']}")

def remove_umpan(user_id: int, jenis: str, jumlah: int):
    """Remove umpan (and save). Raises if insufficient."""
    if jenis not in ["A","B","C","D"]:
        raise ValueError("Jenis umpan harus A, B, C, atau D")
    if jumlah <= 0:
        raise ValueError("Jumlah harus > 0")
    if user_id == OWNER_ID:
        print(f"[REMOVE] Owner, jumlah umpan tetap unlimited (ignored remove request)")
        return
    with LOCK:
        db = load_db(jenis)
        str_id = str(user_id)
        if str_id not in db:
            init_user(user_id)
            db = load_db(jenis)
        current = db[str_id].get("umpan", 0)
        if current < jumlah:
            raise ValueError(f"Umpan {jenis} tidak cukup (minta {jumlah}, punya {current})")
        db[str_id]["umpan"] = current - jumlah
        save_db(db, jenis)
        print(f"[REMOVE] User {user_id} -{jumlah} umpan tipe {jenis}. Total sekarang: {db[str_id]['umpan']}")

def total_umpan(user_id: int) -> int:
    if user_id == OWNER_ID:
        return 999
    user_data = get_user(user_id)
    return sum([v.get("umpan", 0) for v in user_data.values()])

def find_user_by_username(username: str):
    """Return (user_id, data) if found in any jenis, else (None, None)."""
    if not username:
        return None, None
    uname = username.lower().lstrip("@")
    for jenis in ["A","B","C","D"]:
        db = load_db(jenis)
        for uid, data in db.items():
            # store usernames without @ in DB
            if data.get("username", "").lower() == uname:
                return int(uid), data
    return None, None

# ---------------- ATOMIC TRANSFER ---------------- #
def transfer_umpan(sender_id: int, recipient_id: int, jenis: str, jumlah: int):
    """
    Transfer umpan secara atomik.
    Returns (True, message) jika sukses, (False, message) jika gagal.
    """
    if jenis not in ["A","B","C","D"]:
        return False, "Jenis umpan tidak valid"
    if jumlah <= 0:
        return False, "Jumlah harus > 0"
    if sender_id == recipient_id:
        return False, "Tidak bisa transfer ke diri sendiri"

    # Owner special case: owner can add without remove
    if sender_id == OWNER_ID:
        try:
            init_user_if_missing(recipient_id)
            add_umpan(recipient_id, jenis, jumlah)
            return True, "Transfer berhasil (owner)"
        except Exception as e:
            return False, f"Error saat menambahkan umpan ke penerima: {e}"

    # Normal case: check & move within same jenis under LOCK
    with LOCK:
        try:
            # load data for jenis
            db = load_db(jenis)
            s_id = str(sender_id)
            r_id = str(recipient_id)

            # ensure users exist
            if s_id not in db:
                init_user(sender_id)
                db = load_db(jenis)
            if r_id not in db:
                init_user(recipient_id)
                db = load_db(jenis)

            sender_have = db[s_id].get("umpan", 0)
            if sender_have < jumlah:
                return False, f"Saldo tidak cukup (minta {jumlah}, punya {sender_have})"

            # do transfer
            db[s_id]["umpan"] = sender_have - jumlah
            db[r_id]["umpan"] = db[r_id].get("umpan", 0) + jumlah

            # save
            save_db(db, jenis)
            return True, "Transfer berhasil"
        except Exception as e:
            return False, f"Error saat transfer: {e}"

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
            # cannot auto-generate Telegram ID: create temp id by next available numeric id (legacy behaviour)
            # but prefer admin to ensure username->id mapping via user_database
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
