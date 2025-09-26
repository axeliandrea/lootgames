# lootgames/modules/treasure_chest.py
import random
import json
import os
import logging
import traceback
from threading import Lock
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.config import OWNER_ID, ALLOWED_GROUP_ID
from lootgames.modules import umpan

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ================= CONFIG ================= #
CHEST_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton("💎 TREASURE CHEST", callback_data="TREASURE_CHEST")]]
)
CHEST_DB = "storage/treasure_claim.json"
STORAGE_DIR = "storage"
LOCK = Lock()

# ================= DB HELPERS (thread-safe) ================= #
def ensure_storage():
    os.makedirs(STORAGE_DIR, exist_ok=True)

def load_claims():
    ensure_storage()
    with LOCK:
        if not os.path.exists(CHEST_DB):
            return {}
        try:
            with open(CHEST_DB, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.exception("Gagal load_claims, mengembalikan {}")
            return {}

def save_claims(db: dict):
    ensure_storage()
    with LOCK:
        with open(CHEST_DB, "w") as f:
            json.dump(db, f, indent=2)

def reset_claims():
    save_claims({})

# ================= UTIL NOTIFY OWNER ================= #
async def notify_owner(client: Client, text: str):
    try:
        await client.send_message(OWNER_ID, f"[TREASURE DEBUG]\n{text}")
    except Exception as e:
        logger.exception("Gagal kirim notifikasi ke OWNER")

# ================= COMMAND (spawn chest) ================= #
async def spawn_chest(client: Client, message: Message):
    """Owner kirim .treasure_chest di private untuk spawn di grup"""
    try:
        if not message.from_user:
            return
        if message.from_user.id != OWNER_ID:
            await message.reply("❌ Kamu bukan owner!")
            return

        # reset klaim untuk chest baru
        reset_claims()

        text_send = (
            "🎁 **TREASURE CHEST SPAWN!** 🎁\n\n"
            "Klik tombol di bawah untuk klaim (1x per user).\n\n"
            "— Good luck!"
        )

        sent = await client.send_message(
            ALLOWED_GROUP_ID,
            text_send,
            reply_markup=CHEST_BUTTON
        )

        # konfirmasi ke owner (super debug)
        owner_info = (
            f"Chest dikirim ke group: {ALLOWED_GROUP_ID}\n"
            f"Message ID: {sent.message_id}\n"
            f"Waktu: {datetime.utcnow().isoformat()} UTC\n"
            f"Claims DB reset berhasil."
        )
        await message.reply(f"✅ Chest berhasil dikirim ke group!\n\n{owner_info}")
        await notify_owner(client, owner_info)
        logger.info("[TREASURE] Chest spawned di group. " + owner_info)

    except Exception as e:
        err = traceback.format_exc()
        logger.exception("Gagal spawn chest")
        await message.reply(f"❌ Error spawn chest:\n{e}")
        await notify_owner(client, f"Gagal spawn chest:\n{err}")

# ================= CALLBACK (klik tombol) ================= #
async def chest_callback(client: Client, callback_query: CallbackQuery):
    try:
        if not callback_query.from_user:
            return

        user = callback_query.from_user
        user_id = str(user.id)
        username = user.username or user.first_name or user_id
        chat = callback_query.message.chat if callback_query.message else None
        chest_msg_id = callback_query.message.message_id if callback_query.message else None

        # load claims
        claims = load_claims()

        # already claimed?
        if user_id in claims:
            # super-debug: inform user and owner
            await callback_query.answer("❌ Kamu sudah klaim chest ini!", show_alert=True)
            logger.debug(f"[TREASURE] Duplicate claim attempt by {username} ({user_id})")
            await notify_owner(client, f"Duplicate claim by {username} ({user_id}) in chat {chat.id if chat else 'unknown'} message {chest_msg_id}")
            return

        # roll random (1..100)
        roll = random.randint(1, 100)
        logger.debug(f"[TREASURE] Roll for {username} ({user_id}) = {roll}")

        # 10% Umpan A, 90% Zonk
        if roll <= 10:
            # ensure user exists in umpan DB
            umpan.init_user_if_missing(int(user_id), username)
            try:
                umpan.add_umpan(int(user_id), "A", 1)
                result_text = f"🎉 {username} membuka chest dan mendapat **Umpan Common (A)**!"
                logger.info(f"[TREASURE] {username} ({user_id}) mendapat Umpan A")
            except Exception as e:
                # jika add_umpan error, catat dan beri tahu owner
                logger.exception("Gagal add_umpan untuk user")
                await notify_owner(client, f"Gagal add_umpan untuk {username} ({user_id}):\n{traceback.format_exc()}")
                result_text = f"⚠️ Terjadi error saat menambahkan umpan ke {username}. Owner diberi tahu."
        else:
            result_text = f"💨 {username} membuka chest, tapi isinya kosong (Zonk)."
            logger.info(f"[TREASURE] {username} ({user_id}) zonk (roll {roll})")

        # simpan klaim (thread-safe)
        claims[user_id] = {
            "username": username,
            "time": datetime.utcnow().isoformat(),
            "roll": roll,
            "result": result_text,
            "chest_message_id": chest_msg_id
        }
        save_claims(claims)

        # balas ke group (tidak sebagai alert)
        await callback_query.answer("✅ Chest dibuka!", show_alert=False)
        await callback_query.message.reply(result_text)

        # super-debug notify owner tentang klaim baru
        summary = (
            f"Claim oleh: {username} ({user_id})\n"
            f"Chat: {chat.title if chat and getattr(chat,'title',None) else chat.id if chat else 'unknown'}\n"
            f"Chest message id: {chest_msg_id}\n"
            f"Roll: {roll}\n"
            f"Result: {result_text}\n"
            f"Total claims now: {len(claims)}"
        )
        await notify_owner(client, summary)
        logger.debug("[TREASURE] " + summary)

    except Exception as e:
        err = traceback.format_exc()
        logger.exception("Gagal proses chest_callback")
        try:
            await callback_query.answer("❌ Terjadi error saat klaim, owner diberi tahu", show_alert=True)
        except:
            pass
        await notify_owner(client, f"Error chest_callback:\n{err}")

# ================= EXTRA OWNER COMMANDS (debug) ================= #
async def chest_status(client: Client, message: Message):
    """Owner-only: tampilkan status klaim saat ini"""
    try:
        if not message.from_user or message.from_user.id != OWNER_ID:
            return await message.reply("❌ Kamu bukan owner!")
        claims = load_claims()
        total = len(claims)
        lines = [f"Total claims: {total}"]
        for uid, data in claims.items():
            lines.append(f"- {data.get('username')} ({uid}) : {data.get('result')} at {data.get('time')}")
        text = "\n".join(lines) if lines else "No claims yet."
        await message.reply(f"📋 Chest status:\n\n{text}")
        logger.debug("[TREASURE] Owner requested chest status")
    except Exception as e:
        logger.exception("Gagal chest_status")
        await message.reply(f"❌ Error: {e}")
        await notify_owner(client, f"Error chest_status:\n{traceback.format_exc()}")

# ================= REGISTER ================= #
def register(app: Client):
    # spawn command: .treasure_chest in private (owner only)
    app.add_handler(MessageHandler(spawn_chest, filters.private & filters.command("treasure_chest", prefixes=".")))

    # owner debug: .chest_status in private
    app.add_handler(MessageHandler(chest_status, filters.private & filters.command("chest_status", prefixes=".")))

    # callback handler for inline button (TREASURE_CHEST)
    app.add_handler(CallbackQueryHandler(chest_callback, filters.regex("^TREASURE_CHEST$")))

    logger.info("treasure_chest module registered")
