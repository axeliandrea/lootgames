import logging
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772  # ID group
clicked_users = set()

def register(app):
    logger.info("[CHEST] Registering treasure_chest module...")

    @app.on_message(filters.private & filters.command("treasurechest", prefixes=["."]))
    async def treasure_handler(client, message):
        logger.info(f"[CHEST] Command treasurechest dari {message.from_user.id}")
        if message.from_user.id != OWNER_ID:
            await message.reply("❌ Kamu bukan owner.")
            return

        try:
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("💎 TREASURE CHEST", callback_data="open_treasure")]]
            )
            await client.send_message(
                TARGET_GROUP,
                "🎁 **TREASURE CHEST SPAWNED!**\nKlik tombol di bawah untuk mendapatkan reward!",
                reply_markup=keyboard
            )
            await message.reply(f"✅ Berhasil kirim treasure chest ke group {TARGET_GROUP}")
        except Exception as e:
            logger.error(f"[CHEST] Gagal kirim chest: {e}")
            await message.reply(f"❌ Gagal kirim chest: {e}")

    @app.on_callback_query(filters.regex("^open_treasure$"))
    async def chest_callback(client, cq):
        user = cq.from_user
        if user.id in clicked_users:
            await cq.answer("⚠️ Kamu sudah membuka chest ini!", show_alert=True)
            return
        clicked_users.add(user.id)
        await cq.answer("🎉 Kamu buka chest!", show_alert=True)
        logger.info(f"[CHEST] User {user.id} klik chest")
