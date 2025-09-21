# lootgames/modules/autorespon.py
from pyrogram import filters
from pyrogram.types import Message, MessageEntity
from pyrogram.enums import MessageEntityType

__MODULE__ = "AutoRespon"
__HELP__ = """
Auto respon dengan emoji premium 🤩 atau 🖕
Trigger: 'fish', 'fisher', 'lucky', 'fuck', 'kontol', 'anjing'
"""

# Premium emoji ID (ganti sesuai bot)
PREMIUM_EMOJI_ID = 5257967696124852779  # contoh sama seperti AutoFuck

# Kata trigger
TRIGGERS = ["fish", "fisher", "lucky", "fuck", "kontol", "anjing"]

def register(app):
    @app.on_message(filters.group & filters.text, group=2)
    async def auto_reply_premium(client, message: Message):
        text = message.text.lower().strip()

        # Cek apakah ada kata trigger di teks
        if not any(trigger in text for trigger in TRIGGERS):
            return

        # Gunakan dummy char ⬛ yang pasti valid
        dummy_char = "⬛"

        # Buat entity custom emoji
        entities = [
            MessageEntity(
                type=MessageEntityType.CUSTOM_EMOJI,
                offset=0,
                length=1,
                custom_emoji_id=PREMIUM_EMOJI_ID,
            )
        ]

        # Balas pesan dengan premium emoji
        await message.reply(text=dummy_char, entities=entities)
