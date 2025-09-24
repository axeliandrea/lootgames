# lootgames/modules/treasure_chest.py
import logging
import random
from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from lootgames.modules.umpan import add_umpan

logger = logging.getLogger(__name__)

OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772  # ganti sesuai group kamu
clicked_users = set()  # tracking user yang sudah klik chest

def register(app: Client):
    logger.info("[CHEST] Registering treasure_chest module...")

    # ================= PRIVATE COMMAND OWNER ================= #
    @app.on_message(filters.private & filters.command("treasurechest", prefixes=["."]))
    async def treasure_handler(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("❌ Kamu bukan owner.")
            return

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


# ================= CALLBACK QUERY ================= #
async def chest_callback(client: Client, cq: CallbackQuery):
    user = cq.from_user
    if user.id in clicked_users:
        await cq.answer("⚠️ Kamu sudah membuka chest ini!", show_alert=True)
        return

    clicked_users.add(user.id)
    logger.info(f"[CHEST] User {user.id} ({user.first_name}) klik chest")

    # 90% zonk, 10% reward
    if random.random() < 0.10:
        # Beri reward: 1 umpan tipe A
        add_umpan(user.id, "A", 1)
        await cq.answer("🎉 Kamu mendapatkan 1 umpan tipe A!", show_alert=True)
    else:
        await cq.answer("😢 Zonk! Tidak ada yang didapat.", show_alert=True)
