# lootgames/lootgames/modules/yapping.py
import json
import os
import re
from pyrogram import filters
from pyrogram.types import Message

# File penyimpanan point
POINT_FILE = "lootgames/modules/yapping_point.json"
GROUP_ID = -1002904817520  # ID grup target

# Load atau inisialisasi data point
if os.path.exists(POINT_FILE):
    with open(POINT_FILE, "r") as f:
        point_data = json.load(f)
else:
    point_data = {}

def save_points():
    with open(POINT_FILE, "w") as f:
        json.dump(point_data, f, indent=4)

# Fungsi register modul untuk __main__.py
def register(app):

    @app.on_message(filters.chat(GROUP_ID) & filters.text & ~filters.private)
    async def yapping_point(client, message: Message):
        user_id = str(message.from_user.id)
        text = message.text

        # Hitung hanya huruf (a-z, A-Z)
        letters = re.findall(r"[a-zA-Z]", text)
        if len(letters) < 5:
            return  # minimal 5 huruf

        # Cek double huruf berurutan
        for i in range(len(letters)-1):
            if letters[i].lower() == letters[i+1].lower():
                return  # double huruf ditemukan, tidak dapat point

        # Tambahkan point
        if user_id not in point_data:
            point_data[user_id] = 0
        point_data[user_id] += 1
        save_points()

        # Opsional: reply atau log di terminal
        print(f"[YAPPING] {message.from_user.first_name} ({user_id}) mendapat 1 point. Total: {point_data[user_id]}")
