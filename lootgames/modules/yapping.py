# lootgames/modules/yapping.py
import os, re, json
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= CONFIG ================= #
OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772   # <-- FIXED group ID
YAPPINGPOINT_DB = "storage/chat_points.json"
DEBUG = True
IGNORED_USERS = ["6946903915"]
MAX_POINT_PER_CHAT = 5   # maksimal point per chat bubble
MILESTONE_INTERVAL = 100 # setiap 100 point chat beri notifikasi
LOGIN_DB_FILE = "storage/login_data.json"

# ================= UTILS ================= #
def log_debug(msg: str):
    if DEBUG:
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
    log_debug(f"Data disimpan ke {file_path}")

# ================= POINTS ================= #
def load_points() -> dict:
    return load_json(YAPPINGPOINT_DB)

def save_points(data):
    save_json(YAPPINGPOINT_DB, data)

def add_user_if_not_exist(points, user_id, username):
    user_id = str(user_id)
    if user_id not in points:
        points[user_id] = {
            "username": username,
            "points": 0,
            "level": 0,
            "last_milestone": 0
        }
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
    log_debug(f"{username} ({user_id}) +{amount} point | total: {points[str(user_id)]['points']}")

def update_points(user_id, points_change):
    points = load_points()
    user_id = str(user_id)
    if user_id not in points:
        points[user_id] = {"username": "Unknown", "points": 0, "level": 0, "last_milestone": 0}
    points[user_id]["points"] += points_change
    save_points(points)
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
    print("[YAPPING] Handler registered ✅ (Target group:", TARGET_GROUP, ")")

    # ----- AUTO POINT DARI CHAT DI GROUP ----- #
    @app.on_message(filters.chat(TARGET_GROUP) & filters.text)
    async def handle_chat(client: Client, message: Message):
        log_debug(f"Pesan masuk dari {message.from_user.id if message.from_user else 'UNKNOWN'}: {message.text}")

        user = message.from_user
        if not user or str(user.id) in IGNORED_USERS:
            return
        text = message.text or ""
        points = load_points()
        username = user.username or user.first_name or str(user.id)

        amount = calculate_points_from_text(text)
        if amount > 0:
            add_points(points, user.id, username, amount)

            # Check level up
            new_level = check_level_up(points[str(user.id)])
            if new_level != -1:
                await message.reply_text(
                    f"🎉 Selamat {username}, naik ke level {new_level}! {get_badge(new_level)}"
                )

            # milestone
            total_points = points[str(user.id)]["points"]
            last_milestone = points[str(user.id)].get("last_milestone", 0)
            if total_points // MILESTONE_INTERVAL > last_milestone:
                points[str(user.id)]["last_milestone"] = total_points // MILESTONE_INTERVAL
                await message.reply_text(
                    f"🏆 {username} mencapai {total_points} poin!"
                )

            save_points(points)

    # ----- COMMAND DI GROUP ----- #
    @app.on_message(filters.command("rank", prefixes=["/", "."]) & filters.chat(TARGET_GROUP))
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

    @app.on_message(filters.command("leaderboard", prefixes=["/", "."]) & filters.chat(TARGET_GROUP))
    async def leaderboard_cmd(client: Client, message: Message):
        points = load_points()
        text = generate_leaderboard(points, top=10)
        await message.reply_text(text)

    @app.on_message(filters.command("resetyapping", prefixes=["/", "."]) & filters.chat(TARGET_GROUP))
    async def reset_yapping_cmd(client: Client, message: Message):
        if message.from_user.id != OWNER_ID:
            await message.reply_text("❌ Kamu tidak punya izin untuk reset poin.")
            return
        save_points({})
        await message.reply_text("✅ Semua poin yapping sudah direset menjadi 0.")
        log_debug("Database poin yapping direset oleh OWNER")

    # ----- COMMAND CPC (HANYA PRIVATE, OWNER ONLY) ----- #
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

        # cari user_id dari DB
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

        await message.reply_text(
            f"✅ Poin {points[target_id]['username']} berhasil di-set ke {amount}."
        )
        log_debug(f"OWNER set poin {points[target_id]['username']} ({target_id}) jadi {amount}")

#login
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
        print(f"Gagal simpan login DB: {e}")
