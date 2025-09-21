# lootgames/modules/autorespon.py
from pyrogram import filters
from pyrogram.types import Message, MessageEntity
from pyrogram.enums import MessageEntityType

__MODULE__ = "AutoRespon"
__HELP__ = """
Auto respon dengan emoji premium 🤩 atau 🖕
Trigger: 'fish', 'fisher', 'lucky', 'fuck', 'kontol', 'anjing'
"""

# Premium emoji ID (sesuaikan dengan botmu)
PREMIUM_EMOJI_ID = 5257967696124852779

# Daftar trigger
TRIGGERS = ["fish", "fisher", "lucky", "fuck", "kontol", "anjing"]

def register(app):
    @app.on_message(filters.group & filters.text, group=2)
    async def auto_reply_premium(client, message: Message):
        text = message.text.lower().strip()

        # Trigger check: exact match untuk kata kasar, substring match untuk kata lain
        if any(text == t for t in ["fuck", "kontol", "anjing"]) or any(t in text for t in ["fish", "fisher", "lucky"]):
            # Dummy char untuk emoji premium
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

            # Kirim balasan emoji premium
            await message.reply(text=dummy_char, entities=entities)
