# lootgames/lootgames/modules/yapping.py
import json
import os
from pyrogram import filters
from pyrogram.types import Message

# ================= CONFIG ================= #
POINT_FILE = "lootgames/modules/yapping_point.json"
GROUP_ID = -1002904817520  # ID grup target

# ================= INIT DATA ================= #
if os.path.exists(POINT_FILE):
    with open(POINT_FILE, "r") as f:
        point_data = json.load(f)
else:
    point_data = {}

# ================= FUNGSI POINT ================= #
def save_points():
    """Simpan data point ke file JSON"""
    with open(POINT_FILE, "w") as f:
        json.dump(point_data, f, indent=4)

def load_points():
    """Mengembalikan seluruh data point"""
    return point_data

def get_point(user_id):
    """Mengembalikan point user tertentu"""
    return point_data.get(str(user_id), 0)

# ================= REGISTER MODULE ================= #
def register(app):
    @app.on_message(filters.chat(GROUP_ID) & filters.text & ~filters.private)
    async def yapping_point(client, message: Message):
        if not message.from_user:
            print("[DEBUG] Pesan tanpa user, diabaikan")
            return

        user_id = str(message.from_user.id)
        text = message.text

        # Ambil semua huruf unicode
        letters = [c for c in text if c.isalpha()]
        print(f"[DEBUG] User: {message.from_user.first_name}, Text: '{text}', Letters: {letters}")

        # Minimal 5 huruf
        if len(letters) < 5:
            print("[DEBUG] Kurang dari 5 huruf, tidak dapat point")
            return

        # ===== Jika mau periksa double huruf berurutan, aktifkan ini =====
        # for i in range(len(letters)-1):
        #     if letters[i].lower() == letters[i+1].lower():
        #         print("[DEBUG] Double huruf berurutan, tidak dapat point")
        #         return

        # Tambahkan point
        if user_id not in point_data:
            point_data[user_id] = 0
        point_data[user_id] += 1
        save_points()
        print(f"[YAPPING] {message.from_user.first_name} ({user_id}) mendapat 1 point. Total: {point_data[user_id]}")
