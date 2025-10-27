# lootgames/__main__.py (WEBHOOK + MAIN)
import asyncio
import threading
import logging
import os
import json
import sys
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.handlers import CallbackQueryHandler
from flask import Flask, request

# ================= CONFIG ================= #
from lootgames.config import (
    API_ID,
    API_HASH,
    BOT_TOKEN,
    OWNER_ID,
    ALLOWED_GROUP_ID,
    LOG_LEVEL,
    LOG_FORMAT,
)

# ================= LOGGING ================= #
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pyrogram.session").setLevel(logging.WARNING)

# ================= CLIENT PYROGRAM ================= #
app = Client(
    "lootgames",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= IMPORT MODULES ================= #
from lootgames.modules import yapping, menu_utama, user_database, gacha_fishing, aquarium, umpan

# ================= FILE HISTORY ================= #
HISTORY_FILE = "storage/topup_history.json"
os.makedirs("storage", exist_ok=True)

WEBHOOK_URL = "https://preelemental-marth-exactly.ngrok-free.dev/webhook/saweria"

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_history_entry(uid, entry):
    data = load_history()
    if uid not in data:
        data[uid] = []
    data[uid].append(entry)
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"🧾 History top-up disimpan untuk {uid}")

# ================= PEMBULATAN & HITUNG UMPAN ================= #
def normalize_amount(amount):
    if amount >= 50000:
        return 50000
    elif amount >= 10000:
        return 10000
    elif amount >= 5000:
        return 5000
    elif amount >= 1000:
        return 1000
    else:
        return 1000

