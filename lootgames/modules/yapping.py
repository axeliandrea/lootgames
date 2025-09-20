import re
from pyrogram import Client, filters
from pyrogram.types import Message

TARGET_GROUP = -1002904817520  # ganti dengan ID grupmu
DEBUG = True

def register(app: Client):

    print("[DEBUG] Registering yapping handlers...")  # harus muncul saat start

    @app.on_message(filters.group & filters.text)
    async def chat_point_handler(client, message: Message):
        user = message.from_user
        if not user:
            return

        text = message.text.strip()
        # hitung jumlah huruf
        letters_only = re.sub(r"[^a-zA-Z]", "", text)
        if len(letters_only) < 5:
            if DEBUG:
                print(f"[DEBUG] Message too short: '{text}'")
            return

        username = user.username or user.first_name or "Unknown"
        if DEBUG:
            print(f"[DEBUG] {username} sent message: '{text}' → {len(letters_only)} letters → 1 point!")
