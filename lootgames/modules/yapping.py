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
BOT_USERNAME = "justforfvckingfun_bot"
POINT_FILE = "storage/chat_points.json"
DAILY_POINT_FILE = "storage/daily_points.json"
DAILY_RESET_FILE = "storage/daily_reset.json"
DEBUG = True
IGNORED_USERS = ["6946903915"]

# ---------------- UTILS ---------------- #
def log_debug(msg: str):
    if DEBUG:
        print(f"[DEBUG {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            log_debug(f"JSON rusak: {file_path}, skip load")
            return None
    return {}

def save_json(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- POINTS ---------------- #
def load_points():
    data = load_json(POINT_FILE)
    return data if data else {}

def save_points(data):
    save_json(POINT_FILE, data)

def load_daily_points():
    daily_points = load_json(DAILY_POINT_FILE) or {}
    auto_reset_daily_points(daily_points)
    return daily_points

def save_daily_points(data):
    save_json(DAILY_POINT_FILE, data)

def add_user_if_not_exist(points, user_id, username):
    user_id = str(user_id)
    if user_id not in points:
        points[user_id] = {"username": username, "points": 0, "level": 0, "last_milestone": 0}
        log_debug(f"User baru ditambahkan: {username} ({user_id})")
    else:
        points[user_id]["username"] = username
        points[user_id].setdefault("level", 0)
        points[user_id].setdefault("last_milestone", 0)

def add_points(user_id, username, amount=1):
    user_id = str(user_id)
    points = load_points()
    daily_points = load_daily_points()
    add_user_if_not_exist(points, user_id, username)
    add_user_if_not_exist(daily_points, user_id, username)
    old_total = points[user_id]["points"]
    points[user_id]["points"] += amount
    daily_points[user_id]["points"] = daily_points[user_id].get("points", 0) + amount
    log_debug(f"{username}: {old_total} + {amount} = {points[user_id]['points']}")
    save_points(points)
    save_daily_points(daily_points)

def reset_daily_points():
    save_daily_points({})
    save_json(DAILY_RESET_FILE, {"last_reset": datetime.now().strftime("%Y-%m-%d")})
    log_debug("Daily points direset manual")

def auto_reset_daily_points(daily_points):
    reset_info = load_json(DAILY_RESET_FILE) or {}
    today = datetime.now().strftime("%Y-%m-%d")
    last_reset = reset_info.get("last_reset", "")
    if last_reset != today:
        daily_points.clear()
        save_daily_points(daily_points)
        save_json(DAILY_RESET_FILE, {"last_reset": today})
        log_debug(f"Daily points direset otomatis: {today}")

# ---------------- LEVEL ---------------- #
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
    badges = [
        "⬜ NOOB","🥉 ༺ᴠɪᴘ༻ 1","🥈 ༺ᴠɪᴘ༻ 2","🥇 ༺ᴠɪᴘ༻ 3","💎 ༺ᴠɪᴘ༻ 4",
        "🔥 ༺ᴠɪᴘ༻ 5","👑 ༺ᴠɪᴘ༻ 6","🌌 ༺ᴠɪᴘ༻ 7","⚡ ༺ᴠɪᴘ༻ 8","🐉 ༺ᴠɪᴘ༻ 9","🏆 ༺ᴠᴠɪᴘ༻ MAX"
    ]
    if level <= 0: return badges[0]
    elif level <= 9: return badges[1]
    elif level <= 19: return badges[2]
    elif level <= 29: return badges[3]
    elif level <= 39: return badges[4]
    elif level <= 49: return badges[5]
    elif level <= 59: return badges[6]
    elif level <= 69: return badges[7]
    elif level <= 79: return badges[8]
    elif level <= 89: return badges[9]
    else: return badges[10]

def clean_text(text: str) -> str:
    text = re.sub(r"[^a-zA-Z ]", "", text or "")
    cleaned = ""
    for char in text:
        if not cleaned or cleaned[-1] != char:
            cleaned += char
    return cleaned.lower()

def calculate_points(text: str) -> tuple[int, str]:
    cleaned = clean_text(text)
    length = len(cleaned.replace(" ", ""))
    points = length // 5
    return points, cleaned

# ---------------- LEADERBOARD ---------------- #
def generate_leaderboard_page(points: dict, page: int, page_size: int = 10) -> str:
    sorted_points = sorted(points.items(), key=lambda x: x[1].get("points", 0), reverse=True)
    start = page * page_size
    end = start + page_size
    chunk = sorted_points[start:end]
    if not chunk:
        return "📋 Leaderboard kosong."
    text = f"🏆 Yapping board (Page {page+1}) 🏆\n\n"
    for i, (uid, data) in enumerate(chunk, start=start+1):
        username = data.get("username", "Unknown")
        point = data.get("points", 0)
        level = data.get("level", 0)
        badge = get_badge(level)
        text += f"{i}. {username} | Level {level} {badge} | Points {point}\n"
    return text

def leaderboard_keyboard(page: int, max_page: int) -> InlineKeyboardMarkup:
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"leaderboard_{page-1}"))
    if page < max_page:
        buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"leaderboard_{page+1}"))
    rows = [buttons] if buttons else []
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="menu")])
    return InlineKeyboardMarkup(rows)

