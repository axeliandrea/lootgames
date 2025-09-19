# lootgames/modules/yapping.py
import os
import json
from pyrogram import filters
from pyrogram.types import Message
from pyrogram import Client

# ================= CONFIG ================= #
GROUP_ID = -1002904817520  # Ganti sesuai grup target
POINT_FILE = "lootgames/modules/yapping_point.json"

# ================= INIT DATA ================= #
if os.path.exists(POINT_FILE):
    with open(POINT_FILE, "r") as f:
        point_data = json.load(f)
else:
    point_data = {}

def save_points():
    with open(POINT_FILE, "w") as f:
        json.dump(point_data, f, indent=2)

# ================= REGISTER HANDLER ================= #
def register(app: Client):

    @app.on_message(filters.chat(GROUP_ID) & filters.text & ~filters.private)
    async def yapping_point(client: Client, message: Message):
        """Handler utama untuk chat point"""
        user = message.from_user
        if not user:
            return

        text = message.text.strip()
        if len(text) < 5:
            return  # minimal 5 karakter

        user_id = str(user.id)
        if user_id not in point_data:
            point_data[user_id] = {"name": user.first_name, "point": 0}

        point_data[user_id]["point"] += 1
        save_points()

        print(f"[DEBUG] {user.first_name} ({user.id}) chat: '{text}' → total point: {point_data[user_id]['point']}")

    @app.on_message(filters.command("point") & ~filters.private)
    async def check_point(client: Client, message: Message):
        """Cek point sendiri atau user lain"""
        args = message.text.split()
        if len(args) == 1:
            # Cek point sendiri
            user_id = str(message.from_user.id)
            pts = point_data.get(user_id, {"point":0})["point"]
            await message.reply_text(f"Total Chat Pointmu: {pts}")
        elif len(args) == 2:
            # Cek point user lain @username
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

    @app.on_message(filters.command("board") & ~filters.private)
    async def leaderboard(client: Client, message: Message):
        """Leaderboard top 10"""
        if not point_data:
            await message.reply_text("Leaderboard masih kosong.")
            return

        sorted_board = sorted(point_data.items(), key=lambda x: x[1]["point"], reverse=True)
        text = "🏆 Leaderboard Chat Points 🏆\n\n"
        for i, (uid, data) in enumerate(sorted_board[:10], 1):
            text += f"{i}. {data['name']} → {data['point']} point\n"
        await message.reply_text(text)

# ================= AUTO REGISTER (optional) ================= #
# Ini berguna kalau modul diimport langsung
try:
    from lootgames.__main__ import app
except ImportError:
    pass
else:
    register(app)
