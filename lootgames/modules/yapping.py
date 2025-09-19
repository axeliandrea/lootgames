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
GIT_REPO_PATH = "/home/ubuntu/loot"
GIT_LOG_FILE = "storage/git_sync.log"
IGNORED_USERS = ["6946903915"]
DEBUG = True

# ---------------- UTILS ---------------- #
def log_debug(msg: str, to_file=True):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[DEBUG] {timestamp} - {msg}"
    print(line)
    if to_file:
        try:
            os.makedirs(os.path.dirname(GIT_LOG_FILE), exist_ok=True)
            with open(GIT_LOG_FILE, "a") as f:
                f.write(line + "\n")
        except Exception:
            print("[DEBUG] Gagal menulis log ke file.")

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
        print(f"[DEBUG] Data disimpan ke {file_path}: {data}")

# ---------------- POINTS ---------------- #
def load_points():
    return load_json(POINT_FILE)

def save_points(data):
    save_json(POINT_FILE, data)

def load_daily_points():
    daily_points = load_json(DAILY_POINT_FILE)
    auto_reset_daily_points(daily_points)
    return daily_points

def save_daily_points(data):
    save_json(DAILY_POINT_FILE, data)

def add_user_if_not_exist(points, user_id, username):
    user_id = str(user_id)
    if user_id not in points:
        points[user_id] = {"username": username, "points": 0, "level": 0, "last_milestone":0}
        if DEBUG: print(f"[DEBUG] User baru ditambahkan: {username} ({user_id})")
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
    points[user_id]["points"] += amount
    daily_points[user_id]["points"] = daily_points[user_id].get("points",0) + amount
    log_debug(f"{username} ({user_id}) +{amount} point | total: {points[user_id]['points']} | daily: {daily_points[user_id]['points']}")
    save_points(points)
    save_daily_points(daily_points)

def reset_daily_points():
    save_daily_points({})
    save_json(DAILY_RESET_FILE, {"last_reset": datetime.now().strftime("%Y-%m-%d")})
    log_debug("Daily points direset manual")