def calculate_umpan(amount, tipe):
    """
    Hitung jumlah umpan berdasarkan tipe dan nominal.
    Umpan A: 1 pcs = 50
    Umpan B: 1 pcs = 500
    """
    if tipe == "A":
        return int(amount // 50)
    elif tipe == "B":
        return int(amount // 500)
    return 0


# ================= FLASK WEBHOOK ================= #
webhook_app = Flask("saweria_webhook")

@webhook_app.route("/webhook/saweria", methods=["POST"])
def saweria_webhook():
    data = request.json
    if not data:
        return {"status": "invalid"}, 400

    try:
        donor_field = data.get("donator_name") or data.get("donator", {}).get("name") or data.get("dari") or "Donatur"
        pesan = (data.get("message") or data.get("pesan") or "").upper().strip()
        amount = float(data.get("amount_raw", 0) or data.get("amount", 0))
        transaction_id = data.get("id", "")
        timestamp_str = data.get("tanggal") or data.get("time")

        # --- parsing waktu ---
        try:
            tx_time = datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M")
        except Exception:
            tx_time = datetime.utcnow()

        # --- deteksi tipe umpan ---
        if "B" in pesan:
            umpan_type = "B"
        elif "A" in pesan:
            umpan_type = "A"
        else:
            logger.info(f"❌ Tidak ada kode umpan dalam pesan: '{pesan}'")
            return {"status": "ignored"}, 200

        nominal = normalize_amount(amount)
        umpan_bonus = calculate_umpan(nominal, umpan_type)

        # --- gunakan user_id langsung ---
        try:
            user_id = int(donor_field)
            uid_str = str(user_id)
            username = f"user{user_id}"
        except ValueError:
            user_id = None
            uid_str = f"anon_{donor_field.replace(' ', '_')}"
            username = donor_field

        # --- tambah umpan ke database ---
        try:
            umpan.add_umpan(uid_str, umpan_type, umpan_bonus)
            umpan.update_username(uid_str, username)
        except Exception as e:
            logger.error(f"❌ Gagal menambah umpan: {e}")

        # --- simpan history ---
        save_history_entry(uid_str, {
            "id": transaction_id,
            "username": username,
            "amount": nominal,
            "bonus": umpan_bonus,
            "type": umpan_type,
            "status": "success",
            "timestamp": tx_time.timestamp()
        })

        # --- kirim notifikasi Telegram ---
        async def send_msg():
            msg_text = (
                f"💚 Terima kasih {username}!\n"
                f"Donasi Rp{int(nominal):,} berhasil ✅\n"
                f"🎣 Kamu mendapatkan {umpan_bonus} umpan {umpan_type}"
            )
            owner_text = (
                f"💸 Donasi diterima dari {username}\n"
                f"Rp{int(nominal):,} → {umpan_bonus} umpan {umpan_type}\n"
                f"ID: {transaction_id}"
            )
            try:
                if user_id:
                    await app.send_message(user_id, msg_text)
                await app.send_message(OWNER_ID, owner_text)
            except Exception as e:
                logger.error(f"Gagal kirim pesan Telegram: {e}")

        asyncio.run_coroutine_threadsafe(send_msg(), app.loop)

        logger.info(f"✅ Donasi berhasil: {username}, amount={amount}, tipe={umpan_type}, bonus={umpan_bonus}, uid={uid_str}")
        return {"status": "ok"}, 200

    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return {"status": "error", "message": str(e)}, 500


def run_flask():
    webhook_app.run(host="0.0.0.0", port=8080)

# ================= COMMAND /RESTART ================= #
@app.on_message(filters.command("restart") & filters.user(OWNER_ID))
async def restart_bot(client, message):
    await message.reply_text("♻️ Bot sedang direstart, tunggu sebentar...")
    logger.info("♻️ Perintah restart diterima, bot akan restart...")

    await asyncio.sleep(2)

    # Pastikan direktori kerja berada di root project
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.chdir("..")  # naik 1 folder ke root (bukan /lootgames/lootgames)

    # Jalankan ulang dengan path yang benar
    os.execv(sys.executable, [sys.executable, "-m", "lootgames"])

# ================= STARTUP TASK ================= #
async def startup_tasks():
    logger.info("🔹 Menjalankan startup worker fishing...")
    asyncio.create_task(gacha_fishing.fishing_worker(app))

# ================= REGISTER MODULES ================= #
def safe_register(module, name: str):
    try:
        module.register(app)
        logger.info(f"Module {name} registered ✅")
    except AttributeError:
        logger.warning(f"Module {name} tidak memiliki fungsi register()")

safe_register(yapping, "yapping")
safe_register(menu_utama, "menu_utama")

if not hasattr(menu_utama, "register_sedekah_handlers"):
    def register_sedekah_handlers(app):
        logger.debug("[DEBUG] register_sedekah_handlers() dummy aktif ✅")
    menu_utama.register_sedekah_handlers = register_sedekah_handlers
menu_utama.register_sedekah_handlers(app)
logger.info("📦 Sedekah Treasure handler registered ✅")

if not hasattr(user_database, "register"):
    def dummy_register(app):
        logger.info("[INFO] user_database register() dummy dipanggil")
    user_database.register = dummy_register
user_database.register(app)

# ================= CALLBACK FISHING ================= #
async def fishing_callback_handler(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username or f"user{user_id}"

    if data.startswith("FISH_CONFIRM_"):
        jenis = data.replace("FISH_CONFIRM_", "")
        from lootgames.modules.menu_utama import TARGET_GROUP
        try:
            await callback_query.message.edit_text(f"🎣 Kamu memancing dengan umpan {jenis}!")
            await gacha_fishing.fishing_loot(
                client,
                TARGET_GROUP,
                username,
                user_id,
                umpan_type=jenis
            )
        except Exception as e:
            logger.error(f"Gagal proses fishing_loot: {e}")

app.add_handler(CallbackQueryHandler(fishing_callback_handler))

# ================= MAIN BOT ================= #
async def main():
    os.makedirs("storage", exist_ok=True)

    # Jalankan Flask webhook di thread terpisah
    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("🚀 Flask webhook server dijalankan di port 8080")

    # Start Pyrogram
    await app.start()
    logger.info("🚀 LOOT Games Bot started!")
    logger.info(f"📱 Monitoring group: {ALLOWED_GROUP_ID}")
    logger.info(f"👑 Owner ID: {OWNER_ID}")

    # Jalankan startup worker
    await startup_tasks()

    # Kirim notifikasi ke owner
    try:
        await app.send_message(OWNER_ID, "🤖 LOOT Games Bot sudah aktif ya!")
        logger.info("📢 Notifikasi start terkirim ke OWNER.")
    except Exception as e:
        logger.error(f"Gagal kirim notifikasi start: {e}")

    logger.info("[MAIN] Bot berjalan, tekan Ctrl+C untuk berhenti.")
    await asyncio.Event().wait()

# ================= ENTRY POINT ================= #
if __name__ == "__main__":
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass
    asyncio.run(main())



