import logging
from pyrogram import filters

logger = logging.getLogger(__name__)

OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772  # ID group target

def register(app):
    logger.info("[CHEST] Registering treasure_chest module (minimal test)...")

    # ================= PRIVATE COMMAND FOR OWNER ================= #
    @app.on_message(filters.private & filters.command("treasurechest", prefixes=["."]))
    async def treasure_handler(client, message):
        # Hanya owner yang bisa trigger
        if message.from_user.id != OWNER_ID:
            await message.reply("❌ Kamu bukan owner.")
            return

        await message.reply("⏳ Preparing kirim chest (test)...")

        try:
            # Kirim chat biasa ke group tanpa tombol
            await client.send_message(
                chat_id=TARGET_GROUP,
                text="TEST CHEST - pesan dari owner"
            )
            await message.reply(f"✅ Berhasil kirim TEST CHEST ke group {TARGET_GROUP}")
        except Exception as e:
            logger.error(f"[CHEST] Gagal kirim chest: {e}")
            await message.reply(f"❌ Gagal kirim chest: {e}")
