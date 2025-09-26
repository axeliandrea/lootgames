# lootgames/modules/treasure_chest.py
import logging
import traceback
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.config import OWNER_ID, ALLOWED_GROUP_ID

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

CHEST_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton("💎 TREASURE CHEST", callback_data="TREASURE_CHEST")]]
)

def register(app: Client):
    logger.info("Registering treasure_chest (TEST handler)")

    @app.on_message(filters.private & filters.command(["treasure_chest", "treasurechest"], prefixes="."))
    async def spawn_test(client: Client, message):
        # ACK immediately so kita tahu handler terpanggil
        try:
            caller = message.from_user.id if message.from_user else None
            await message.reply(f"DEBUG: command diterima. caller_id={caller}. mengecek permission & ALLOWED_GROUP_ID...")

            if caller != OWNER_ID:
                await message.reply("❌ Kamu bukan owner. Command hanya untuk OWNER.")
                return

            # tampilkan tipe ALLOWED_GROUP_ID untuk debugging
            await message.reply(f"DEBUG: ALLOWED_GROUP_ID = {ALLOWED_GROUP_ID} (type {type(ALLOWED_GROUP_ID)})")

            # coba konversi ke int jika memungkinkan
            try:
                gid = int(ALLOWED_GROUP_ID)
            except Exception:
                gid = ALLOWED_GROUP_ID

            # kirim pesan ke group
            try:
                sent = await client.send_message(gid, f"TEST TREASURE CHEST spawn at {datetime.utcnow().isoformat()} UTC", reply_markup=CHEST_BUTTON)
                await message.reply(f"✅ Pesan terkirim ke group!\ngroup={gid}\nmessage_id={sent.message_id}")
            except Exception as e:
                tb = traceback.format_exc()
                await message.reply(f"❌ Gagal kirim pesan ke group!\nError: {e}\n\nTraceback:\n{tb}")
                logger.exception("Gagal mengirim test message ke group")
        except Exception as e:
            tb = traceback.format_exc()
            await message.reply(f"❌ Error internal spawn_test:\n{e}\n\nTraceback:\n{tb}")
            logger.exception("spawn_test internal error")

    @app.on_callback_query(filters.regex("^TREASURE_CHEST$"))
    async def cb_test(client: Client, cq):
        try:
            uid = cq.from_user.id if cq.from_user else None
            uname = cq.from_user.username if cq.from_user else "unknown"
            await cq.answer("CLAIM received (test)", show_alert=False)
            await cq.message.reply(f"TEST: {uname} ({uid}) klik chest — ini balasan test.")
        except Exception:
            logger.exception("cb_test error")
