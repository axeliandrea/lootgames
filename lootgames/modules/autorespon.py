# lootgames/modules/autorespon.py
from pyrogram import filters
from pyrogram.types import Message, MessageEntity
from pyrogram.enums import MessageEntityType

PREMIUM_EMOJI_ID = 5257967696124852779
EXACT_TRIGGERS = ["fuck", "kontol", "anjing"]
FUN_TRIGGERS = ["fish", "fisher", "lucky"]

def setup(client):
    @client.on_message(filters.group & filters.text, group=2)
    async def auto_reply_premium(message: Message):
        text = message.text.lower().strip()
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
