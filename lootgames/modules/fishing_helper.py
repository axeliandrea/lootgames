# lootgames/modules/fishing_helper.py
from pyrogram.types import MessageEntity
from pyrogram.enums import MessageEntityType
import logging

logger = logging.getLogger(__name__)

FISHING_EMOJI = {"char": "🎣", "id": 5463406036410969564}

async def send_single_emoji(client, chat_id: int, emoji: dict, text: str = "", reply_to: int = None):
    dummy = "⬛"
    full_text = dummy + text
    entities = [
        MessageEntity(
            type=MessageEntityType.CUSTOM_EMOJI,
            offset=0,
            length=len(dummy),
            custom_emoji_id=int(emoji["id"])
        )
    ]
    try:
        return await client.send_message(chat_id, full_text, entities=entities, reply_to_message_id=reply_to)
    except Exception as e:
        logger.error(f"Gagal kirim emoji ke {chat_id}: {e}")
        return None
