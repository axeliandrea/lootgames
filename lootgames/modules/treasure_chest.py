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

    @app.on_message(filters.private & filters.user(OWNER_ID) & filters.command("treasurechest", prefixes=["."]))
    async def treasure_handler(client, message):
        try:
            # Step 1: notify owner preparing
            await message.reply(f"⏳ Preparing kirim TREASURE CHEST ke group {TARGET_GROUP}")
            logger.info("[CHEST] Preparing kirim treasure chest...")

            # Step 2: delay 2 detik
            await asyncio.sleep(2)

            # Step 3: kirim chest ke grup
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("💎 TREASURE CHEST", callback_data="open_treasure")]]
            )
            await client.send_message(
                chat_id=TARGET_GROUP,
                text="🎁 **TREASURE CHEST SPAWNED!**\nKlik tombol di bawah untuk mendapatkan reward!",
                reply_markup=keyboard
            )

            # Step 4: notify owner success
            await message.reply(f"✅ Berhasil kirim TREASURE CHEST ke group {TARGET_GROUP}")
            logger.info(f"[CHEST] Chest terkirim ke {TARGET_GROUP}")

        except Exception as e:
            err = f"[CHEST] Error: {e}"
            logger.error(err)
            await message.reply(f"❌ Gagal kirim chest:\n`{e}`")

    @app.on_callback_query(filters.regex("^open_treasure$"))
    async def chest_callback(client, callback_query):
        user = callback_query.from_user
        logger.info(f"[CHEST] {user.id} klik chest!")
        await callback_query.answer("🎉 Kamu buka chest... (reward system menyusul)", show_alert=True)
