# lootgames/modules/autorespon.py
from pyrogram import filters
from pyrogram.types import Message, MessageEntity
from pyrogram.enums import MessageEntityType
from lootgames import client  # pastikan ini instance Pyrogram aktif

__MODULE__ = "AutoRespon"
__HELP__ = """
Auto respon dengan emoji premium 🤩 atau 🖕
Trigger: 'fish', 'fisher', 'lucky', 'fuck', 'kontol', 'anjing'
"""

PREMIUM_EMOJI_ID = 5257967696124852779

# Kata kasar exact match
EXACT_TRIGGERS = ["fuck", "kontol", "anjing"]
# Kata fun substring match
FUN_TRIGGERS = ["fish", "fisher", "lucky"]

@client.on_message(filters.group & filters.text, group=2)
async def auto_reply_premium(message: Message):
    text = message.text.lower().strip()

    # Cek kata kasar (exact) dan kata fun (substring)
    if text in EXACT_TRIGGERS or any(f in text for f in FUN_TRIGGERS):
        dummy_char = "⬛"
        entities = [
            MessageEntity(
                type=MessageEntityType.CUSTOM_EMOJI,
                offset=0,
                length=1,
                custom_emoji_id=PREMIUM_EMOJI_ID
            )
        ]
        await message.reply(text=dummy_char, entities=entities)
