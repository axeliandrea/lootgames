# lootgames/modules/yapping.py
import os, re, json
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= CONFIG ================= #
OWNER_ID = 6395738130
TARGET_GROUP = -1002904817520
BOT_USERNAME = "gamesofloot_bot"
POINT_FILE = "storage/chat_points.json"
DEBUG = True
IGNORED_USERS = ["6946903915"]

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
            print(f"[DEBUG] JSON rusak: {file_path}, membuat ulang")
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
    return load_json(POINT_FILE)

def save_points(data):
    save_json(POINT_FILE, data)

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

def add_points(user_id, username, amount=1):
    points = load_points()
    add_user_if_not_exist(points, user_id, username)
    points[str(user_id)]["points"] += amount
    log_debug(f"{username} ({user_id}) +{amount} point | total: {points[str(user_id)]['points']}")
    save_points(points)

def edit_points(user_id, amount):
    points = load_points()
    user_id = str(user_id)
    if user_id not in points:
        return False
    points[user_id]["points"] = amount
    save_points(points)
    return True

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
        if top and i > top:
            break
        text += f"{i}. {data['username']} - {data['points']} pts | Level {data['level']} {get_badge(data['level'])}\n"
    return text

# ================= REGISTER HANDLER ================= #
def register(app: Client):

    # ---------------- auto point handler ---------------- #
    @app.on_message(
        filters.chat(TARGET_GROUP) &
        ~filters.command(["mypoint", "resetchatpoint", "kepoin", "noyap", "scanpoint", "ya", "menufish", "rpc"], prefixes=[".", "/"])
    )

    # ---------------- CHAT POINT ---------------- #
    @app.on_message(filters.chat(TARGET_GROUP) & filters.text & ~filters.private)
    async def chat_point_handler(client: Client, message: Message):
        user = message.from_user
        if not user: return
        if str(user.id) in IGNORED_USERS: return

        # Abaikan text command
        if message.text.startswith(("/", ".", "!", "#")): return

        # Hanya hitung huruf alfabet
        text = re.sub(r"[^a-zA-Z]", "", message.text or "")
        if len(text) < 5: return  # minimal 5 huruf = 1 point

        username = user.username or user.first_name or "Unknown"
        add_points(user.id, username)

        # Level up check
        points = load_points()
        new_level = check_level_up(points[str(user.id)])
        if new_level != -1:
            save_points(points)
            await message.reply(
                f"🎉 Selamat {username}, naik level {new_level}! {get_badge(new_level)}",
                quote=True
            )

    # ================= COMMANDS PREFIX TITIK ================= #
    # .mypoint
    @app.on_message(filters.command(["mypoint"]) & (filters.group | filters.private))
    async def mypoint_handler(client, message: Message):
        user_id = str(message.from_user.id)
        points = load_points()
        if user_id not in points:
            await message.reply("📌 Anda belum memiliki poin.")
        else:
            data = points[user_id]
            await message.reply(f"💠 {data['username']} - {data['points']} pts | Level {data['level']} {get_badge(data['level'])}")

    # .board
    @app.on_message(filters.command(["board"]) & (filters.group | filters.private))
    async def board_handler(client, message: Message):
        points = load_points()
        text = generate_leaderboard(points)
        await message.reply(text)

    # .rank5 → Top 5
    @app.on_message(filters.command(["rank5"]) & (filters.group | filters.private))
    async def rank5_handler(client, message: Message):
        points = load_points()
        text = generate_leaderboard(points, top=5)
        await message.reply(text)

    # .rpc @username <jumlah> → edit points (owner)
    # .rpc @username <jumlah> → edit points (owner)
    @app.on_message(filters.command("rpc", prefixes=".") & (filters.group | filters.private))
    async def rpc_handler(client, message: Message):
        if message.from_user.id != OWNER_ID:
            await message.reply("❌ Hanya owner yang bisa mengedit point.")
            return

        parts = message.text.strip().split()
        if len(parts) != 3:
            await message.reply("Format salah. Gunakan: `.rpc @username jumlah`")
            return

        username = parts[1].lstrip("@").lower()
        try:
            jumlah = int(parts[2])
        except ValueError:
            await message.reply("Jumlah harus berupa angka.")
            return

        points = load_points()
        target_id = None
        for uid, data in points.items():
            if data.get("username", "").lower() == username:
                target_id = uid
                break

        if not target_id:
            await message.reply(f"❌ User {username} belum memiliki poin, pastikan user sudah chat sebelumnya.")
            return

    # Update point langsung
    points[target_id]["points"] = jumlah
    save_points(points)

    await message.reply(f"✅ Point {username} diubah menjadi {jumlah} dan tersimpan ke database.")

