# lootgames/modules/yapping.py
import os
import json
import traceback
from pyrogram import filters
from pyrogram.types import Message
from pyrogram import Client

# ================= CONFIG ================= #
GROUP_ID = -1002904817520  # Ganti sesuai grup target
POINT_FILE = "lootgames/modules/yapping_point.json"

# ================= INIT DATA ================= #
point_data = {}
if not os.path.exists(POINT_FILE):
    # Buat file baru
    try:
        with open(POINT_FILE, "w") as f:
            json.dump({}, f, indent=2)
        print(f"[SUPERFINAL] Created new point file: {POINT_FILE}")
    except Exception as e:
        print(f"[SUPERFINAL] Failed to create point file: {e}")

# Load existing data
try:
    with open(POINT_FILE, "r") as f:
        point_data = json.load(f)
    print(f"[SUPERFINAL] Loaded point_data from {POINT_FILE}")
except Exception as e:
    print(f"[SUPERFINAL] Failed to load point_data: {e}")
    point_data = {}

def save_points():
    """Simpan point ke file JSON"""
    try:
        with open(POINT_FILE, "w") as f:
            json.dump(point_data, f, indent=2)
        print(f"[SUPERFINAL] Saved point_data to {POINT_FILE}")
    except Exception as e:
        print(f"[SUPERFINAL] Failed to save point_data: {e}")

def load_points():
    """Load point dari file dan kembalikan dictionary"""
    global point_data
    try:
        if os.path.exists(POINT_FILE):
            with open(POINT_FILE, "r") as f:
                point_data = json.load(f)
            print(f"[SUPERFINAL] Loaded point_data from {POINT_FILE}")
        else:
            point_data = {}
            with open(POINT_FILE, "w") as f:
                json.dump(point_data, f, indent=2)
            print(f"[SUPERFINAL] Point file not found. Created new file.")
    except Exception as e:
        print(f"[SUPERFINAL] Error loading points: {e}")
        traceback.print_exc()
    return point_data

# ================= REGISTER HANDLER ================= #
def register(app: Client):
    print("[SUPERFINAL] Registering yapping_point handler...")

    @app.on_message(filters.chat(GROUP_ID) & filters.text & ~filters.private)
    async def yapping_point(client: Client, message: Message):
        try:
            user = message.from_user
            if not user:
                print("[SUPERFINAL] Message has no from_user, skipping")
                return

            text = message.text.strip()
            if len(text) < 5:
                print(f"[SUPERFINAL] Message too short ({len(text)} chars), skipping")
                return  # minimal 5 karakter

            user_id = str(user.id)
            if user_id not in point_data:
                point_data[user_id] = {"name": user.first_name, "point": 0}

            point_data[user_id]["point"] += 1
            save_points()

            print(f"[SUPERFINAL] {user.first_name} ({user.id}) chat: '{text}' → total point: {point_data[user_id]['point']}")
        except Exception as e:
            print(f"[SUPERFINAL] Exception in yapping_point: {e}")
            traceback.print_exc()

    @app.on_message(filters.command("point") & ~filters.private)
    async def check_point(client: Client, message: Message):
        try:
            args = message.text.split()
            if len(args) == 1:
                user_id = str(message.from_user.id)
                pts = point_data.get(user_id, {"point":0})["point"]
                await message.reply_text(f"Total Chat Pointmu: {pts}")
            elif len(args) == 2:
                username = args[1].replace("@", "")
                found = None
                for uid, data in point_data.items():
                    if data.get("name") == username:
                        found = data
                        break
                if found:
                    await message.reply_text(f"Total Chat Point {username}: {found['point']}")
                else:
                    await message.reply_text("User tidak ditemukan.")
            print(f"[SUPERFINAL] /point command processed by {message.from_user.first_name}")
        except Exception as e:
            print(f"[SUPERFINAL] Exception in check_point: {e}")
            traceback.print_exc()

    @app.on_message(filters.command("board") & ~filters.private)
    async def leaderboard(client: Client, message: Message):
        try:
            if not point_data:
                await message.reply_text("Leaderboard masih kosong.")
                print("[SUPERFINAL] Leaderboard empty")
                return

            sorted_board = sorted(point_data.items(), key=lambda x: x[1]["point"], reverse=True)
            text = "🏆 Leaderboard Chat Points 🏆\n\n"
            for i, (uid, data) in enumerate(sorted_board[:10], 1):
                text += f"{i}. {data['name']} → {data['point']} point\n"
            await message.reply_text(text)
            print(f"[SUPERFINAL] Leaderboard sent by {message.from_user.first_name}")
        except Exception as e:
            print(f"[SUPERFINAL] Exception in leaderboard: {e}")
            traceback.print_exc()

    print("[SUPERFINAL] yapping.py handlers registered successfully")

# ================= AUTO REGISTER ================= #
try:
    from lootgames.__main__ import app
except ImportError:
    print("[SUPERFINAL] app not found, skip auto-register")
else:
    register(app)
