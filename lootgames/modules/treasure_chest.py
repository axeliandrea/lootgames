# lootgames/modules/treasure_chest.py
import logging
import random
from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from lootgames.modules.umpan import add_umpan

logger = logging.getLogger(__name__)

OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772  # Ganti sesuai ID group
clicked_users = set()  # Track user yang sudah buka chest

def register(app: Client):
    logger.info("[CHEST] Registering treasure_chest module...")

    # ================= COMMAND OWNER ================= #
    @app.on_message(
        filters.user(OWNER_ID) &
        filters.command("treasurechest", prefixes=["."]) &
        (filters.private | filters.group)
    )
    async def treasure_handler(client: Client, message):
        logger.info(f"[CHEST] .treasurechest command diterima dari {message.from_user.id}")

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
            # Reset clicked_users setiap chest baru
            clicked_users.clear()
            logger.info("[CHEST] clicked_users di-reset untuk chest baru")
        except Exception as e:
            logger.error(f"[CHEST] Gagal kirim chest: {e}")
            await message.reply(f"❌ Gagal kirim chest: {e}")

    # ================= CALLBACK UNTUK USER ================= #
    @app.on_callback_query(filters.regex("^open_treasure$"))
    async def chest_callback(client: Client, cq: CallbackQuery):
        user = cq.from_user
        if user.id in clicked_users:
            await cq.answer("⚠️ Kamu sudah membuka chest ini!", show_alert=True)
            return

        clicked_users.add(user.id)
        logger.info(f"[CHEST] User {user.id} ({user.first_name}) klik chest")

        # Tentukan hadiah
        chance = random.randint(1, 100)
        if chance <= 90:
            # Zonk
            text = "💀 Zonk! Kamu tidak mendapatkan apa-apa."
            await cq.answer(text, show_alert=True)
            logger.info(f"[CHEST] User {user.id} dapat ZONK")
        else:
            # 10% chance dapat umpan tipe A
            jumlah_umpan = random.randint(1, 3)  # Bisa ubah jumlah
            add_umpan(user.id, "A", jumlah_umpan)
            text = f"🎉 Selamat! Kamu mendapatkan {jumlah_umpan} umpan tipe A."
            await cq.answer(text, show_alert=True)
            logger.info(f"[CHEST] User {user.id} dapat {jumlah_umpan} umpan tipe A")
