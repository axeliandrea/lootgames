# lootgames/modules/yapping.py (debug + perbaikan poin)
import os, re, json
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= CONFIG ================= #
OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772
YAPPINGPOINT_DB = "storage/chat_points.json"
DEBUG = True
IGNORED_USERS = ["6946903915"]
MAX_POINT_PER_CHAT = 5
MILESTONE_INTERVAL = 100

# ================= UTILS ================= #
def log_debug(msg: str):
    if DEBUG:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[YAPPING][{timestamp}] {msg}")

def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            log_debug(f"⚠️ JSON rusak: {file_path}, membuat ulang")
            return {}
    return {}

def save_json(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log_debug(f"💾 Data disimpan ke {file_path}")

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
        log_debug(f"👤 User baru ditambahkan: {username} ({user_id})")
    else:
        points[user_id]["username"] = username
        points[user_id].setdefault("level", 0)
        points[user_id].setdefault("last_milestone", 0)

# Perbaikan: hitung semua huruf Unicode (isalpha)
def calculate_points_from_text(text: str) -> int:
    if not text:
        return 0
    clean_text = ''.join(ch for ch in text if ch.isalpha())  # include unicode letters
    log_debug(f"🔎 clean_text (letters only): '{clean_text}' len={len(clean_text)}")
    points = len(clean_text) // 5
    return min(points, MAX_POINT_PER_CHAT)

def add_points(points, user_id, username, amount):
    add_user_if_not_exist(points, user_id, username)
    points[str(user_id)]["points"] += amount
    log_debug(f"➕ {username} ({user_id}) +{amount} point | total: {points[str(user_id)]['points']}")

def update_points(user_id, points_change):
    points = load_points()
    user_id = str(user_id)
    if user_id not in points:
        points[user_id] = {"username": "Unknown", "points": 0, "level": 0, "last_milestone": 0}
    points[user_id]["points"] += points_change
    save_points(points)
    log_debug(f"🔄 Updated points for {user_id}: {points_change} change")

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
    log_debug(f"✅ Handler registered (Target group: {TARGET_GROUP})")

    # -- DEBUG: handler global untuk cek pesan apa yg bot terima (temporary) -- #
    @app.on_message(filters.text)
    async def debug_all_messages(client: Client, message: Message):
        try:
            chat_info = f"{getattr(message.chat,'id',None)} / {getattr(message.chat,'title', getattr(message.chat,'first_name',None))}"
            from_info = f"{getattr(message.from_user,'id',None)} / @{getattr(message.from_user,'username',None)}"
            log_debug(f"[DEBUG_ALL] chat={chat_info} from={from_info} text={repr(message.text)}")
        except Exception as e:
            log_debug(f"[DEBUG_ALL] error: {e}")

    # ----- AUTO POINT DARI CHAT DI GROUP ----- #
    @app.on_message(filters.chat(TARGET_GROUP) & filters.text)
    async def handle_chat(client: Client, message: Message):
        try:
            log_debug(f"📩 Pesan masuk (handler group) dari {message.from_user.id if message.from_user else 'UNKNOWN'}: {repr(message.text)}")
            user = message.from_user
            if not user:
                log_debug("⚠️ Pesan tanpa from_user, di-skip")
                return
            if str(user.id) in IGNORED_USERS:
                log_debug(f"🚫 User {user.id} di-ignore")
                return

            text = message.text or ""
            points = load_points()
            username = user.username or user.first_name or str(user.id)

            amount = calculate_points_from_text(text)
            log_debug(f"🧮 Kalkulasi poin untuk {username}: {amount}")
            if amount > 0:
                add_points(points, user.id, username, amount)

                # Check level up
                new_level = check_level_up(points[str(user.id)])
                if new_level != -1:
                    await message.reply_text(
                        f"🎉 Selamat {username}, naik ke level {new_level}! {get_badge(new_level)}"
                    )
                    log_debug(f"⬆️ {username} naik level ke {new_level}")

                # milestone
                total_points = points[str(user.id)]["points"]
                last_milestone = points[str(user.id)].get("last_milestone", 0)
                if total_points // MILESTONE_INTERVAL > last_milestone:
                    points[str(user.id)]["last_milestone"] = total_points // MILESTONE_INTERVAL
                    await message.reply_text(
                        f"🏆 {username} mencapai {total_points} poin!"
                    )
                    log_debug(f"🏅 {username} mencapai milestone {total_points} poin")

                save_points(points)
            else:
                log_debug("ℹ️ Tidak ada poin dari pesan ini")
        except Exception as e:
            log_debug(f"❌ Exception di handle_chat: {e}")

    # ----- COMMAND DEBUG: tampilkan chat id ----- #
    @app.on_message(filters.command("chatid", prefixes=["/", "."]))
    async def chatid_cmd(client: Client, message: Message):
        try:
            cid = message.chat.id
            uid = message.from_user.id if message.from_user else None
            await message.reply_text(f"chat.id = {cid}\nfrom.id = {uid}")
            log_debug(f"📢 /chatid dipanggil -> chat.id {cid}, from.id {uid}")
        except Exception as e:
            log_debug(f"❌ chatid_cmd error: {e}")

    # (lainnya: rank/leaderboard/resetyapping/cpc seperti sebelumnya)
    @app.on_message(filters.command("rank", prefixes=["/", "."]) & filters.chat(TARGET_GROUP))
    async def rank_cmd(client: Client, message: Message):
        points = load_points()
        user_data = points.get(str(message.from_user.id))
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
        log_debug("🗑️ Database poin yapping direset oleh OWNER")
