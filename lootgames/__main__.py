import os
import logging
from pyrogram import Client, filters
from lootgames.modules import (
    treasure_chest,
    yapping,
    menu_utama,
    user_database,
    gacha_fishing,
    aquarium,
)
from lootgames.modules.umpan import register_topup
from lootgames.config import (
    API_ID, API_HASH, BOT_TOKEN, OWNER_ID, LOG_LEVEL, LOG_FORMAT
)

# ================= LOGGING ================= #
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# ================= CLIENT ================= #
app = Client(
    "lootgames",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= GLOBAL MESSAGE LOGGER ================= #
@app.on_message()
async def _debug_all_messages(client, message):
    try:
        uid = message.from_user.id if message.from_user else "NONE"
        uname = message.from_user.username if message.from_user else "NONE"
        ctype = message.chat.type if message.chat else "NONE"
        text = message.text or message.caption or "<non-text>"
        print(f"[ALL MSG][{uid}][{uname}] chat_type={ctype} -> {repr(text)}")
    except Exception as e:
        print("[ALL MSG][ERR]", e)

# ================= REGISTER MODULES ================= #
print("[MAIN] Mendaftarkan modules...")
treasure_chest.register(app)  # prioritas command private
yapping.register(app)
menu_utama.register(app)
user_database.register(app)
register_topup(app)
print("[MAIN] Semua module dipanggil register (check logs untuk konfirmasi).")

# ================= STORAGE ================= #
os.makedirs("storage", exist_ok=True)

# ================= OWNER START COMMAND ================= #
@app.on_message(filters.private & filters.user(OWNER_ID) & filters.command("start", prefixes=["/"]))
async def notify_owner(client, message):
    try:
        await message.reply("🤖 LootGames Bot sudah aktif.")
    except Exception as e:
        logger.error(f"Gagal kirim notifikasi start ke owner: {e}")

# ================= RUN BOT ================= #
print("[MAIN] Bot starting...")
app.run()
