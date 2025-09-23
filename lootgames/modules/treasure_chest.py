# lootgames/modules/treasure_chest.py
import logging
import random
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from lootgames.modules import umpan  # <- import modul umpan

logger = logging.getLogger(__name__)

OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772
clicked_users = set()  # tracking user yang sudah klik chest

def register(app):
    logger.info("[CHEST] Registering treasure_chest module...")

    # ================= PRIVATE COMMAND OWNER ================= #
    @app.on_message(filters.private & filters.command("treasurechest", prefixes=["."]))
    async def treasure_handler(client, message: Message):
        if message.from_user.id != OWNER_ID:
            await message.reply("❌ Kamu bukan owner.")
            return

        global clicked_users
        clicked_users = set()  # reset chest

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
    async def chest_callback(client, cq: CallbackQuery):
        user = cq.from_user
        if user.id in clicked_users:
            await cq.answer("⚠️ Kamu sudah membuka chest ini!", show_alert=True)
            return

        clicked_users.add(user.id)
        logger.info(f"[CHEST] User {user.id} ({user.first_name}) klik chest")

        # Tentukan hadiah
        chance = random.randint(1, 100)
        if chance <= 10:  # 10% dapat reward
            umpan.init_user(user.id, user.username)  # pastikan user ada di DB
            umpan.add_umpan(user.id, "A", 1)         # +1 umpan tipe A
            reward_msg = "🎉 Selamat! Kamu mendapatkan **1 Umpan Tipe A (Common)**!"
        else:
            reward_msg = "😢 Zonk! Tidak mendapatkan apa-apa."

        # tombol kembali setelah buka chest
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Kembali", callback_data="main")]
        ])

        await cq.message.edit_text(
            f"🎁 @{user.username or user.first_name} membuka chest!\n{reward_msg}",
            reply_markup=kb
        )
        await cq.answer(reward_msg, show_alert=True)
