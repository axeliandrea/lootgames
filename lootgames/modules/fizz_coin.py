# lootgames/modules/fizz_coin.py
import json
import os
import threading

_LOCK = threading.Lock()

# ---------------- PATH DB ---------------- #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "../storage/fizz_coin.json")

os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

# ---------------- HELPER LOAD / SAVE ---------------- #
def _load_db() -> dict:
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        print(f"[DEBUG] fizz_coin DB created at {DB_FILE}")
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
        print(f"[DEBUG] fizz_coin loaded: {data}")
        return data
    except Exception as e:
        print(f"[DEBUG] fizz_coin load error: {e}")
        return {}

def _save_db(db: dict):
    try:
        with _LOCK:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
        print(f"[DEBUG] fizz_coin saved: {db}")
    except Exception as e:
        print(f"[DEBUG] fizz_coin save error: {e}")

# ---------------- PUBLIC FUNCTIONS ---------------- #
def add_coin(user_id: int, amount: int) -> int:
    """Tambah atau kurangi coin user. Bisa negatif. Kembalikan total baru."""
    db = _load_db()
    uid = str(user_id)
    old = db.get(uid, 0)
    new_total = old + amount
    if new_total < 0:
        new_total = 0  # coin tidak boleh negatif
    db[uid] = new_total
    _save_db(db)
    print(f"[DEBUG] add_coin - user:{uid} old:{old} change:{amount} total:{db[uid]}")
    return db[uid]

def get_coin(user_id: int) -> int:
    db = _load_db()
    uid = str(user_id)
    total = db.get(uid, 0)
    print(f"[DEBUG] get_coin - user:{uid} total:{total}")
    return total

def reset_coin(user_id: int):
    db = _load_db()
    uid = str(user_id)
    db[uid] = 0
    _save_db(db)
    return 0

def reset_all():
    db = {}
    _save_db(db)
    return True
