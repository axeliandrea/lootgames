# chat_point.py
import os
import json
import re
import asyncio
from datetime import datetime
from pyrogram import filters
from pyrogram.types import Message

from .utils import (
    load_points,
    save_points,
    load_daily_points,
    save_daily_points,
    add_user_if_not_exist,
    reset_daily_points,
)

# ---------------- CONFIG ---------------- #
POINT_FILE = "storage/chat_points.json"
DAILY_POINT_FILE = "storage/daily_points.json"
GIT_REPO_PATH = "/home/ubuntu/loot"
GIT_LOG_FILE = "storage/git_sync.log"

OWNER_ID = 6395738130
TARGET_GROUP = -1002904817520
DEBUG = True
IGNORED_USERS = ["6946903915"]  # Userbot ID yang tidak dihitung poin

# ---------------- HELPERS / LOG ---------------- #
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
    return length // 5, cleaned

# ---------------- LEVEL SYSTEM ---------------- #
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

# ---------------- GIT AUTO SYNC (background) ---------------- #
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

# ---------------- MIDNIGHT AUTO RESET (background) ---------------- #
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

# ---------------- HANDLER REGISTRATION ---------------- #
def register_commands(bot):
    """
    Daftarkan semua handler ke bot. Panggil fungsi ini dari __main__.py setelah Client dibuat.
    """

    # ---------------- auto point handler ---------------- #
    @bot.on_message(
        filters.chat(TARGET_GROUP) &
        ~filters.command(["mypoint", "resetchatpoint", "kepoin", "noyap", "scanpoint", "ya"], prefixes=[".", "/"])
    )
    async def auto_point(client, message: Message):
        content = (message.text or message.caption or "").strip()
        user = message.from_user
        if not user:
            return
        user_id = str(user.id)
        username = user.username or user.first_name or "Unknown"
        if user_id in IGNORED_USERS:
            log_debug(f"{username} termasuk userbot, skip point")
            return
        if content.startswith(("/kepo", ".kepo")):
            return
        if len(content) < 5:
            log_debug(f"{username} pesan <5 karakter, skip")
            return
        points_to_add, cleaned_text = calculate_points(content)
        points_to_add = min(points_to_add, 5)
        if points_to_add < 1:
            log_debug(f"{username} pesan setelah clean <5 huruf, skip")
            return
        points = load_points()
        daily_points = load_daily_points()
        add_user_if_not_exist(points, user_id, username)
        add_user_if_not_exist(daily_points, user_id, username)
        prev_points = points[user_id].get("points", 0)
        points[user_id]["points"] = prev_points + points_to_add
        daily_points[user_id]["points"] = daily_points[user_id].get("points", 0) + points_to_add
        new_total = points[user_id]["points"]
        new_daily_total = daily_points[user_id]["points"]
        # Milestone notif
        last_milestone = points[user_id].get("last_milestone", 0)
        last_index = last_milestone // 100
        new_index = new_total // 100
        if new_index > last_index and new_index > 0:
            milestone_value = new_index * 100
            try:
                await message.reply(
                    f"```\n"
                    f"🎉 Congrats {username}! Reached {milestone_value:,} points 💗\n"
                    f"⭐ Total poin sekarang: {new_total:,}\n"
                    f"💠 Level: {points[user_id].get('level', 0)} {get_badge(points[user_id].get('level', 0))}\n"
                    f"```",
                    quote=True
                )
            except Exception as e:
                log_debug(f"Gagal kirim milestone message: {e}")
            finally:
                points[user_id]["last_milestone"] = milestone_value
        # Level up notif
        new_level = check_level_up(points[user_id])
        if new_level != -1:
            try:
                notif = await message.reply(
                    f"🎉 Selamat {username}, kamu naik ke level {new_level}! {get_badge(new_level)}",
                    quote=True
                )
                try:
                    await notif.pin(disable_notification=True)
                except Exception as e:
                    log_debug(f"Gagal pin pesan level up: {e}")
            except Exception as e:
                log_debug(f"Gagal kirim level up notif: {e}")
        save_points(points)
        save_daily_points(daily_points)
        log_debug(
            f"{username} chat valid → '{content}' | "
            f"cleaned: '{cleaned_text}' | "
            f"+{points_to_add} point | total: {new_total} | daily: {new_daily_total}"
        )

    # ---------------- .mypoint command ---------------- #
    @bot.on_message(filters.command(["mypoint"], prefixes=["."]) & filters.chat(TARGET_GROUP))
    async def mypoint_cmd(client, message: Message):
        points = load_points()
        daily_points = load_daily_points()
        user_id = str(message.from_user.id)
        username = message.from_user.username or message.from_user.first_name or "Unknown"
        add_user_if_not_exist(points, user_id, username)
        add_user_if_not_exist(daily_points, user_id, username)
        save_points(points)
        save_daily_points(daily_points)
        user_points = points[user_id].get("points", 0)
        user_daily = daily_points[user_id].get("points", 0)
        user_level = points[user_id].get("level", 0)
        badge = get_badge(user_level)
        if user_level < 99:
            next_req = LEVEL_EXP.get(user_level, user_points)
            remaining = next_req - user_points
            info = f"📈 {remaining:,} point lagi untuk naik ke level {user_level + 1}."
        else:
            info = "🏆 Kamu sudah mencapai level tertinggi!"
        await message.reply(
            f"💰 Total points: {user_points:,}\n"
            f"⭐ Daily points: {user_daily:,}\n"
            f"💠 Level: {user_level} {badge}\n"
            f"{info}"
        )

    # ---------------- reset daily manual (owner) ---------------- #
    @bot.on_message(filters.command(["resetchatdaily", "resetdaily"], prefixes=["."]) & filters.user(OWNER_ID))
    async def owner_reset_daily(client, message: Message):
        reset_daily_points()
        await message.reply("✅ Semua daily points sudah di-reset oleh owner.")

    # ---------------- manual refresh milestone (owner) ---------------- #
    @bot.on_message(filters.command(["refreshmilestone", "refresh"], prefixes=["."]) & filters.user(OWNER_ID))
    async def owner_refresh_milestone(client, message: Message):
        points = load_points()
        updated_count = 0
        for user_id, data in points.items():
            total = data.get("points", 0)
            milestone_value = (total // 100) * 100 if total >= 100 else 0
            if data.get("last_milestone", 0) != milestone_value:
                data["last_milestone"] = milestone_value
                updated_count += 1
        save_points(points)
        await message.reply(
            f"✅ Milestone untuk {updated_count} user berhasil di-refresh.\n"
            f"(command: .refresh / .refreshmilestone)"
        )

    # ---------------- .scanpoint command (owner only) ---------------- #
    @bot.on_message(filters.command(["scanpoint"], prefixes=["."]))
    async def owner_scanpoint(client, message: Message):
        if message.from_user.id != OWNER_ID:
            await message.reply("❌ Hanya owner yang bisa menggunakan command ini.")
            return

        points = load_points()
        daily_points = load_daily_points()

        msg = await message.reply("🔄 Sedang scan members group, mohon tunggu...")

        # Ambil semua member group
        members = []
        try:
            async for m in client.get_chat_members(TARGET_GROUP):
                if m.user:
                    members.append(m.user.id)
        except Exception as e:
            await msg.edit(f"❌ Gagal ambil member group: {e}")
            return

        current_ids = [str(uid) for uid in members]

        removed_users = []
        for user_id in list(points.keys()):
            if user_id not in current_ids and user_id not in IGNORED_USERS and user_id != "__last_reset__":
                removed_users.append(user_id)
                points.pop(user_id, None)
                daily_points.pop(user_id, None)

        save_points(points)
        save_daily_points(daily_points)

        result_text = (
            f"✅ Scan selesai.\n"
            f"🔹 Total users dihapus: {len(removed_users)}\n"
            f"🔹 User IDs dihapus: {', '.join(removed_users) if removed_users else 'Tidak ada'}"
        )
        result_msg = await msg.edit(result_text)

        # Auto delete setelah 2 detik
        await asyncio.sleep(2)
        try:
            await result_msg.delete()
        except Exception:
            pass  # jika gagal delete jangan crash

    # ---------------- start background tasks ---------------- #
    try:
        bot.loop.create_task(auto_midnight_reset())
        bot.loop.create_task(git_auto_sync())
        log_debug("🔧 Background tasks registered (midnight reset, git auto sync)")
    except Exception as e:
        log_debug(f"❌ Gagal register background tasks: {e}")

# akhir register_commands
