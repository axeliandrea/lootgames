# lootgames/modules/yapping.py
import os
import json
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= CONFIG ================= #
POINT_FILE = "storage/chat_points.json"
TARGET_GROUP = -1002904817520  # ganti sesuai grup chat
DEBUG = True

# ================= INIT DATA ================= #
if not os.path.exists("storage"):
    os.makedirs("storage")

if not os.path.exists(POINT_FILE):
    with open(POINT_FILE, "w") as f:
        json.dump({}, f, indent=2)

points_data = {}
try:
    with open(POINT_FILE, "r") as f:
        points_data = json.load(f)
except Exception:
    points_data = {}

# ================= UTILITY ================= #
def load_points():
    global points_data
    try:
        with open(POINT_FILE, "r") as f:
            points_data = json.load(f)
    except Exception as e:
        print(f"[LOAD_POINTS] Error: {e}")
    return points_data

def save_points():
    global points_data
    try:
        with open(POINT_FILE, "w") as f:
            json.dump(points_data, f, indent=2)
    except Exception as e:
        print(f"[SAVE_POINTS] Error: {e}")

# ================= REGISTER HANDLER ================= #
def register(app: Client):

    # ----- CHAT POINT HANDLER ----- #
    @app.on_message(filters.chat(TARGET_GROUP) & filters.text & ~filters.private)
    async def chat_point_handler(client: Client, message: Message):
        global points_data
        user = message.from_user
        if not user:
            return

        text = message.text.strip()
        if DEBUG:
            print(f"[CHAT LOG] {user.first_name} ({user.id}): '{text}'")

        if len(text) >= 5:
            points_data = load_points()  # selalu reload dari file
            user_id = str(user.id)
            username = user.username or user.first_name or "Unknown"
            if user_id not in points_data:
                points_data[user_id] = {"username": username, "points": 0}
            points_data[user_id]["points"] += 1
            save_points()
            if DEBUG:
                print(f"[POINT] {username} → total points: {points_data[user_id]['points']}")

    # ----- .point COMMAND ----- #
    @app.on_message(filters.command("point", prefixes=["."]) & filters.chat(TARGET_GROUP))
    async def point_cmd(client: Client, message: Message):
        points_data = load_points()
        args = message.text.split()
        if len(args) == 1:
            # cek poin sendiri
            user_id = str(message.from_user.id)
            pts = points_data.get(user_id, {"points": 0})["points"]
            await message.reply_text(f"Total Chat Pointmu: {pts}")
        elif len(args) == 2:
            # cek poin orang lain
            username = args[1].replace("@","")
            found = None
            for uid, data in points_data.items():
                if data.get("username") == username:
                    found = data
                    break
            if found:
                await message.reply_text(f"Total Chat Point {username}: {found['points']}")
            else:
                await message.reply_text("User tidak ditemukan.")

    # ----- .board COMMAND ----- #
    @app.on_message(filters.command("board", prefixes=["."]) & filters.chat(TARGET_GROUP))
    async def board_cmd(client: Client, message: Message):
        points_data = load_points()
        if not points_data:
            await message.reply_text("Leaderboard masih kosong.")
            return
        sorted_board = sorted(points_data.items(), key=lambda x: x[1]["points"], reverse=True)
        text = "🏆 Leaderboard Chat Points 🏆\n\n"
        for i, (uid, data) in enumerate(sorted_board[:10],1):
            text += f"{i}. {data['username']} → {data['points']} pts\n"
        await message.reply_text(text)
