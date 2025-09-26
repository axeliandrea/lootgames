# lootgames/modules/yapping.py
import os, re, json
import logging
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from lootgames.config import ALLOWED_GROUP_ID, OWNER_ID

# ================= CONFIG ================= #
YAPPINGPOINT_DB = "storage/chat_points.json"
DEBUG = True
IGNORED_USERS = ["6946903915"]
MAX_POINT_PER_CHAT = 5
MILESTONE_INTERVAL = 100
LOGIN_DB_FILE = "storage/login_data.json"

# ================= LOGGING ================= #
logger = logging.getLogger(__name__)
if DEBUG:
    logger.setLevel(logging.DEBUG)

def log_debug(msg: str):
    logger.debug(msg)

# ================= JSON UTILS ================= #
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
    log_debug(f"Data disimpan ke {file_path}")

# ================= POINTS ================= #
def load_points() -> dict:
    return load_json(YAPPINGPOINT_DB)

def save_points(data):
    save_json(YAPPINGPOINT_DB, data)

def calculate_points_from_text(text: str) -> int:
    letters_only = re.sub(r"[^a-zA-Z]", "", text)
    if len(letters_only) < 5:
        return 0
    points = len(letters_only) // 5
    return min(points, MAX_POINT_PER_CHAT)

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

# ================= UPDATE POINTS ================= #
def update_points(user_id: int, amount: int, username: str = None):
    data = load_points()
    uid = str(user_id)

    if uid not in data:
        data[uid] = {
            "username": username or str(user_id),
            "points": 0,
            "level": 0,
            "last_milestone": 0
        }

    if username:
        data[uid]["username"] = username

    data[uid]["points"] += amount
    if data[uid]["points"] < 0:
        data[uid]["points"] = 0

    # cek level up
    new_level = check_level_up(data[uid])
    if new_level != -1:
        log_debug(f"User {data[uid]['username']} naik ke level {new_level}")

    save_points(data)
    return new_level

# ================= LEADERBOARD ================= #
def generate_leaderboard(points: dict, top=0) -> str:
    sorted_points = sorted(points.items(), key=lambda x: x[1].get("points", 0), reverse=True)
    if not sorted_points: 
        return "Leaderboard kosong"
    text = "🏆 Leaderboard 🏆\n\n"
    for i, (uid, data) in enumerate(sorted_points, start=1):
        if top and i > top: break
        text += f"{i}. {data['username']} - {data['points']} pts | Level {data['level']} {get_badge(data['level'])}\n"
    return text

# ================= HANDLER REGISTER ================= #
def register(app: Client):
    log_debug(f"[YAPPING] Handler registered ✅ (Target group: {ALLOWED_GROUP_ID})")

    @app.on_message(filters.chat(ALLOWED_GROUP_ID) & filters.text)
    async def handle_chat(client: Client, message: Message):
        user = message.from_user
        if not user or str(user.id) in IGNORED_USERS:
            return

        text = message.text or ""
        log_debug(f"[CHAT] Dari {user.id} ({user.username}) → {text}")

        username = user.username or user.first_name or str(user.id)

        amount = calculate_points_from_text(text)
        if amount <= 0:
            return

        new_level = update_points(user.id, amount, username)

        if new_level != -1:
            try:
                await message.reply_text(
                    f"🎉 Selamat {username}, naik ke level {new_level}! {get_badge(new_level)}"
                )
            except Exception as e:
                log_debug(f"Gagal kirim level up: {e}")

        # milestone
        points = load_points()
        total_points = points[str(user.id)]["points"]
        last_milestone = points[str(user.id)].get("last_milestone", 0)
        if total_points // MILESTONE_INTERVAL > last_milestone:
            points[str(user.id)]["last_milestone"] = total_points // MILESTONE_INTERVAL
            try:
                await message.reply_text(f"🏆 {username} mencapai {total_points} poin!")
            except Exception as e:
                log_debug(f"Gagal kirim milestone: {e}")
            save_points(points)

    # ----- COMMANDS ----- #
    @app.on_message(filters.command("rank", prefixes=["/", "."]) & filters.chat(ALLOWED_GROUP_ID))
    async def rank_cmd(client: Client, message: Message):
        user = message.from_user
        if not user: return
        points = load_points()
        user_data = points.get(str(user.id))
        if not user_data:
            await message.reply_text("Kamu belum punya poin.")
            return
        await message.reply_text(
            f"📊 {user_data['username']} - {user_data['points']} pts | Level {user_data['level']} {get_badge(user_data['level'])}"
        )

    @app.on_message(filters.command("leaderboard", prefixes=["/", "."]) & filters.chat(ALLOWED_GROUP_ID))
    async def leaderboard_cmd(client: Client, message: Message):
        points = load_points()
        text = generate_leaderboard(points, top=10)
        await message.reply_text(text)

    @app.on_message(filters.command("resetyapping", prefixes=["/", "."]) & filters.chat(ALLOWED_GROUP_ID))
    async def reset_yapping_cmd(client: Client, message: Message):
        if message.from_user.id != OWNER_ID:
            await message.reply_text("❌ Kamu tidak punya izin untuk reset poin.")
            return
        save_points({})
        await message.reply_text("✅ Semua poin yapping sudah direset menjadi 0.")
        log_debug("Database poin yapping direset oleh OWNER")

    @app.on_message(filters.command("cpc", prefixes=[".", "/"]) & filters.private)
    async def cheat_point_cmd(client: Client, message: Message):
        if message.from_user.id != OWNER_ID:
            await message.reply_text("❌ Kamu tidak punya izin untuk cheat point.")
            return

        if len(message.command) < 3:
            await message.reply_text("⚠️ Format: .cpc @username jumlah")
            return

        target_username = message.command[1].lstrip("@")
        try:
            amount = int(message.command[2])
        except ValueError:
            await message.reply_text("⚠️ Jumlah harus angka.")
            return

        points = load_points()
        target_id = None
        for uid, data in points.items():
            if data["username"].lower() == target_username.lower():
                target_id = uid
                break

        if not target_id:
            await message.reply_text("❌ User tidak ditemukan di database poin.")
            return

        points[target_id]["points"] = amount
        save_points(points)
        await message.reply_text(f"✅ Poin {points[target_id]['username']} berhasil di-set ke {amount}.")
        log_debug(f"OWNER set poin {points[target_id]['username']} ({target_id}) jadi {amount}")

# ================= LOGIN ================= #
def load_login() -> dict:
    try:
        with open(LOGIN_DB_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_login(data: dict):
    try:
        with open(LOGIN_DB_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log_debug(f"Gagal simpan login DB: {e}")
