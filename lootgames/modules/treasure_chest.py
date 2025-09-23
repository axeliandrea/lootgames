# lootgames/modules/treasure_chest.py
import asyncio
import logging
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772  # ID grup target


def register(app):
    logger.info("[CHEST] Registering treasure_chest module...")

    # Tes: tanpa filter user dulu
    @app.on_message(filters.private & filters.command("treasurechest", prefixes=["."]))
    async def treasure_handler(client, message):
        logger.info("[CHEST] Handler .treasurechest terpanggil")
        await message.reply("⏳ Preparing kirim chest...")

        await asyncio.sleep(2)

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("💎 TREASURE CHEST", callback_data="open_treasure")]]
        )
        await client.send_message(
            chat_id=TARGET_GROUP,
            text="🎁 **TREASURE CHEST SPAWNED!**\nKlik tombol di bawah untuk mendapatkan reward!",
            reply_markup=keyboard
        )

        await message.reply(f"✅ Berhasil kirim TREASURE CHEST ke group {TARGET_GROUP}")

    @app.on_callback_query(filters.regex("^open_treasure$"))
    async def chest_callback(client, cq):
        user = cq.from_user
        logger.info(f"[CHEST] {user.id} klik chest")
        await cq.answer("🎉 Kamu buka chest!", show_alert=True)
