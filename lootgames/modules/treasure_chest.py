# lootgames/modules/treasure_chest.py
import os
import json
import random
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from lootgames.modules import umpan

# ================= CONFIG ================= #
OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772
LUCKY_DB = "storage/lucky_chip.json"
DEBUG = True

# ================= UTIL ================= #
def log_debug(msg: str):
    if DEBUG:
        print(f"[CHEST][{datetime.now().strftime('%H:%M:%S')}] {msg}")

def load_lucky():
    if not os.path.exists(LUCKY_DB):
        return {"claimed": False, "user_id": None}
    with open(LUCKY_DB, "r") as f:
        return json.load(f)

def save_lucky(data):
    os.makedirs(os.path.dirname(LUCKY_DB), exist_ok=True)
    with open(LUCKY_DB, "w") as f:
        json.dump(data, f, indent=2)

# ================= HANDLERS ================= #
async def spawn_chest(client: Client, message: Message):
    """Owner spawn treasure chest ke group target"""
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ Kamu tidak memiliki izin menggunakan command ini.")
    if message.chat.type != "private":
        return await message.reply_text("⚠️ Command ini hanya bisa dipakai di private chat.")

    btn = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🎁 TREASURE CHEST 🎁", callback_data="open_chest")]]
    )

    await client.send_message(
        TARGET_GROUP,
        "💰 **Sebuah Treasure Chest muncul di sini!**\n"
        "Siapa yang beruntung mendapatkannya?",
        reply_markup=btn,
    )
    await message.reply_text("✅ Treasure Chest berhasil dikirim ke group target.")
    log_debug("Treasure chest spawned.")

async def open_chest(client: Client, cq: CallbackQuery):
    """User klik tombol chest"""
    user = cq.from_user
    lucky_data = load_lucky()

    # Delay 1 detik untuk anti floodwait
    await asyncio.sleep(1)

    # Tentukan hasil random
    roll = random.randint(1, 100)
    if roll <= 90:
        result = "ZONK ❌ (tidak dapat apa-apa)"
    elif roll <= 95:
        result = "🎣 Kamu dapat **1x Umpan A**"
        await umpan.add_umpan(user.id, "A", 1)
    elif roll <= 99:
        if not lucky_data["claimed"]:
            lucky_data["claimed"] = True
            lucky_data["user_id"] = user.id
            save_lucky(lucky_data)
            result = "🍀 Kamu beruntung! Mendapat **Lucky Chip**"
        else:
            result = "ZONK ❌ (Lucky Chip sudah diambil orang lain)"
    else:
        result = "💎 Kamu mendapatkan **Lucky Sawer**"

    # Kirim hasil ke user
    await cq.answer(result, show_alert=True)
    log_debug(f"{user.id} opened chest → {result}")

# ================= REGISTER ================= #
def register(app: Client):
    app.add_handler(
        filters.command("treasurechest", prefixes=["."]) & filters.private,
        spawn_chest,
    )
    app.add_handler(
        filters.callback_query("open_chest"),
        open_chest,
    )
    log_debug("Handler treasure_chest terdaftar ✅")
