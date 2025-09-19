# lootgames/modules/yapping.py
import os
import json
import traceback
from pyrogram import filters, Client
from pyrogram.types import Message

# ================= CONFIG ================= #
GROUP_ID = -1002904817520  # Ganti sesuai grup target
POINT_FILE = "lootgames/modules/yapping_point.json"

# ================= INIT DATA ================= #
point_data = {}

# Buat file baru jika belum ada
if not os.path.exists(POINT_FILE):
    try:
        with open(POINT_FILE, "w") as f:
            json.dump({}, f, indent=2)
        print(f"[YAPPING] Created new point file: {POINT_FILE}")
    except Exception as e:
        print(f"[YAPPING] Failed to create point file: {e}")

# Load data JSON
try:
    with open(POINT_FILE, "r") as f:
        point_data = json.load(f)
    print(f"[YAPPING] Loaded point_data from {POINT_FILE}")
except Exception as e:
    print(f"[YAPPING] Failed to load point_data: {e}")
    point_data = {}

# ================= UTILITY ================= #
def save_points():
    """Simpan point ke file JSON"""
    try:
        with open(POINT_FILE, "w") as f:
            json.dump(point_data, f, indent=2)
        print(f"[YAPPING] Saved point_data to {POINT_FILE}")
    except Exception as e:
        print(f"[YAPPING] Failed to save point_data: {e}")

def load_points():
    """Load point dan kembalikan dictionary"""
    global point_data
    try:
        if os.path.exists(POINT_FILE):
            with open(POINT_FILE, "r") as f:
                point_data = json.load(f)
            print(f"[YAPPING] Loaded point_data from {POINT_FILE}")
        else:
            point_data = {}
            with open(POINT_FILE, "w") as f:
                json.dump(point_data, f, indent=2)
            print(f"[YAPPING] Point file not found. Created new file.")
    except Exception as e:
        print(f"[YAPPING] Error loading points: {e}")
        traceback.print_exc()
    return point_data

# ================= REGISTER HANDLER ================= #
def register(app: Client):
    print("[YAPPING] Registering handlers...")

    # ================= HANDLER CHAT POINT ================= #
    @app.on_message(filters.text & ~filters.private)  # Sementara, tangkap semua chat untuk debug
    async def yapping_point(client: Client, message: Message):
        """Handler chat point utama"""
        try:
            user = message.from_user
            if not user:
                print("[YAPPING] Message has no from_user, skipping")
                return

            text = message.text.strip()
            if len(text) < 5:
                print(f"[YAPPING] Message too short ({len(text)} chars), skipping")
                return  # minimal 5 karakter

            user_id = str(user.id)
            if user_id not in point_data:
                point_data[user_id] = {"username": user.first_name, "points": 0}

            point_data[user_id]["points"] += 1
            save_points()

            print(f"[YAPPING] {user.first_name} ({user.id}) → total points: {point_data[user_id]['points']}")
        except Exception as e:
            print(f"[YAPPING] Exception in yapping_point: {e}")
            traceback.print_exc()

    # ================= COMMAND CHECK POINT ================= #
    @app.on_message(filters.command("point") & ~filters.private)
    async def check_point(client: Client, message: Message):
        """Cek point sendiri atau user lain"""
        try:
            args = message.text.split()
            if len(args) == 1:
                user_id = str(message.from_user.id)
                pts = point_data.get(user_id, {"points": 0})["points"]
                await message.reply_text(f"Total Chat Pointmu: {pts}")
            elif len(args) == 2:
                username = args[1].replace("@", "")
                found = None
                for uid, data in point_data.items():
                    if data.get("username") == username:
                        found = data
                        break
                if found:
                    await message.reply_text(f"Total Chat Point {username}: {found['points']}")
                else:
                    await message.reply_text("User tidak ditemukan.")
            print(f"[YAPPING] /point command processed by {message.from_user.first_name}")
        except Exception as e:
            print(f"[YAPPING] Exception in check_point: {e}")
            traceback.print_exc()

    # ================= COMMAND LEADERBOARD ================= #
    @app.on_message(filters.command("board") & ~filters.private)
    async def leaderboard(client: Client, message: Message):
        """Leaderboard top 10"""
        try:
            if not point_data:
                await message.reply_text("Leaderboard masih kosong.")
                print("[YAPPING] Leaderboard empty")
                return

            sorted_board = sorted(point_data.items(), key=lambda x: x[1]["points"], reverse=True)
            text = "🏆 Leaderboard Chat Points 🏆\n\n"
            for i, (uid, data) in enumerate(sorted_board[:10], 1):
                text += f"{i}. {data['username']} → {data['points']} pts\n"
            await message.reply_text(text)
            print(f"[YAPPING] Leaderboard sent by {message.from_user.first_name}")
        except Exception as e:
            print(f"[YAPPING] Exception in leaderboard: {e}")
            traceback.print_exc()

    print("[YAPPING] Handlers registered successfully")
