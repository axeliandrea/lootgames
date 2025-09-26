# lootgames/modules/treasure_chest.py
import random
import json
import os
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.config import OWNER_ID, ALLOWED_GROUP_ID
from lootgames.modules import umpan

logger = logging.getLogger(__name__)

# ================= CONFIG ================= #
CHEST_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton("💎 TREASURE CHEST", callback_data="TREASURE_CHEST")]]
)
CHEST_DB = "storage/treasure_claim.json"

# ================= DB HELPERS ================= #
def load_claims():
    if not os.path.exists(CHEST_DB):
        return {}
    with open(CHEST_DB, "r") as f:
        return json.load(f)

def save_claims(db: dict):
    os.makedirs("storage", exist_ok=True)
    with open(CHEST_DB, "w") as f:
        json.dump(db, f, indent=2)

# ================= COMMAND ================= #
async def spawn_chest(client: Client, message: Message):
    """Owner kirim .treasure_chest di private untuk spawn di grup"""
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ Kamu bukan owner!")

    try:
        # reset klaim untuk chest baru
        save_claims({})
        await client.send_message(
            ALLOWED_GROUP_ID,
            "🎁 **TREASURE CHEST SPAWN!** 🎁\nKlik tombol untuk klaim sekali saja!",
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
    user_id = str(user.id)
    username = user.username or user.first_name or user_id

    claims = load_claims()
    if user_id in claims:
        return await callback_query.answer("❌ Kamu sudah klaim chest ini!", show_alert=True)

    # Random drop
    roll = random.randint(1, 100)
    if roll <= 10:
        umpan.init_user_if_missing(int(user_id), username)
        umpan.add_umpan(int(user_id), "A", 1)
        msg = f"🎉 {username} membuka chest dan mendapat **Umpan Common (A)**!"
    else:
        msg = f"💨 {username} membuka chest, tapi isinya kosong (Zonk)."

    # simpan ke DB klaim
    claims[user_id] = {"username": username, "result": msg}
    save_claims(claims)

    try:
        await callback_query.answer("✅ Chest berhasil diklaim!", show_alert=False)
        await callback_query.message.reply(msg)
    except Exception as e:
        logger.error(f"Gagal proses chest callback: {e}")

# ================= REGISTER ================= #
def register(app: Client):
    app.add_handler(MessageHandler(spawn_chest, filters.private & filters.command("treasure_chest", prefixes=".")))
    app.add_handler(CallbackQueryHandler(chest_callback, filters.regex("^TREASURE_CHEST$")))
