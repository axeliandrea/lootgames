import os
import json
from threading import Lock

LOCK = Lock()
DBGROUP_FILE = "lootgames/modules/database_group.json"

# ---------------- INIT DATABASE ---------------- #
if not os.path.exists(DBGROUP_FILE):
    with open(DBGROUP_FILE, "w") as f:
        json.dump({}, f, indent=2)

# ---------------- UTILS ---------------- #
def load_db():
    with LOCK:
        with open(DBGROUP_FILE, "r") as f:
            return json.load(f)

def save_db(db):
    with LOCK:
        with open(DBGROUP_FILE, "w") as f:
            json.dump(db, f, indent=2)

# ---------------- USER OPERATIONS ---------------- #
def init_user(user_id: int, username: str = None):
    db = load_db()
    str_id = str(user_id)
    if str_id not in db:
        db[str_id] = {
            "username": username or f"user_{user_id}"
        }
        save_db(db)

def update_username(user_id: int, username: str):
    db = load_db()
    str_id = str(user_id)
    if str_id not in db:
        init_user(user_id, username)
        db = load_db()
    db[str_id]["username"] = username
    save_db(db)

def get_user_by_id(user_id: int):
    db = load_db()
    return db.get(str(user_id), None)

def get_user_id_by_username(username: str):
    db = load_db()
    for uid, data in db.items():
        if data.get("username", "").lower() == username.lower().lstrip("@"):
            return int(uid)
    return None

def all_users():
    return load_db()
