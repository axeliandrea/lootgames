# lootgames/modules/treasure_chest.py
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
import asyncio, random
from datetime import datetime
from lootgames.modules import umpan

OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772
DEBUG = True

def log_debug(msg: str):
    if DEBUG:
        print(f"[CHEST][{datetime.now().strftime('%H:%M:%S')}] {msg}")

async def spawn_chest(client: Client, message: Message):
    log_debug(f"spawn_chest() terpanggil dengan text={repr(message.text)} user={message.from_user.id if message.from_user else None}")

    if not message.from_user or message.from_user.id != OWNER_ID:
        await message.reply_text("❌ Kamu tidak memiliki izin.")
        return

    if message.chat.type != ChatType.PRIVATE:
        await message.reply_text("⚠️ Hanya bisa di private chat.")
        return

    btn = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🎁 TREASURE CHEST 🎁", callback_data="open_chest")]]
    )
    await client.send_message(
        TARGET_GROUP,
        "💰 **Sebuah Treasure Chest muncul di sini!**\nSiapa yang beruntung?",
        reply_markup=btn
    )
    await message.reply_text("✅ Chest dikirim ke group target.")
    log_debug("Treasure chest berhasil dikirim.")

async def open_chest(client: Client, cq: CallbackQuery):
    user = cq.from_user
    log_debug(f"open_chest() ditekan oleh {user.id}")
    await asyncio.sleep(1)
    roll = random.randint(1, 100)
    if roll <= 90:
        result = "ZONK ❌"
    else:
        result = "🎣 Kamu dapat **1x Umpan A**"
        await umpan.add_umpan(user.id, "A", 1)
    await cq.answer(result, show_alert=True)
    log_debug(f"{user.id} hasil={result}")

def register(app: Client):
    log_debug("Mendaftarkan handler treasure_chest...")

    # DEBUG TEST: log semua pesan sebelum filter jalan
    async def _precheck(client, message):
        log_debug(f"[PRECHECK] Pesan masuk ke treasure_chest scope: {repr(message.text)}")
    app.add_handler(MessageHandler(_precheck, filters.text), group=-1)

    # Command handler
    app.add_handler(
        MessageHandler(
            spawn_chest,
            filters.command(["treasurechest"], prefixes=["."])
        ),
        group=0,
    )

    # Callback handler
    app.add_handler(
        CallbackQueryHandler(
            open_chest,
            filters=lambda _, cq: cq.data == "open_chest"
        ),
        group=1,
    )

    log_debug("Handler treasure_chest terdaftar ✅")
