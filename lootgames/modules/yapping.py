# lootgames/modules/yapping.py
import os
import re
import json
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ---------------- CONFIG ---------------- #
OWNER_ID = 6395738130
TARGET_GROUP = -1002904817520
BOT_USERNAME = "gamesofloot_bot"

POINT_FILE = "storage/chat_points.json"
DAILY_POINT_FILE = "storage/daily_points.json"
DAILY_RESET_FILE = "storage/daily_reset.json"
DEBUG = True
IGNORED_USERS = ["6946903915"]

# ---------------- UTILS ---------------- #
def log_debug(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[DEBUG] {ts} - {msg}"
    print(line)

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- POINT SYSTEM ---------------- #
def load_points(): return load_json(POINT_FILE)
def save_points(data): save_json(POINT_FILE, data)
def load_daily(): 
    daily = load_json(DAILY_POINT_FILE)
    auto_reset_daily(daily)
    return daily
def save_daily(data): save_json(DAILY_POINT_FILE, data)

def add_user(points, user_id, username):
    user_id = str(user_id)
    if user_id not in points:
        points[user_id] = {"username": username, "points": 0, "level": 0, "last_milestone":0}
    else:
        points[user_id]["username"] = username
        points[user_id].setdefault("level",0)
        points[user_id].setdefault("last_milestone",0)

def add_points(user_id, username, amount=1):
    user_id = str(user_id)
    points = load_points()
    daily = load_daily()
    add_user(points, user_id, username)
    add_user(daily, user_id, username)
    points[user_id]["points"] += amount
    daily[user_id]["points"] = daily[user_id].get("points",0) + amount
    log_debug(f"{username} +{amount} point | total: {points[user_id]['points']}")
    save_points(points)
    save_daily(daily)

def auto_reset_daily(daily_points):
    reset_info = load_json(DAILY_RESET_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    if reset_info.get("last_reset","") != today:
        daily_points.clear()
        save_daily(daily_points)
        save_json(DAILY_RESET_FILE, {"last_reset": today})
        log_debug("✅ Daily points auto reset")

def calculate_points(text: str) -> int:
    # Hanya huruf, minimal 5 char = 1 point
    cleaned = re.sub(r"[^a-zA-Z]", "", text)
    length = len(cleaned)
    points = length // 5
    return min(points, 5)  # maksimal 5 per chat

# ---------------- LEADERBOARD ---------------- #
def generate_board(points, page=0, page_size=10):
    sorted_pts = sorted(points.items(), key=lambda x: x[1]["points"], reverse=True)
    start, end = page*page_size, (page+1)*page_size
    chunk = sorted_pts[start:end]
    if not chunk:
        return "Leaderboard kosong"
    text = "🏆 Leaderboard 🏆\n"
    for i,(uid,data) in enumerate(chunk,start=start+1):
        text += f"{i}. {data['username']} - {data['points']} points\n"
    return text

def board_keyboard(page, max_page):
    buttons = []
    if page>0: buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"board_{page-1}"))
    if page<max_page: buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"board_{page+1}"))
    rows = [buttons] if buttons else []
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="menu")])
    return InlineKeyboardMarkup(rows)

# ---------------- REGISTER ---------------- #
def register(app: Client):
    # Auto points handler
    @app.on_message(filters.chat(TARGET_GROUP) & ~filters.command())
    async def handle_message(client, message: Message):
        user = message.from_user
        if not user: return
        if str(user.id) in IGNORED_USERS: return
        text = message.text or ""
        if len(text) < 5: return
        pts = calculate_points(text)
        if pts < 1: return
        add_points(user.id, user.username or user.first_name, pts)

    # /mypoint
    @app.on_message(filters.command(["mypoint", f"mypoint@{BOT_USERNAME}"], prefixes="/"))
    async def mypoint(client, message: Message):
        uid = str(message.from_user.id)
        points = load_points()
        if uid not in points:
            await message.reply("Anda belum memiliki poin")
        else:
            data = points[uid]
            await message.reply(f"{data['username']} - {data['points']} points")

    # /board
    @app.on_message(filters.command(["board", f"board@{BOT_USERNAME}"], prefixes="/"))
    async def board(client, message: Message):
        points = load_points()
        text = generate_board(points)
        await message.reply(text)
