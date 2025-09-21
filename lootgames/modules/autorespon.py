# lootgames/modules/autorespon.py
from pyrogram import filters
from pyrogram.types import Message, MessageEntity
from pyrogram.enums import MessageEntityType
import logging

__MODULE__ = "AutoRespon"
__HELP__ = """
Auto respon dengan emoji premium 🤩 atau 🖕
Trigger: 
- Kata kasar (exact match): 'fuck', 'kontol', 'anjing'
- Kata fun (substring match): 'fish', 'fisher', 'lucky'
"""

logger = logging.getLogger(__name__)

# Premium emoji ID
PREMIUM_EMOJI_ID = 5257967696124852779

# Kata kasar exact match
EXACT_TRIGGERS = ["fuck", "kontol", "anjing"]
# Kata fun substring match
FUN_TRIGGERS = ["fish", "fisher", "lucky"]

def setup(client):
    """Pasang auto-respon emoji premium ke client aktif"""

    @client.on_message(filters.group & filters.text, group=2)
    async def auto_reply_premium(message: Message):
        text = message.text.lower().strip()

        # Cek kata kasar exact match atau kata fun substring
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
            try:
                await message.reply(text=dummy_char, entities=entities)
                logger.info(f"Auto-reply emoji premium dikirim ke {message.from_user.id}: {text}")
            except Exception as e:
                logger.error(f"Gagal kirim auto-reply: {e}")
