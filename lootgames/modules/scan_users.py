# lootgames/modules/scan_users.py
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from lootgames.config import API_ID, API_HASH, BOT_TOKEN
from lootgames.modules import database_group as db

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ================= CLIENT ================= #
app = Client(
    "lootgames_scan",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= HANDLER JOIN ================= #
async def join_handler(client: Client, message: Message):
    user = message.from_user
    user_id = user.id
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    username = user.username or first_name

    # masukkan ke database
    db.add_user(user_id, username)

    # log
    logger.info(f"✅ User terdaftar via .join: {user_id} | {full_name} | {first_name} | {last_name}")

    # balas user
    await message.reply(
        f"🎉 Kamu berhasil join!\n\n"
        f"ID: {user_id}\n"
        f"Nama Lengkap: {full_name}\n"
        f"Nama Depan: {first_name}\n"
        f"Nama Belakang: {last_name}\n"
        f"Username: @{username}"
    )

# ================= REGISTER HANDLER ================= #
def register(app: Client):
    app.add_handler(
        app.add_handler(
            filters=filters.private & filters.command("join", prefixes="."),
            callback=join_handler
        )
    )

# ================= RUN MANUAL ================= #
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    app.add_handler(
        filters=filters.private & filters.command("join", prefixes="."),
        callback=join_handler
    )
    asyncio.run(app.run())
