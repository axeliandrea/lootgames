from pyrogram import Client, filters
from pyrogram.types import Message, MessageEntity
from pyrogram.enums import MessageEntityType

__MODULE__ = "AutoFuck"
__HELP__ = """
Auto respon dengan emoji premium 🖕
Trigger: 'fuck', 'kontol', 'anjing'
"""

# Premium emoji ID
PREMIUM_EMOJI_ID = 5257967696124852779

@app.on_message(filters.group & filters.text, group=2)
async def auto_fuck_reply(client, message: Message):
    text = message.text.lower().strip()

    if text not in ["fuck", "kontol", "anjing"]:
        return

    entities = [
        MessageEntity(
            type=MessageEntityType.CUSTOM_EMOJI,
            offset=0,
            length=1,  # selalu 1 untuk dummy char
            custom_emoji_id=PREMIUM_EMOJI_ID,
        )
    ]

    # pakai dummy text (⬛), nanti Telegram render jadi emoji premium
    await message.reply(text="⬛", entities=entities)
