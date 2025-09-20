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

# ================= FUNCTION AUTO SCAN ================= #
async def auto_scan_users():
    """
    Scan semua user yang pernah chat bot di private chat
    dan pastikan ada di database global.
    """
    logger.info("🔍 Mulai auto-scan users yang pernah chat bot...")
    try:
        async for dialog in app.get_dialogs():
            if dialog.chat.type == "private":
                user = dialog.chat
                user_id = user.id
                username = user.username or user.first_name
                full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                first_name = user.first_name or ""
                last_name = user.last_name or ""

                # tambahkan user ke database
                db.add_user(user_id, username)
                # simpan data lengkap ke database (optional tambahan)
                data = db.load_db()
                data[str(user_id)].update({
                    "full_name": full_name,
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username
                })
                db.save_db(data)

                logger.info(f"✅ Auto-scan user: {user_id} | {full_name} | @{username}")
    except Exception as e:
        logger.error(f"❌ Gagal auto-scan users: {e}")

# ================= HANDLER .JOIN ================= #
@app.on_message(filters.private & filters.command("join", prefixes="."))
async def join_handler(client: Client, message: Message):
    user = message.from_user
    user_id = user.id
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    username = user.username or first_name

    # masukkan ke database
    db.add_user(user_id, username)
    data = db.load_db()
    data[str(user_id)].update({
        "full_name": full_name,
        "first_name": first_name,
        "last_name": last_name,
        "username": username
    })
    db.save_db(data)

    logger.info(f"✅ User terdaftar via .join: {user_id} | {full_name} | @{username}")

    # balas user
    await message.reply(
        f"🎉 Kamu berhasil join!\n\n"
        f"ID: {user_id}\n"
        f"Nama Lengkap: {full_name}\n"
        f"Nama Depan: {first_name}\n"
        f"Nama Belakang: {last_name}\n"
        f"Username: @{username}"
    )

# ================= RUN BOT ================= #
async def main():
    await app.start()
    logger.info("🚀 Bot scan/join started!")
    # Auto-scan seluruh user yang pernah chat
    await auto_scan_users()
    logger.info("🎯 Auto-scan selesai, bot siap menerima .join command")
    await asyncio.Event().wait()  # biar bot tetap jalan

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
