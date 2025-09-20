import os
import re
import json
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message

OWNER_ID = 6395738130
TARGET_GROUP = -1002904817520
BOT_USERNAME = "gamesofloot_bot"
POINT_FILE = "storage/chat_points.json"
DEBUG = True
IGNORED_USERS = ["6946903915"]

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

def load_points():
    return load_json(POINT_FILE)

def save_points(data):
    save_json(POINT_FILE, data)

def add_user_if_not_exist(points, user_id, username):
    user_id = str(user_id)
    if user_id not in points:
        points[user_id] = {"username": username, "points": 0, "level": 0}
        log_debug(f"User baru ditambahkan: {username} ({user_id})")
    else:
        points[user_id]["username"] = username
        points[user_id].setdefault("level", 0)

def add_points(user_id, username, amount=1):
    points = load_points()
    add_user_if_not_exist(points, user_id, username)
    points[str(user_id)]["points"] += amount
    log_debug(f"{username} ({user_id}) +{amount} point → total: {points[str(user_id)]['points']}")
    save_points(points)

def check_level_up(user_data):
    old = user_data.get("level", 0)
    new = user_data.get("points", 0)//100
    if new != old:
        user_data["level"] = new
        return new
    return -1

def get_badge(level):
    if level<=0: return "⬜ NOOB"
    elif level<=9: return "🥉 VIP 1"
    elif level<=19: return "🥈 VIP 2"
    elif level<=29: return "🥇 VIP 3"
    elif level<=39: return "💎 VIP 4"
    elif level<=49: return "🔥 VIP 5"
    elif level<=59: return "👑 VIP 6"
    elif level<=69: return "🌌 VIP 7"
    elif level<=79: return "⚡ VIP 8"
    elif level<=89: return "🐉 VIP 9"
    else: return "🏆 MAX VIP"

def register(app: Client):
    log_debug("Registering yapping handlers...")

    @app.on_message(filters.chat(TARGET_GROUP) & filters.text)
    async def chat_point_handler(client, message: Message):
        user = message.from_user
        if not user:
            return
        if str(user.id) in IGNORED_USERS:
            log_debug(f"Ignored user {user.id}")
            return

        letters = re.sub(r"[^a-zA-Z]", "", message.text.strip())
        log_debug(f"Message: {message.text} | letters: {letters} | length: {len(letters)}")
        if len(letters) < 5:
            log_debug("Kurang dari 5 huruf, tidak diberi point")
            return

        username = user.username or user.first_name or "Unknown"
        add_points(user.id, username)
        points = load_points()
        lvl = check_level_up(points[str(user.id)])
        if lvl != -1:
            save_points(points)
            try:
                await message.reply(f"🎉 {username} naik level {lvl}! {get_badge(lvl)}")
            except Exception as e:
                log_debug(f"Gagal reply level up: {e}")

    @app.on_message(filters.command(["mypoint", f"mypoint@{BOT_USERNAME}"]))
    async def mypoint(client, message: Message):
        uid = str(message.from_user.id)
        pts = load_points()
        if uid not in pts:
            await message.reply("Belum ada point")
        else:
            data = pts[uid]
            await message.reply(f"{data['username']} - {data['points']} pts | Level {data['level']} {get_badge(data['level'])}")

    log_debug("Yapping handlers registered")