def auto_reset_daily_points(daily_points):
    reset_info = load_json(DAILY_RESET_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    last_reset = reset_info.get("last_reset", "")
    if last_reset != today:
        daily_points.clear()
        save_daily_points(daily_points)
        save_json(DAILY_RESET_FILE, {"last_reset": today})
        log_debug(f"Daily points direset otomatis: {today}")

# ---------------- LEVEL & BADGE ---------------- #
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
    elif level <= 9: return "🥉 ༺ᴠɪᴘ༻ 1"
    elif level <= 19: return "🥈 ༺ᴠɪᴘ༻ 2"
    elif level <= 29: return "🥇 ༺ᴠɪᴘ༻ 3"
    elif level <= 39: return "💎 ༺ᴠɪᴘ༻ 4"
    elif level <= 49: return "🔥 ༺ᴠɪᴘ༻ 5"
    elif level <= 59: return "👑 ༺ᴠɪᴘ༻ 6"
    elif level <= 69: return "🌌 ༺ᴠɪᴘ༻ 7"
    elif level <= 79: return "⚡ ༺ᴠɪᴘ༻ 8"
    elif level <= 89: return "🐉 ༺ᴠɪᴘ༻ 9"
    else: return "🏆 ༺ᴠᴠɪᴘ༻ MAX"

def clean_text(text: str) -> str:
    text = re.sub(r"[^a-zA-Z ]", "", text or "")
    cleaned = ""
    for char in text:
        if not cleaned or cleaned[-1] != char:
            cleaned += char
    return cleaned.lower()

def calculate_points(text: str) -> tuple[int,str]:
    cleaned = clean_text(text)
    length = len(cleaned.replace(" ", ""))
    return length // 5, cleaned

# ---------------- LEADERBOARD ---------------- #
def generate_leaderboard_page(points: dict, page: int, page_size: int = 10) -> str:
    sorted_points = sorted(points.items(), key=lambda x: x[1].get("points", 0), reverse=True)
    start = page * page_size
    end = start + page_size
    chunk = sorted_points[start:end]
    if not chunk:
        return "```\n📋 Leaderboard kosong.\n```"
    text = "```\n"
    text += f"🏆 Yapping board (Page {page+1}) 🏆\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for i, (user_id, data) in enumerate(chunk, start=start+1):
        username = data.get("username", "Unknown")
        point = data.get("points", 0)
        level = data.get("level", 0)
        badge = get_badge(level)
        text += f"{i}. {username}\n   💠 Level : {level} {badge}\n   ⭐ Yapping Point : {point:,}\n━━━━━━━━━━━━━━━━━━━━━━\n"
    text += "```"
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
async def git_auto_sync():
    while True:
        await asyncio.sleep(1800)
        try:
            if not os.path.exists(GIT_REPO_PATH):
                log_debug(f"❌ Path repo Git tidak ditemukan: {GIT_REPO_PATH}")
                continue
            os.chdir(GIT_REPO_PATH)
            status = os.popen("git status --porcelain").read().strip()
            if not status:
                log_debug("✅ Tidak ada perubahan, skip git commit/push")
                continue
            os.system("git pull --rebase")
            os.system("git add storage/chat_points.json storage/daily_points.json")
            commit_msg = f'Auto-save chat points {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            os.system(f'git commit -m "{commit_msg}" || true')
            os.system("git push || true")
            log_debug("✅ Chat points berhasil di-sync ke GitHub")
        except Exception as e:
            log_debug(f"❌ Gagal auto sync chat points: {e}")

async def auto_midnight_reset():
    log_debug("🔄 Background midnight reset task started")
    last_reset_date = datetime.now().strftime("%Y-%m-%d")
    while True:
        try:
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            if today != last_reset_date and now.hour == 0:
                reset_daily_points()
                last_reset_date = today
                log_debug(f"✅ Daily points auto reset at {now.strftime('%Y-%m-%d %H:%M:%S')}")
                await asyncio.sleep(5)
            await asyncio.sleep(1)
        except Exception as e:
            log_debug(f"❌ Error di auto_midnight_reset: {e}")
            await asyncio.sleep(5)

# ---------------- REGISTER ---------------- #
def register(bot: Client):

    # Auto point chat handler
    @bot.on_message(filters.chat(TARGET_GROUP) & ~filters.command())
    async def auto_point(client: Client, message: Message):
        content = (message.text or message.caption or "").strip()
        user = message.from_user
        if not user: return
        user_id = str(user.id)
        username = user.username or user.first_name or "Unknown"
        if user_id in IGNORED_USERS: return
        if DEBUG:
            log_debug(f"Message detected: {content} from {username}")
        if len(content.replace(" ","")) < 5: return
        points_to_add, _ = calculate_points(content)
        points_to_add = min(points_to_add,5)
        if points_to_add < 1: return
        add_points(user_id, username, points_to_add)

        # Milestone
        points = load_points()
        last_milestone = points[user_id].get("last_milestone",0)
        new_index = points[user_id]["points"]//100
        last_index = last_milestone//100
        if new_index>last_index and new_index>0:
            points[user_id]["last_milestone"] = new_index*100
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

    # /mypoint command
    @bot.on_message(filters.command(commands=["mypoint", f"mypoint@{BOT_USERNAME}"], prefixes="/"))
    async def mypoint_handler(client, message: Message):
        user_id = str(message.from_user.id)
        points = load_points()
        if user_id not in points:
            await message.reply("📌 Anda belum memiliki poin.")
        else:
            data = points[user_id]
            await message.reply(f"💠 {data['username']} - {data['points']} Yapping Points | Level {data['level']} {get_badge(data['level'])}")

    # /board command
    @bot.on_message(filters.command(commands=["board", f"board@{BOT_USERNAME}"], prefixes="/"))
    async def board_handler(client, message: Message):
        points = load_points()
        text = generate_leaderboard_page(points,0)
        max_page = max(0,(len(points)-1)//10)
        keyboard = leaderboard_keyboard(0,max_page)
        await message.reply_text(text, reply_markup=keyboard)

    @bot.on_callback_query(filters.regex(r"^leaderboard_\d+$"))
    async def leaderboard_callback(client, cq: CallbackQuery):
        points = load_points()
        page = int(cq.data.split("_")[1])
        max_page = max(0,(len(points)-1)//10)
        text = generate_leaderboard_page(points,page)
        keyboard = leaderboard_keyboard(page,max_page)
        await cq.answer()
        await cq.message.edit_text(text, reply_markup=keyboard)

    # Owner reset daily
    @bot.on_message(filters.user(OWNER_ID) & filters.command(commands=["resetchatdaily"], prefixes="."))
    async def reset_daily_command(client, message: Message):
        reset_daily_points()
        await message.reply("✅ Daily points berhasil direset manual")

    # Owner edit points
    @bot.on_message(filters.user(OWNER_ID) & filters.command(commands=["editp"], prefixes="."))
    async def edit_point_command(client, message: Message):
        if len(message.command)<3:
            await message.reply("Usage: .editp @username <jumlah>")
            return
        target_username = message.command[1].lstrip("@")
        try:
            jumlah = int(message.command[2])
        except:
            await message.reply("Jumlah harus angka!")
            return
        points = load_points()
        for uid,data in points.items():
            if (data.get("username") or "").lower()==target_username.lower():
                data["points"] = jumlah
                save_points(points)
                await message.reply(f"✅ Poin {target_username} diubah menjadi {jumlah}")
                return
        await message.reply("❌ Username tidak ditemukan")

    # Background tasks
    try:
        bot.loop.create_task(auto_midnight_reset())
        bot.loop.create_task(git_auto_sync())
        log_debug("🔧 Background tasks registered")
    except Exception as e:
        log_debug(f"❌ Gagal register background tasks: {e}")
