# lootgames/modules/user_database.py
import json
import os

DB_FILE = "lootgames/modules/user_database.json"

# ================= HELPERS ================= #
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ================= REGISTER FUNCTION ================= #
def register(app):
    """Placeholder untuk logic .join/.update user"""
    pass

# ================= USER HELPERS ================= #
def get_user_id_by_username(username: str):
    """Cari user_id berdasarkan username @username"""
    db = load_db()
    for uid, info in db.items():
        if info.get("username", "").lower() == username.lower().lstrip("@"):
            return int(uid)
    return None

def set_player_loot(user_id: int, status: bool = True, username: str = None):
    """Set status user sebagai Player Loot"""
    db = load_db()
    str_uid = str(user_id)
    if str_uid not in db:
        db[str_uid] = {}
    db[str_uid]["player_loot"] = status
    if username:
        db[str_uid]["username"] = username.lstrip("@")
    save_db(db)

def get_user_data(user_id: int):
    db = load_db()
    return db.get(str(user_id), {})
