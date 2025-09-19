# lootgames/modules/yapping.py
import os
import json
import traceback
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= CONFIG ================= #
GROUP_ID = -1002904817520  # ID grup target
POINT_FILE = "lootgames/modules/yapping_point.json"

# ================= INIT DATA ================= #
point_data = {}

if not os.path.exists(POINT_FILE):
    with open(POINT_FILE, "w") as f:
        json.dump({}, f, indent=2)
    print(f"[YAPPING] Created new point file: {POINT_FILE}")

try:
    with open(POINT_FILE, "r") as f:
        point_data = json.load(f)
    print(f"[YAPPING] Loaded point_data from {POINT_FILE}")
except Exception as e:
    print(f"[YAPPING] Failed to load point_data: {e}")
    point_data = {}

def save_points():
    try:
        with open(POINT_FILE, "w") as f:
            json.dump(point_data, f, indent=2)
        print(f"[YAPPING] Saved point_data to {POINT_FILE}")
    except Exception as e:
        print(f"[YAPPING] Failed to save point_data: {e}")

def load_points():
    global point_data
    try:
        if os.path.exists(POINT_FILE):
            with open(POINT_FILE, "r") as f:
                point_data = json.load(f)
        else:
            point_data = {}
            with open(POINT_FILE, "w") as f:
                json.dump(point_data, f, indent=2)
    except Exception as e:
        print(f"[YAPPING] Error loading points: {e}")
        traceback.print_exc()
    return point_data

# ================= REGISTER HANDLER ================= #
def register(app: Client):
    print("[YAPPING] Registering handlers...")

    # ---------------- CHAT POINT ---------------- #
    @app.on_message(filters.text & ~filters.private)
    async def yapping_point(client: Client, message: Message):
        try:
            user = message.from_user
            chat_id = message.chat.id
            text = message.text.strip()
            
            # Log semua pesan masuk
            print(f"[SUPERDEBUG] Message from {user.first_name if user else 'Unknown'} ({user.id if user else 'N/A'}) in chat {chat_id}: '{text}'")

            # Hanya grup target (opsional, bisa comment untuk debug)
            if chat_id != GROUP_ID:
                return

            # Cek panjang pesan ≥5
            if len(text) >= 5 and user:
                user_id = str(user.id)
                if user_id not in point_data:
                    point_data[user_id] = {"username": user.first_name, "points": 0}
                point_data[user_id]["points"] += 1
                save_points()
                print(f"[YAPPING-POINT] {user.first_name} → total points: {point_data[user_id]['points']}")
        except Exception as e:
            print(f"[YAPPING] Exception: {e}")
            traceback.print_exc()

    # ---------------- COMMAND CHECK POINT ---------------- #
    @app.on_message(filters.command("point") & ~filters.private)
    async def check_point(client: Client, message: Message):
        try:
            args = message.text.split()
            if len(args) == 1:
                user_id = str(message.from_user.id)
                pts = point_data.get(user_id, {"points":0})["points"]
                await message.reply_text(f"Total Chat Pointmu: {pts}")
            elif len(args) == 2:
                username = args[1].replace("@","")
                found = None
                for uid, data in point_data.items():
                    if data.get("username") == username:
                        found = data
                        break
                if found:
                    await message.reply_text(f"Total Chat Point {username}: {found['points']}")
                else:
                    await message.reply_text("User tidak ditemukan.")
        except Exception as e:
            print(f"[YAPPING] Exception in check_point: {e}")
            traceback.print_exc()

    # ---------------- COMMAND LEADERBOARD ---------------- #
    @app.on_message(filters.command("board") & ~filters.private)
    async def leaderboard(client: Client, message: Message):
        try:
            if not point_data:
                await message.reply_text("Leaderboard masih kosong.")
                return

            sorted_board = sorted(point_data.items(), key=lambda x: x[1]["points"], reverse=True)
            text = "🏆 Leaderboard Chat Points 🏆\n\n"
            for i, (uid, data) in enumerate(sorted_board[:10],1):
                text += f"{i}. {data['username']} → {data['points']} pts\n"
            await message.reply_text(text)
        except Exception as e:
            print(f"[YAPPING] Exception in leaderboard: {e}")
            traceback.print_exc()

    print("[YAPPING] Handlers registered successfully")
