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
Debug mode aktif: semua pesan masuk akan dicetak di console.
"""

logger = logging.getLogger(__name__)

# Premium emoji ID
PREMIUM_EMOJI_ID = 5257967696124852779

# Kata kasar exact match
EXACT_TRIGGERS = ["fuck", "kontol", "anjing"]
# Kata fun substring match
FUN_TRIGGERS = ["fish", "fisher", "lucky"]

def setup(client, debug: bool = True):
    """Pasang auto-respon emoji premium ke client aktif"""
    
    @client.on_message(filters.group & filters.text, group=2)
    async def auto_reply_premium(_, message: Message):
        text = message.text.lower().strip()
        
        if debug:
            logger.debug(f"[DEBUG] Pesan masuk dari {message.from_user.username or message.from_user.id}: {text}")
        
        matched_trigger = None

        # Cek kata kasar exact match
        if text in EXACT_TRIGGERS:
            matched_trigger = text
        # Cek kata fun substring
        else:
            for f in FUN_TRIGGERS:
                if f in text:
                    matched_trigger = f
                    break

        if matched_trigger:
            if debug:
                logger.debug(f"[DEBUG] Trigger cocok: {matched_trigger}")

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
