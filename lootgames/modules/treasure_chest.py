# lootgames/modules/treasure_chest.py
import os
import json
import random
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.modules import umpan

# ================= CONFIG ================= #
OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772
DEBUG = True

# ================= UTIL ================= #
def log_debug(msg: str):
    if DEBUG:
        print(f"[CHEST][{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ================= HANDLERS ================= #
async def spawn_chest(client: Client, message: Message):
    """Owner spawn treasure chest ke group target"""
    log_debug(f"Command '.treasurechest' diterima dari user {message.from_user.id} ({message.from_user.username}) di chat {message.chat.id} ({message.chat.type})")

    # Cek owner
    if message.from_user.id != OWNER_ID:
        await message.reply_text("❌ Kamu tidak memiliki izin menggunakan command ini.")
        log_debug(f"User {message.from_user.id} bukan owner. Command diblokir.")
        return

    # Cek private chat
    if message.chat.type != "private":
        await message.reply_text("⚠️ Command ini hanya bisa dipakai di private chat ke bot.")
        log_debug(f"Command dijalankan bukan di private chat. chat_type={message.chat.type}")
        return

    # Kirim treasure chest
    btn = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🎁 TREASURE CHEST 🎁", callback_data="open_chest")]]
    )

    await client.send_message(
        TARGET_GROUP,
        "💰 **Sebuah Treasure Chest muncul di sini!**\n"
        "Siapa yang beruntung mendapatkannya?",
        reply_markup=btn
    )
    await message.reply_text("✅ Treasure Chest berhasil dikirim ke group target.")
    log_debug("Treasure chest spawned ke group target.")

async def open_chest(client: Client, cq: CallbackQuery):
    """User klik tombol chest"""
    user = cq.from_user
    log_debug(f"Callback 'open_chest' ditekan oleh user {user.id} ({user.username})")

    await asyncio.sleep(1)  # Anti-flood delay
    roll = random.randint(1, 100)

    if roll <= 90:
        result = "ZONK ❌ (tidak dapat apa-apa)"
    else:
        result = "🎣 Kamu dapat **1x Umpan A**"
        await umpan.add_umpan(user.id, "A", 1)

    await cq.answer(result, show_alert=True)
    log_debug(f"{user.id} opened chest → {result}")

# ================= REGISTER ================= #
def register(app: Client):
    log_debug("Mendaftarkan handler treasure_chest...")

    # Command spawn chest hanya di private chat
    app.add_handler(
        MessageHandler(
            spawn_chest,
            filters.command("treasurechest", prefixes=["."]) & filters.private
        ),
        group=0
    )

    # CallbackQuery untuk tombol treasure chest
    app.add_handler(
        CallbackQueryHandler(
            open_chest,
            filters=lambda _, cq: cq.data == "open_chest"
        ),
        group=1
    )

    log_debug("Handler treasure_chest terdaftar ✅")
