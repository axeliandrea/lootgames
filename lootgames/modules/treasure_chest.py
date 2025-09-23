import logging
import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from lootgames.modules import umpan

logger = logging.getLogger(__name__)

OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772  # ganti sesuai ID group
clicked_users = set()  # user yang sudah klik chest

def register(app: Client):
    logger.info("[CHEST] Registering treasure_chest module...")

    # ================= PRIVATE COMMAND OWNER ================= #
    @app.on_message(filters.user(OWNER_ID) & filters.command("treasurechest", prefixes=["."]))
    async def treasure_handler(client, message):
        logger.info(f"[CHEST] Command diterima dari {message.from_user.id}")
        await message.reply("⏳ Preparing kirim treasure chest...")

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("💎 TREASURE CHEST", callback_data="open_treasure")]]
        )

        try:
            await client.send_message(
                TARGET_GROUP,
                "🎁 **TREASURE CHEST SPAWNED!**\nKlik tombol di bawah untuk mendapatkan reward!",
                reply_markup=keyboard
            )
            await message.reply(f"✅ Berhasil kirim treasure chest ke group {TARGET_GROUP}")
        except Exception as e:
            logger.error(f"[CHEST] Gagal kirim chest: {e}")
            await message.reply(f"❌ Gagal kirim chest: {e}")

    # ================= CALLBACK QUERY UNTUK SEMUA USER ================= #
    @app.on_callback_query(filters.regex("^open_treasure$"))
    async def chest_callback(client, cq):
        user = cq.from_user
        if user.id in clicked_users:
            await cq.answer("⚠️ Kamu sudah membuka chest ini!", show_alert=True)
            return

        clicked_users.add(user.id)
        logger.info(f"[CHEST] User {user.id} ({user.first_name}) klik chest")

        # Random reward
        chance = random.randint(1, 100)
        if chance <= 10:
            # User menang umpan tipe A
            umpan.init_user_if_missing(user.id, user.username)
            umpan.add_umpan(user.id, "A", 1)
            await cq.answer("🎉 Selamat! Kamu mendapatkan 1 umpan tipe A!", show_alert=True)
            logger.info(f"[CHEST] User {user.id} mendapatkan 1 umpan tipe A")
        else:
            # Zonk
            await cq.answer("💀 Zonk! Tidak ada reward kali ini.", show_alert=True)
            logger.info(f"[CHEST] User {user.id} zonk")

