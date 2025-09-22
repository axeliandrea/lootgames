# lootgames/modules/yapping.py
import os, re, json
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= CONFIG ================= #
OWNER_ID = 6395738130
TARGET_GROUP = -1002904817520
YAPPINGPOINT_DB = "storage/chat_points.json"
DEBUG = True
IGNORED_USERS = ["6946903915"]
MAX_POINT_PER_CHAT = 5  # maksimal point per chat per chat bubble
MILESTONE_INTERVAL = 100  # setiap 100 point chat beri notifikasi

# ================= UTILS ================= #
def log_debug(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[DEBUG] {timestamp} - {msg}")

def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            log_debug(f"JSON rusak: {file_path}, membuat ulang")
            return {}
    return {}

def save_json(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    if DEBUG:
        log_debug(f"Data disimpan ke {file_path}")

# ================= POINTS ================= #
def load_points() -> dict:
    return load_json(YAPPINGPOINT_DB)

def save_points(data):
    save_json(YAPPINGPOINT_DB, data)

def add_user_if_not_exist(points, user_id, username):
    user_id = str(user_id)
    if user_id not in points:
        points[user_id] = {"username": username, "points": 0, "level": 0, "last_milestone": 0}
        if DEBUG:
            log_debug(f"User baru ditambahkan: {username} ({user_id})")
    else:
        points[user_id]["username"] = username
        points[user_id].setdefault("level", 0)
        points[user_id].setdefault("last_milestone", 0)

def calculate_points_from_text(text: str) -> int:
    clean_text = re.sub(r"[^a-zA-Z]", "", text)
    points = len(clean_text) // 5
    return min(points, MAX_POINT_PER_CHAT)

def add_points(points, user_id, username, amount):
    add_user_if_not_exist(points, user_id, username)
    points[str(user_id)]["points"] += amount
    if DEBUG:
        log_debug(f"{username} ({user_id}) +{amount} point | total: {points[str(user_id)]['points']}")

def update_points(user_id, points_change):
    points = load_points()
    user_id = str(user_id)
    if user_id not in points:
        points[user_id] = {"username": "Unknown", "points": 0, "level": 0, "last_milestone": 0}
    points[user_id]["points"] += points_change
    save_points(points)
    if DEBUG:
        log_debug(f"Updated points for {user_id}: {points_change} change")

# ================= LEVEL & BADGE ================= #
LEVEL_EXP = {}
base_exp = 10000
factor = 1.4
for lvl in range(0, 100):
    LEVEL_EXP[lvl] = int(base_exp)
    base_exp = int(base_exp * factor)

def check_level_up(user_data: dict) -> int:
    points_val = user_data.get("points", 0)
    old_level = user_data.get("level", 0)
    new_level = old_level
    for lvl in range(0, 99):
        if points_val >= LEVEL_EXP[lvl]:
            new_level = lvl + 1
        else:
            break
    if new_level != old_level:
        user_data["level"] = new_level
        return new_level
    return -1

def get_badge(level: int) -> str:
    if level <= 0: return "⬜ NOOB"
    elif level <= 9: return "🥉 VIP 1"
    elif level <= 19: return "🥈 VIP 2"
    elif level <= 29: return "🥇 VIP 3"
    elif level <= 39: return "💎 VIP 4"
    elif level <= 49: return "🔥 VIP 5"
    elif level <= 59: return "👑 VIP 6"
    elif level <= 69: return "🌌 VIP 7"
    elif level <= 79: return "⚡ VIP 8"
    elif level <= 89: return "🐉 VIP 9"
    else: return "🏆 MAX VIP"

# ================= LEADERBOARD ================= #
def generate_leaderboard(points: dict, top=0) -> str:
    sorted_points = sorted(points.items(), key=lambda x: x[1].get("points",0), reverse=True)
    if not sorted_points: return "Leaderboard kosong"
    text = "🏆 Leaderboard 🏆\n\n"
    for i, (uid, data) in enumerate(sorted_points, start=1):
        if top and i > top: break
        text += f"{i}. {data['username']} - {data['points']} pts | Level {data['level']} {get_badge(data['level'])}\n"
    return text