# ---------------- BACKGROUND TASKS ---------------- #
async def auto_midnight_reset():
    last_reset_date = datetime.now().strftime("%Y-%m-%d")
    while True:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        if today != last_reset_date and now.hour == 0:
            reset_daily_points()
            last_reset_date = today
            log_debug(f"Daily points auto reset at {now}")
            await asyncio.sleep(5)
        await asyncio.sleep(1)

# ---------------- REGISTER COMMANDS ---------------- #
def register(bot: Client):

    # Auto point handler
    @bot.on_message(filters.group)
    async def auto_point(client, message: Message):
        user = message.from_user
        if not user:
            log_debug("Message tanpa user, skip")
            return
        if str(user.id) in IGNORED_USERS:
            log_debug(f"User {user.id} di-ignore")
            return

        user_id = str(user.id)
        username = user.username or user.first_name or "Unknown"
        content = (message.text or message.caption or "").strip()

        log_debug(f"Memproses pesan dari {username}: '{content}'")

        if len(content.replace(" ", "")) < 5:
            log_debug(f"Pesan terlalu pendek, skip")
            return

        points_to_add, cleaned_text = calculate_points(content)
        log_debug(f"Cleaned: '{cleaned_text}', chars: {len(cleaned_text.replace(' ', ''))}, points: {points_to_add}")

        if points_to_add < 1:
            log_debug("Poin <1, skip")
            return

        add_points(user_id, username, points_to_add)
        log_debug(f"{username} ditambahkan {points_to_add} point")

        # Milestone
        points = load_points()
        last_milestone = points[user_id].get("last_milestone", 0)
        new_index = points[user_id]["points"] // 100
        last_index = last_milestone // 100
        if new_index > last_index and new_index > 0:
            points[user_id]["last_milestone"] = new_index * 100
            save_points(points)
            try:
                await message.reply(f"🎉 Congrats {username}! Reached {new_index*100} points 💗", quote=True)
            except: pass

        # Level up
        new_level = check_level_up(points[user_id])
        if new_level != -1:
            save_points(points)
            try:
                await message.reply(f"🎉 Selamat {username}, naik level {new_level}! {get_badge(new_level)}", quote=True)
            except: pass

    # /mypoint
    @bot.on_message(filters.command(["mypoint", f"mypoint@{BOT_USERNAME}"]))
    async def mypoint_handler(client, message: Message):
        user_id = str(message.from_user.id)
        points = load_points()
        if user_id not in points:
            await message.reply("📌 Anda belum memiliki poin.")
        else:
            data = points[user_id]
            await message.reply(f"{data['username']} - {data['points']} Points | Level {data['level']} {get_badge(data['level'])}")

    # /board
    @bot.on_message(filters.command(["board", f"leaderboard@{BOT_USERNAME}"]))
    async def board_handler(client, message: Message):
        points = load_points()
        text = generate_leaderboard_page(points, 0)
        max_page = max(0, (len(points)-1)//10)
        keyboard = leaderboard_keyboard(0, max_page)
        await message.reply_text(text, reply_markup=keyboard)

    @bot.on_callback_query(filters.regex(r"^leaderboard_\d+$"))
    async def leaderboard_callback(client, cq: CallbackQuery):
        points = load_points()
        page = int(cq.data.split("_")[1])
        max_page = max(0, (len(points)-1)//10)
        text = generate_leaderboard_page(points, page)
        keyboard = leaderboard_keyboard(page, max_page)
        await cq.answer()
        await cq.message.edit_text(text, reply_markup=keyboard)

    # Background tasks
    try:
        bot.loop.create_task(auto_midnight_reset())
        log_debug("Background tasks registered")
    except Exception as e:
        log_debug(f"Gagal register background tasks: {e}")
