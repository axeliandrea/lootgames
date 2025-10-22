# lootgames/modules/umpan.py 
import json
import os
from threading import Lock
from pyrogram import Client

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
    """Inisialisasi user di semua tipe umpan jika belum ada"""
    for jenis in ["A","B","C","D"]:
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
    """Update username di semua tipe umpan"""
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
    if user_id != OWNER_ID:
        if str_id not in db:
            init_user(user_id)
            db = load_db(jenis)
        db[str_id]["umpan"] += jumlah
        save_db(db, jenis)
        print(f"[ADD] User {user_id} +{jumlah} umpan tipe {jenis}. Total sekarang: {db[str_id]['umpan']}")
    else:
        print(f"[ADD] Owner, jumlah umpan tetap unlimited")

def remove_umpan(user_id: int, jenis: str, jumlah: int):
    if jenis not in ["A","B","C","D"]:
        raise ValueError("Jenis umpan harus A, B, C, atau D")
    db = load_db(jenis)
    str_id = str(user_id)
    if user_id == OWNER_ID:
        print(f"[REMOVE] Owner, jumlah umpan tetap unlimited")
        return
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
    """Cari user_id dan data user berdasarkan username"""
    username_clean = username.lower().lstrip("@")
    for jenis in ["A","B","C","D"]:
        db = load_db(jenis)
        for uid, data in db.items():
            if data["username"].lower() == username_clean:
                return int(uid), data
    return None, None

# ---------------- TRANSFER ---------------- #
def transfer_umpan(sender_id: int, recipient_id: int, jenis: str, jumlah: int):
    """
    Transfer umpan dari sender ke recipient.
    Owner tidak kehilangan umpan tapi recipient tetap bertambah.
    """
    if jenis not in ["A","B","C","D"]:
        return False, "Jenis umpan salah"
    if jumlah <= 0:
        return False, "Jumlah harus > 0"

    db_sender = load_db(jenis)
    db_recipient = load_db(jenis)
    str_sender = str(sender_id)
    str_recipient = str(recipient_id)

    if str_sender not in db_sender:
        init_user(sender_id)
        db_sender = load_db(jenis)
    if str_recipient not in db_recipient:
        init_user(recipient_id)
        db_recipient = load_db(jenis)

    # Kurangi umpan sender (kecuali owner)
    if sender_id != OWNER_ID:
        if db_sender[str_sender]["umpan"] < jumlah:
            return False, f"Umpan {jenis} tidak cukup"
        db_sender[str_sender]["umpan"] -= jumlah
        save_db(db_sender, jenis)

    # Tambah umpan recipient
    db_recipient[str_recipient]["umpan"] += jumlah
    save_db(db_recipient, jenis)

    return True, f"Transfer {jumlah} umpan tipe {jenis} berhasil"

# ---------------- UTILS ---------------- #
def get_user_ids():
    """Return semua user_id di database (gabungan semua tipe)"""
    ids = set()
    for jenis in ["A","B","C","D"]:
        db = load_db(jenis)
        ids.update([int(k) for k in db.keys()])
    return ids

def init_user_if_missing(user_id: int, username: str = None):
    """Init user hanya jika belum ada di semua tipe"""
    for jenis in ["A","B","C","D"]:
        db = load_db(jenis)
        str_id = str(user_id)
        if str_id not in db:
            db[str_id] = {"username": username or f"user_{user_id}", "umpan": 0}
            save_db(db, jenis)

# ================================================================
# KOMPATIBILITAS UNTUK MENU_UTAMA (alias fungsi lama)
# ================================================================

def get_umpan(user_id: int, jenis: str) -> int:
    """Mengembalikan jumlah umpan user sesuai jenis."""
    if jenis not in UMPAN_FILES:
        raise ValueError("Jenis umpan tidak valid")
    db = load_db(jenis)
    str_id = str(user_id)
    if str_id not in db:
        init_user(user_id)
        db = load_db(jenis)
    return db[str_id]["umpan"]

def kurangi_umpan(user_id: int, jenis: str, jumlah: int):
    """Alias untuk remove_umpan (biar kompatibel dengan menu_utama)."""
    remove_umpan(user_id, jenis, jumlah)
