import asyncio
import logging
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772  # ID group target

# tracking user yang sudah klik chest
clicked_users = set()

def register(app):
    logger.info("[CHEST] Registering treasure_chest module...")

    # ================= PRIVATE COMMAND FOR OWNER ================= #
    @app.on_message(filters.private & filters.user(OWNER_ID) & filters.command("treasurechest", prefixes=["."]))
    async def treasure_handler(client, message):
        logger.info(f"[CHEST] Owner {OWNER_ID} trigger .treasurechest")
        await message.reply("⏳ Preparing kirim chest...")

        await asyncio.sleep(1)

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("💎 TREASURE CHEST", callback_data="open_treasure")]]
        )

        try:
            await client.send_message(
                chat_id=TARGET_GROUP,
                text="🎁 **TREASURE CHEST SPAWNED!**\nKlik tombol di bawah untuk mendapatkan reward!",
                reply_markup=keyboard
            )
            await message.reply(f"✅ Berhasil kirim TREASURE CHEST ke group {TARGET_GROUP}")
        except Exception as e:
            logger.error(f"[CHEST] Gagal kirim chest: {e}")
            await message.reply(f"❌ Gagal kirim chest: {e}")

    # ================= CALLBACK QUERY FOR ALL USERS ================= #
    @app.on_callback_query(filters.regex("^open_treasure$"))
    async def chest_callback(client, cq):
        user = cq.from_user
        if user.id in clicked_users:
            await cq.answer("⚠️ Kamu sudah membuka chest ini!", show_alert=True)
            return

        clicked_users.add(user.id)
        logger.info(f"[CHEST] User {user.id} ({user.first_name}) klik chest")
        await cq.answer("🎉 Kamu buka chest!", show_alert=True)
