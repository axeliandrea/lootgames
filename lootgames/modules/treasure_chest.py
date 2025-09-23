# lootgames/modules/treasure_chest.py
import logging
import random
from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from lootgames.modules.umpan import add_umpan

logger = logging.getLogger(__name__)

OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772  # Default group target
clicked_users = set()  # Tracking user yang sudah klik chest

def register(app: Client):
    logger.info("[CHEST] Registering treasure_chest module...")

    # ================= COMMAND OWNER ================= #
    @app.on_message(filters.user(OWNER_ID) & filters.command("treasurechest", prefixes=["."]))
    async def treasure_handler(client, message):
        global clicked_users
        clicked_users = set()  # reset setiap spawn baru

        # Bisa kirim ke TARGET_GROUP default atau ke chat sekarang
        target = TARGET_GROUP if message.chat.type in ["private", "supergroup", "group"] else message.chat.id
        await message.reply("⏳ Preparing kirim treasure chest...")

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("💎 TREASURE CHEST", callback_data="open_treasure")]]
        )

        try:
            await client.send_message(
                target,
                "🎁 **TREASURE CHEST SPAWNED!**\nKlik tombol di bawah untuk mendapatkan reward!",
                reply_markup=keyboard
            )
            logger.info(f"[CHEST] Treasure chest dikirim ke chat {target}")
            await message.reply(f"✅ Berhasil kirim treasure chest ke chat {target}")
        except Exception as e:
            logger.error(f"[CHEST] Gagal kirim chest: {e}")
            await message.reply(f"❌ Gagal kirim chest: {e}")

    # ================= CALLBACK QUERY UNTUK SEMUA USER ================= #
    @app.on_callback_query(filters.regex("^open_treasure$"))
    async def chest_callback(client, cq):
        user = cq.from_user
        global clicked_users

        if user.id in clicked_users:
            await cq.answer("⚠️ Kamu sudah membuka chest ini!", show_alert=True)
            return

        clicked_users.add(user.id)
        logger.info(f"[CHEST] User {user.id} ({user.first_name}) klik chest")

        # Tentukan reward: 10% dapat umpan tipe A
        if random.randint(1,10) == 1:  # 10% chance
            add_umpan(user.id, "A", 1)
            await cq.answer("🎉 Kamu dapat 1 umpan tipe A!", show_alert=True)
            logger.info(f"[CHEST] User {user.id} dapat 1 umpan tipe A")
        else:
            await cq.answer("💀 Zonk! Tidak dapat apa-apa.", show_alert=True)
            logger.info(f"[CHEST] User {user.id} zonk")
