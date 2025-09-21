# lootgames/modules/autorespon.py
from pyrogram import filters
from pyrogram.types import Message, MessageEntity
from pyrogram.enums import MessageEntityType

__MODULE__ = "AutoRespon"
__HELP__ = """
Auto respon dengan emoji premium 🤩
Trigger: 'fish', 'fisher', 'lucky', 'fuck', 'kontol', 'anjing'
"""

# Premium emoji ID (ganti sesuai kebutuhan)
PREMIUM_EMOJI_ID = 6235295024817379885

# Kata trigger
TRIGGERS = ["fish", "fisher", "lucky", "fuck", "kontol", "anjing"]

def register(app):
    @app.on_message(filters.group & filters.text, group=2)
    async def auto_reply_premium(client, message: Message):
        text = message.text.lower()

        # Cek apakah ada kata trigger di dalam teks
        if not any(trigger in text for trigger in TRIGGERS):
            return

        # Gunakan dummy char 1-byte supaya entity valid
        dummy_char = "a"

        # Buat entity custom emoji
        entities = [
            MessageEntity(
                type=MessageEntityType.CUSTOM_EMOJI,
                offset=0,
                length=1,
                custom_emoji_id=PREMIUM_EMOJI_ID,
            )
        ]

        # Kirim balasan
        await message.reply(text=dummy_char, entities=entities)
