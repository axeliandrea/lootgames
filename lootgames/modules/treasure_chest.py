# lootgames/modules/treasure_chest.py
import logging
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772  # pastikan ini grup target yang benar

def register(app):
    @app.on_message(filters.private & filters.user(OWNER_ID) & filters.regex(r"^\.treasurechest$"))
    async def send_treasure_chest(client, message):
        logger.info("[CHEST] Command .treasurechest dipanggil!")
        try:
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("💎 Ambil Treasure!", callback_data="open_treasure")]]
            )

            sent = await client.send_message(
                chat_id=TARGET_GROUP,
                text="🎁 Sebuah **Treasure Chest** muncul di tengah laut!\n\nKlik tombol di bawah untuk membuka kunci.",
                reply_markup=keyboard
            )

            await message.reply("✅ Treasure chest berhasil dikirim ke grup.")
            logger.info(f"[CHEST] Chest terkirim ke {TARGET_GROUP} -> msg_id={sent.id}")

        except Exception as e:
            logger.error(f"[CHEST] Error kirim chest: {e}")
            await message.reply(f"❌ Gagal kirim chest:\n`{e}`")
