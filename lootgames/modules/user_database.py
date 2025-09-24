# lootgames/modules/user_database.py
import json
import os
from datetime import datetime, timedelta

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

# ================= REGISTER & UPDATE ================= #
def register_user(user_id: int, username: str = None):
    """Daftarkan user baru jika belum ada di database"""
    db = load_db()
    str_uid = str(user_id)
    if str_uid not in db:
        db[str_uid] = {
            "username": username.lstrip("@") if username else "",
            "daily_streak": 0,
            "weekly_streak": 0,
            "last_login": None,
            "player_loot": False
        }
        save_db(db)
    else:
        if username:
            db[str_uid]["username"] = username.lstrip("@")
            save_db(db)

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

# ================= LOGIN & STREAK ================= #
def update_daily_login(user_id: int):
    """Update login harian user, increment streak harian/mingguan"""
    db = load_db()
    str_uid = str(user_id)
    if str_uid not in db:
        register_user(user_id)
        db = load_db()

    today = datetime.today().date()
    last_login_str = db[str_uid].get("last_login")
    last_login = datetime.strptime(last_login_str, "%Y-%m-%d").date() if last_login_str else None

    # Reset streak mingguan jika lebih dari 7 hari
    reset_weekly_streak_if_needed(user_id)

    if last_login == today:
        return False  # Sudah login hari ini

    # Update streak harian
    if last_login and (today - last_login).days == 1:
        db[str_uid]["daily_streak"] += 1
    else:
        db[str_uid]["daily_streak"] = 1

    # Update streak mingguan
    if last_login and (today - last_login).days <= 7:
        db[str_uid]["weekly_streak"] += 1
    else:
        db[str_uid]["weekly_streak"] = 1

    db[str_uid]["last_login"] = today.strftime("%Y-%m-%d")
    save_db(db)
    return True

def reset_weekly_streak_if_needed(user_id: int):
    """Reset streak mingguan jika user tidak login lebih dari 7 hari"""
    db = load_db()
    str_uid = str(user_id)
    if str_uid not in db:
        return

    last_login_str = db[str_uid].get("last_login")
    if not last_login_str:
        return

    last_login = datetime.strptime(last_login_str, "%Y-%m-%d").date()
    today = datetime.today().date()
    delta_days = (today - last_login).days

    if delta_days >= 7:
        db[str_uid]["weekly_streak"] = 0
        save_db(db)

# ================= RESET / EDIT ================= #
def reset_user_streak(user_id: int):
    """Reset streak harian dan mingguan user"""
    db = load_db()
    str_uid = str(user_id)
    if str_uid in db:
        db[str_uid]["daily_streak"] = 0
        db[str_uid]["weekly_streak"] = 0
        save_db(db)

def edit_username(user_id: int, username: str):
    """Update username user"""
    db = load_db()
    str_uid = str(user_id)
    if str_uid not in db:
        register_user(user_id, username)
    else:
        db[str_uid]["username"] = username.lstrip("@")
        save_db(db)
