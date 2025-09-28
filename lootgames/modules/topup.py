# lootgames/modules/topup.py
import logging
import re
from pyrogram import Client, filters
from pyrogram.types import Message

from lootgames.config import OWNER_ID
from lootgames.modules import umpan  # integrasi database umpan

logger = logging.getLogger(__name__)

PAYFUN_ID = 5796879502        # ID bot PayFun
CIP_PER_UMPAN = 50            # 1 umpan per 50 cip
MIN_CIP = 250                 # minimal cip
TARGET_GROUP = -1002946278772 # hanya berlaku di group ini
UMPAN_JENIS = "A"             # Common Type A disimpan di database tipe A

# ---------------- REGISTER ---------------- #
def register(app: Client):
    logger.info("[TOPUP] Handler topup terdaftar.")

    # Handler untuk command /cip (hanya di group target & reply OWNER)
    @app.on_message(filters.command("cip") & filters.reply & filters.chat(TARGET_GROUP))
    async def handle_cip(client: Client, message: Message):
        try:
            if not message.reply_to_message or message.reply_to_message.from_user.id != OWNER_ID:
                return  # hanya berlaku jika reply ke OWNER_ID

            args = message.text.split()
            if len(args) < 3 or args[2].lower() != "topup":
                return

            try:
                cip_amount = int(args[1])
            except ValueError:
                return await message.reply("❌ Nominal cip harus angka!")

            if cip_amount < MIN_CIP:
                return await message.reply(f"❌ Minimal topup adalah {MIN_CIP} cip.")

            username = message.from_user.username or f"user{message.from_user.id}"
            logger.info(f"[TOPUP] {username} mencoba topup {cip_amount} cip.")

            # Tandai transaksi → tunggu respon PayFun
            await message.reply(f"⏳ Menunggu konfirmasi topup {cip_amount} cip dari PayFun...")

        except Exception as e:
            logger.error(f"[TOPUP] Error handle_cip: {e}")

    # Handler untuk respon dari PayFun bot (hanya di group target)
    @app.on_message(filters.chat(PAYFUN_ID) & filters.chat(TARGET_GROUP))
    async def handle_payfun(client: Client, message: Message):
        try:
            text = message.text or ""
            # Cek format pesan sukses PayFun
            match = re.search(r"Berhasil Tip Rp(\d+)\s+ke\s+@(\w+)", text)
            if not match:
                return

            amount = int(match.group(1))
            username = match.group(2)

            # Hitung umpan
            pcs = amount // CIP_PER_UMPAN
            if pcs <= 0:
                return

            # Ambil user_id dari username
            try:
                user = await client.get_users(username)
                user_id = user.id
            except Exception:
                user_id = None

            if user_id:
                # Update username agar sinkron
                umpan.update_username(user_id, username)
                # Simpan ke database umpan tipe A
                umpan.add_umpan(user_id, UMPAN_JENIS, pcs)
                logger.info(f"[TOPUP] Database umpan ditambahkan → {username} +{pcs} tipe {UMPAN_JENIS}")

            # Balas ke group
            reply_text = f"@{username} Berhasil topup {pcs} pcs Umpan 🐛 Common Type A"
            await message.reply(reply_text)

            logger.info(f"[TOPUP] {username} topup sukses Rp{amount} → {pcs} umpan diberikan.")

        except Exception as e:
            logger.error(f"[TOPUP] Error handle_payfun: {e}")

    # ---------------- COMMAND .mybait ---------------- #
    @app.on_message(filters.command("mybait") & filters.chat(TARGET_GROUP))
    async def handle_mybait(client: Client, message: Message):
        try:
            user_id = message.from_user.id
            user_data = umpan.get_user(user_id)

            lines = [f"🐛 Stok Umpan @{message.from_user.username or user_id}:"]
            total = 0
            for jenis, data in user_data.items():
                lines.append(f"- {jenis}: {data['umpan']} pcs")
                total += data['umpan']

            lines.append(f"Total semua umpan: {total} pcs")
            await message.reply("\n".join(lines))

        except Exception as e:
            logger.error(f"[TOPUP] Error handle_mybait: {e}")
            await message.reply(f"❌ Terjadi error: {e}")
