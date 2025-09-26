# lootgames/modules/treasure_chest.py
import random
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

from lootgames.config import OWNER_ID, ALLOWED_GROUP_ID
from lootgames.modules import umpan

logger = logging.getLogger(__name__)

CHEST_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton("💎 TREASURE CHEST", callback_data="TREASURE_CHEST")]]
)

# ================= SPAWN CHEST ================= #
async def spawn_chest(client: Client, message: Message):
    """Owner kirim .treasure_chest di private untuk spawn di grup"""
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ Kamu bukan owner!")

    try:
        await client.send_message(
            ALLOWED_GROUP_ID,
            "🎁 **TREASURE CHEST SPAWN!** 🎁\nKlik tombol untuk klaim!",
            reply_markup=CHEST_BUTTON
        )
        await message.reply("✅ Chest berhasil dikirim ke group!")
        logger.info("[TREASURE] Chest spawned di group.")
    except Exception as e:
        logger.error(f"Gagal spawn chest: {e}")
        await message.reply(f"❌ Error spawn chest: {e}")

# ================= CALLBACK ================= #
async def chest_callback(client: Client, callback_query: CallbackQuery):
    user = callback_query.from_user
    user_id = user.id
    username = user.username or user.first_name or str(user_id)

    # Random drop
    roll = random.randint(1, 100)
    if roll <= 10:
        # Dapat umpan type A
        umpan.init_user_if_missing(user_id, username)
        umpan.add_umpan(user_id, "A", 1)
        msg = f"🎉 {username} membuka chest dan mendapat **Umpan Common (A)**!"
    else:
        msg = f"💨 {username} membuka chest, tapi isinya kosong (Zonk)."

    try:
        await callback_query.answer("Chest dibuka!", show_alert=False)
        await callback_query.message.reply(msg)
    except Exception as e:
        logger.error(f"Gagal proses chest callback: {e}")

# ================= REGISTER ================= #
def register(app: Client):
    # Command owner
    app.add_handler(
        filters.create(lambda _, __, msg: msg.text and msg.text.lower().startswith(".treasure_chest"))
        (spawn_chest)
    )
    # Callback
    app.add_handler(
        filters.create(lambda _, __, cb: cb.data == "TREASURE_CHEST")
        (chest_callback)
    )
