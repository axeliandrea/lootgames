# lootgames/modules/treasure_chest.py
import random
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.modules import umpan

OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772
DEBUG = True

def log_debug(msg: str):
    if DEBUG:
        print(f"[CHEST][{datetime.now().strftime('%H:%M:%S')}] {msg}")

async def spawn_chest(client: Client, message: Message):
    try:
        log_debug(
            f"spawn_chest() dipanggil — from_user={getattr(message.from_user,'id',None)} "
            f"username={getattr(message.from_user,'username',None)} chat_id={getattr(message.chat,'id',None)} "
            f"chat_type={getattr(message.chat,'type',None)} text={repr(message.text)}"
        )
    except Exception as e:
        print("[CHEST][ERR] gagal print info message:", e)

    # hanya owner
    if not message.from_user or message.from_user.id != OWNER_ID:
        await message.reply_text("❌ Kamu tidak memiliki izin menggunakan command ini.")
        log_debug("bukan owner -> command diblokir")
        return

    # pastikan private chat (gunakan enum ChatType)
    if message.chat.type != ChatType.PRIVATE:
        await message.reply_text("⚠️ Command ini hanya bisa dipakai di private chat ke bot.")
        log_debug(f"ditolak karena chat_type != PRIVATE (chat_type={message.chat.type})")
        return

    # kirim chest ke group target — bungkus try/except supaya error terlihat
    btn = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🎁 TREASURE CHEST 🎁", callback_data="open_chest")]]
    )

    try:
        await client.send_message(
            TARGET_GROUP,
            "💰 **Sebuah Treasure Chest muncul di sini!**\nSiapa yang beruntung mendapatkannya?",
            reply_markup=btn
        )
        await message.reply_text("✅ Treasure Chest berhasil dikirim ke group target.")
        log_debug(f"treasure chest dikirim ke group {TARGET_GROUP}")
    except Exception as e:
        await message.reply_text("❌ Gagal mengirim treasure chest ke group target. Cek logs.")
        log_debug(f"ERROR mengirim ke group {TARGET_GROUP}: {e}")

async def open_chest(client: Client, cq: CallbackQuery):
    user = cq.from_user
    log_debug(f"open_chest() ditekan oleh user={getattr(user,'id',None)} username={getattr(user,'username',None)}")
    await asyncio.sleep(1)
    roll = random.randint(1, 100)
    log_debug(f"roll={roll}")
    if roll <= 90:
        result = "ZONK ❌ (tidak dapat apa-apa)"
    else:
        result = "🎣 Kamu dapat **1x Umpan A**"
        try:
            umpan.add_umpan(user.id, "A", 1)
            log_debug(f"umpan.add_umpan sukses untuk user {user.id}")
        except Exception as e:
            log_debug(f"ERROR add_umpan: {e}")
    try:
        await cq.answer(result, show_alert=True)
    except Exception as e:
        log_debug(f"ERROR cq.answer: {e}")
    log_debug(f"{user.id} opened chest → {result}")

def register(app: Client):
    log_debug("Mendaftarkan handler treasure_chest...")
    # spawn hanya di private chat & prioritas tinggi (group=0)
    app.add_handler(
        MessageHandler(
            spawn_chest,
            filters.command("treasurechest", prefixes=["."]) & filters.private
        ),
        group=0
    )
    # callback button
    app.add_handler(
        CallbackQueryHandler(open_chest, filters=lambda _ , cq: getattr(cq, "data", None) == "open_chest"),
        group=1
    )
    log_debug("Handler treasure_chest terdaftar ✅")
