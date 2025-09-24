import logging
import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from lootgames.modules.umpan import add_umpan

logger = logging.getLogger(__name__)

OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772  # ganti sesuai ID group
clicked_users = set()

def register(app: Client):
    logger.info("[CHEST] Registering treasure_chest module...")

    # ================= PRIVATE COMMAND OWNER ================= #
    @app.on_message(filters.private & filters.command("treasurechest", prefixes=["."]))
    async def treasure_handler(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("❌ Kamu bukan owner.")
            return

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("💎 Buka Treasure Chest", callback_data="open_treasure")]]
        )

        try:
            await client.send_message(
                TARGET_GROUP,
                "🎁 **TREASURE CHEST SPAWNED!**\nKlik tombol di bawah untuk mendapatkan reward!",
                reply_markup=keyboard
            )
            await message.reply(f"✅ Treasure chest berhasil dikirim ke group {TARGET_GROUP}")
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

        # 90% zonk, 10% reward umpan tipe A
        reward = random.choices(["ZONK", "UMPAN_A"], weights=[90, 10])[0]
        if reward == "UMPAN_A":
            add_umpan(user.id, "A", 1)  # Tambah 1 umpan tipe A
            await cq.answer("🎉 Selamat! Kamu dapat 1 umpan tipe A!", show_alert=True)
        else:
            await cq.answer("😢 Zonkk! Tidak ada yang kamu dapat.", show_alert=True)
