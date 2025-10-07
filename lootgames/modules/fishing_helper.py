# lootgames/modules/fishing_helper.py
import logging
from typing import Optional, Dict
from pyrogram import Client
from pyrogram.types import MessageEntity
from pyrogram.enums import MessageEntityType

logger = logging.getLogger(__name__)

# 🎣 Emoji default untuk fishing
FISHING_EMOJI = {"char": "🎣", "id": 5463406036410969564}


async def send_single_emoji(
    client: Client,
    chat_id: int,
    emoji: Dict,
    text: str = "",
    reply_to: Optional[int] = None
):
    """
    Mengirim satu emoji custom dengan teks opsional ke chat.
    
    Args:
        client (Client): instance Pyrogram client.
        chat_id (int): ID chat tujuan.
        emoji (dict): {'char': str, 'id': int} emoji custom.
        text (str, optional): teks tambahan. Defaults ke "".
        reply_to (int, optional): ID pesan untuk reply. Defaults ke None.
    
    Returns:
        Message | None: pesan terkirim atau None jika error.
    """
    dummy = "⬛"  # placeholder untuk custom emoji
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
        return await client.send_message(
            chat_id=chat_id,
            text=full_text,
            entities=entities,
            reply_to_message_id=reply_to
        )
    except Exception as e:
        logger.error(f"[FISHING_HELPER] Gagal kirim emoji ke {chat_id}: {e}")
        return None
