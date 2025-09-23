import json
import os
import threading

DB_FILE = "lootgames/storage/fizz_coin.json"
_LOCK = threading.Lock()

# ---------------- INTERNAL HELPERS ---------------- #
def _load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_db(db):
    with _LOCK:
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[fizz_coin] Gagal save DB: {e}")
            return False

# ---------------- PUBLIC FUNCTIONS ---------------- #
def get_coin(user_id: int) -> int:
    db = _load_db()
    return db.get(str(user_id), 0)

def add_coin(user_id: int, amount: int) -> int:
    if amount <= 0:
        return get_coin(user_id)
    db = _load_db()
    uid = str(user_id)
    db[uid] = db.get(uid, 0) + amount
    _save_db(db)
    return db[uid]

def remove_coin(user_id: int, amount: int) -> int:
    if amount <= 0:
        return get_coin(user_id)
    db = _load_db()
    uid = str(user_id)
    current = db.get(uid, 0)
    new_amount = max(0, current - amount)
    db[uid] = new_amount
    _save_db(db)
    return new_amount

def set_coin(user_id: int, amount: int) -> int:
    db = _load_db()
    uid = str(user_id)
    db[uid] = max(0, amount)
    _save_db(db)
    return db[uid]
