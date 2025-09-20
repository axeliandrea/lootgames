# lootgames/modules/user_database.py
import os
import json
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= CONFIG ================= #
DATA_PLAYER = "lootgames/modules/user_data.json"  # rename jadi DATA_PLAYER

# ================= INIT ================= #
if not os.path.exists(DATA_PLAYER):
    with open(DATA_PLAYER, "w") as f:
        json.dump({}, f, indent=2)

def load_users():
    with open(DATA_PLAYER, "r") as f:
        return json.load(f)

def save_users(users):
    with open(DATA_PLAYER, "w") as f:
        json.dump(users, f, indent=2)

# ================= REGISTER ================= #
def register(app: Client):

    @app.on_message(filters.private & filters.command("join"))
    async def join_handler(client: Client, message: Message):
        user_id = str(message.from_user.id)
        username = message.from_user.username or ""

        users = load_users()
        if user_id not in users:
            users[user_id] = {"username": username}
            save_users(users)
            await message.reply_text("🎉 Selamat, anda sudah menjadi player Loot!")
            print(f"[JOIN] New player added: {user_id} ({username})")
        else:
            await message.reply_text("⚠️ Anda sudah terdaftar sebagai player Loot.")
            print(f"[JOIN] Player already exists: {user_id} ({username})")

    @app.on_message(filters.private & filters.command("update"))
    async def update_handler(client: Client, message: Message):
        user_id = str(message.from_user.id)
        new_username = message.from_user.username or ""

        users = load_users()
        if user_id in users:
            old_username = users[user_id].get("username", "")
            if old_username != new_username:
                users[user_id]["username"] = new_username
                save_users(users)
                await message.reply_text(f"✅ Username diperbarui: {old_username} → {new_username}")
                print(f"[UPDATE] User {user_id} username updated: {old_username} → {new_username}")
            else:
                await message.reply_text("ℹ️ Username Anda tidak berubah.")
                print(f"[UPDATE] User {user_id} username not changed.")
        else:
            await message.reply_text("⚠️ Anda belum terdaftar. Gunakan /join terlebih dahulu.")
            print(f"[UPDATE] User {user_id} not found.")
