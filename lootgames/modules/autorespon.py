# lootgames/modules/autorespon.py
import re
from pyrogram import filters
from pyrogram.types import Message, MessageEntity
from pyrogram.enums import MessageEntityType

__MODULE__ = "AutoRespon"
__HELP__ = """
Auto respon dengan emoji premium 🤩 atau 🖕
Trigger: 'fish', 'fisher', 'lucky', 'fuck', 'kontol', 'anjing'
"""

PREMIUM_EMOJI_ID = 5257967696124852779
TRIGGERS = ["fish", "fisher", "lucky", "fuck", "kontol", "anjing"]

def register(app):
    @app.on_message(filters.group & filters.text, group=2)
    async def auto_reply_premium(client, message: Message):
        text = message.text.lower().strip()
        pattern = r'\b(?:' + '|'.join(map(re.escape, TRIGGERS)) + r')\b'
        if not re.search(pattern, text):
            return

        dummy_char = "⬛"
        entities = [
            MessageEntity(
                type=MessageEntityType.CUSTOM_EMOJI,
                offset=0,
                length=1,
                custom_emoji_id=PREMIUM_EMOJI_ID,
            )
        ]
        await message.reply(text=dummy_char, entities=entities)
