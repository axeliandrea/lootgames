#   # 
# lootgames/modules/menu_utama.py
import os
import time  # pastikan ada di top imports
import logging
import asyncio
import re
import httpx
import random
import json
import tempfile
from collections import defaultdict
from pyrogram import Client, filters
from lootgames.__main__ import load_history
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.modules import yapping, umpan, user_database
from lootgames.modules import fizz_coin
from lootgames.modules import aquarium
from lootgames.modules.gacha_fishing import fishing_loot
from datetime import datetime, timezone, timedelta
from lootgames.modules.utils import save_topup_history, calculate_umpan

WEBHOOK_URL = "https://preelemental-marth-exactly.ngrok-free.dev/webhook/saweria"

logger = logging.getLogger(__name__)
OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772 # ganti sesuai supergroup bot (-1002904817520 TRIAL , -1002946278772 LOOT) #

# ---------------- STATE ---------------- #
TRANSFER_STATE = {}       # user_id: {"jenis": "A/B/C/D"}
TUKAR_POINT_STATE = {}    # user_id: {"step": step, "jumlah_umpan": n}
OPEN_MENU_STATE = {}      # user_id: True jika menu aktif
LOGIN_STATE = {}  # user_id: {"last_login_day": int, "streak": int, "umpan_given": set()}
STREAK_REWARDS = {1: 0, 2: 5, 3: 6, 4: 7, 5: 8, 6: 9, 7: 10}


#fizz coin
TUKAR_COIN_STATE = {}  # user_id: {"jenis": "A" atau "B"}
# ---------------- PATH DB ---------------- #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # folder modules
DB_FILE = os.path.join(BASE_DIR, "../storage/fizz_coin.json")  # ke folder storage
# pastikan folder storage ada
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

# ----------------- INISIALISASI -----------------
AUTO_FISH_TASKS = {}
user_last_fishing = defaultdict(lambda: 0)  # cooldown 10 detik per user
user_task_count = defaultdict(lambda: 0)   # generate task ID unik per user

# ----------------- TREASURE CHEST -----------------
# TREASURE CHEST
TREASURE_FILE = "storage/treasure_chest.json"
os.makedirs(os.path.dirname(TREASURE_FILE), exist_ok=True)
# lock untuk mencegah race condition pada klaim treasure (single-process)
TREASURE_LOCK = asyncio.Lock()

SEDEKAH_FILE = "storage/sedekah_tc.json"
os.makedirs(os.path.dirname(SEDEKAH_FILE), exist_ok=True)
SEDEKAH_LOCK = asyncio.Lock()
SEDEKAH_STATE = {}
SEDEKAH_EXPIRE_SECONDS = 60  # 1 menit

CHEST_EXPIRE_SECONDS = 60  # 1 menit

# ================= FILE I/O ================= #
def load_treasure_data():
    """Load file chest data (auto reset jika rusak)."""
    if not os.path.exists(TREASURE_FILE):
        data = {"chest_id": 0, "claimed_users": [], "created_at": 0}
        with open(TREASURE_FILE, "w") as f:
            json.dump(data, f)
        return data
    try:
        with open(TREASURE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        # jika file korup, reset baru
        data = {"chest_id": 0, "claimed_users": [], "created_at": 0}
        with open(TREASURE_FILE, "w") as f:
            json.dump(data, f)
        return data


def save_treasure_data(data):
    """Simpan data secara atomic (anti rusak saat crash)."""
    tmpfd, tmpname = tempfile.mkstemp(dir=os.path.dirname(TREASURE_FILE) or ".")
    try:
        with os.fdopen(tmpfd, "w") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmpname, TREASURE_FILE)
    except Exception:
        try:
            os.remove(tmpname)
        except Exception:
            pass
        raise


def is_chest_expired(data: dict) -> bool:
    """Cek apakah chest sudah lewat 1 jam"""
    if "created_at" not in data or data["created_at"] == 0:
        return True
    return (time.time() - data["created_at"]) > CHEST_EXPIRE_SECONDS


# ================= SEND CHEST ================= #
async def send_treasure_chest(client, cq):
    """Owner kirim chest baru ke group"""
    data = load_treasure_data()
    data["chest_id"] = data.get("chest_id", 0) + 1
    data["claimed_users"] = []
    data["created_at"] = time.time()
    save_treasure_data(data)

    # Tombol klaim di grup
    keyboard_group = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Claim Treasure Chest", callback_data="TREASURE_CLAIM")]
    ])

    # Kirim info ke grup
    await client.send_message(
        TARGET_GROUP,
        "🎉 **Treasure Chest Spawned!** 🎉\n\n"
        "Expired in 1 minutues",
        reply_markup=keyboard_group
    )

    # Tombol kembali di DM owner
    keyboard_owner = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data="main")]
    ])

    # Edit pesan di private chat owner
    await cq.message.edit_text(
        "📦 Treasure Chest send to Loot!\n\n"
        "✅ Treasure Chest Spawned Successfully.\n\n"
        "Back to Main Menu.",
        reply_markup=keyboard_owner
    )

    print(f"[TREASURE] Chest #{data['chest_id']} dikirim ke group oleh owner.")


# ================= HANDLE CLAIM ================= #
async def handle_treasure_claim(client, cq):
    """Player klaim chest — versi aman dari double claim"""
    user_id = cq.from_user.id
    uname = cq.from_user.username or f"user{user_id}"

    async with TREASURE_LOCK:
        data = load_treasure_data()

        # Cek apakah chest sudah hangus
        if is_chest_expired(data):
            await cq.answer("⏳ Treasure Chest sudah hangus.", show_alert=True)
            return

        # Cek apakah sudah klaim
        if user_id in data.get("claimed_users", []):
            await cq.answer("❌ Kamu sudah klaim Treasure Chest ini!", show_alert=True)
            return

        # Tambahkan user ke daftar klaim (agar langsung terkunci)
        data.setdefault("claimed_users", []).append(user_id)
        save_treasure_data(data)

    # ====== Di luar lock, lakukan roll hadiah ====== #
    roll = random.random()
    if roll < 0.5:
        hadiah = "🤧 Zonk"
        text = f"😜 Sian deh lu! @{uname}, You got Zonk!"
        await asyncio.sleep(1)
    elif roll < 0.95:
        hadiah = "🐛 Umpan Common (Type A)"
        try:
            umpan.add_umpan(user_id, "A", 2)
        except Exception as e:
            print(f"[TREASURE][ERROR] Gagal add umpan A: {e}")
        text = f"🐛 @{uname} Got **1 Common (Type A)**!"
        await asyncio.sleep(2)
    else:
        hadiah = "🐌 Umpan Rare (Type B)"
        try:
            umpan.add_umpan(user_id, "B", 1)
        except Exception as e:
            print(f"[TREASURE][ERROR] Gagal add umpan B: {e}")
        text = f"🐌 @{uname} Got **1 Rare (Type B)**! 🥳"
        await asyncio.sleep(3)

    # Kirim konfirmasi
    await cq.answer("✅ Hadiah berhasil diklaim!", show_alert=True)
    await cq.message.reply_text(text)

    print(f"[TREASURE] @{uname} klaim chest #{data.get('chest_id')} -> {hadiah}")

# ===================================================================== #
# ---------------- HANDLE INPUT ---------------- #
# ---------------- HANDLE INPUT ---------------- #
async def handle_sedekah_input(client, message: Message):
    """Menangani input slot penerima untuk sedekah"""
    user_id = message.from_user.id
    state = SEDEKAH_STATE.get(user_id)
    if not state:
        return

    step = state.get("step")
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.reply("⚠️ Harus berupa angka. Coba lagi.")
        return
    slot_value = int(text)

    # STEP INPUT SLOT PENERIMA
    if step == "await_slot_input":
        amount = state.get("amount")
        jenis = state.get("jenis")

        if slot_value < 5 or slot_value > 100:
            await message.reply("⚠️ Slot penerima harus 5 - 100.")
            return
        if slot_value > amount:
            await message.reply(f"⚠️ Slot tidak boleh lebih besar dari jumlah umpan ({amount}).")
            return

        # Simpan slot di state
        state["slot"] = slot_value
        state["step"] = "sent"

        # Langsung kirim chest ke grup
        await send_sedekah_to_group(client, user_id, jenis, amount, slot_value, message)

        # Hapus state user agar tidak menumpuk
        SEDEKAH_STATE.pop(user_id, None)

# ---------------- SEND TO GROUP ---------------- #
async def send_sedekah_to_group(client, sender_id, jenis, amount, slot, message):
    """Kirim sedekah chest ke grup"""
    try:
        umpan.remove_umpan(sender_id, jenis, amount)
    except Exception as e:
        await message.reply(f"❌ Gagal mengurangi umpan: {e}")
        return

    chest_id = int(time.time())
    amount_per_slot = amount // slot
    new_chest = {
        "id": chest_id,
        "sender": sender_id,
        "jenis": jenis,
        "amount": amount_per_slot,
        "slot": slot,
        "claimed": [],        # tidak terlalu dipakai sekarang, tetap ada untuk backward compat
        "created_at": time.time(),
        "winner": None,       # akan diisi user_id jika ada pemenang
        "attempts": []        # user_id yang sudah mencoba (opsional, untuk mencegah spam)
    }

    #SEDEKAH
    data = load_sedekah_data()
    data["active"].append(new_chest)
    save_sedekah_data(data)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Claim Sedekah", callback_data=f"SEDEKAH_CLAIM:{chest_id}")]
    ])

    await client.send_message(
        TARGET_GROUP,
        f"🎁 **{message.from_user.first_name}** membagikan **Sedekah Treasure Chest!**\n"
        f"🎣 {amount_per_slot} Umpan Type {jenis} per orang (slot {slot})",
        reply_markup=keyboard
    )

    await message.reply("✅ Sedekah Treasure Chest dikirim ke grup!")

async def handle_sedekah_claim(client, cq):
    """Handle klaim sedekah:
    - Jika expired -> refund sisa ke sender
    - Jika sudah ada winner -> beri tahu chest sudah dimenangkan
    - Jika belum ada winner -> roll (20% win, 80% zonk)
      * jika win -> set winner, beri umpan, hapus chest dari active (slot terpakai)
      * jika zonk -> simpan attempt, chest tetap aktif
    """
    user_id = cq.from_user.id
    uname = cq.from_user.username or f"user{user_id}"

    # parse callback data
    try:
        _, chest_id_str = cq.data.split(":")
        chest_id = int(chest_id_str)
    except Exception:
        await cq.answer("❌ Data chest tidak valid.", show_alert=True)
        return

    async with SEDEKAH_LOCK:
        data = load_sedekah_data()
        active = data.get("active", [])
        chest = next((c for c in active if c["id"] == chest_id), None)

        if not chest:
            await cq.answer("⚠️ Chest tidak ditemukan atau sudah habis.", show_alert=True)
            return

        # expired -> refund sisa
        if time.time() - chest["created_at"] > SEDEKAH_EXPIRE_SECONDS:
            sisa_slot = chest["slot"] - (1 if chest.get("winner") else 0)
            # jika winner belum ada, refund seluruh amount (slot * amount)
            if sisa_slot > 0:
                refund_amount = sisa_slot * chest["amount"]
                try:
                    umpan.add_umpan(chest["sender"], chest["jenis"], refund_amount)
                    print(f"[SEDEKAH][EXPIRE] Chest #{chest_id} expired. Refund {refund_amount} umpan Type {chest['jenis']} to user {chest['sender']}")
                except Exception as e:
                    print(f"[SEDEKAH][ERROR][REFUND] Gagal refund ke {chest['sender']}: {e}")
            else:
                print(f"[SEDEKAH][EXPIRE] Chest #{chest_id} expired. Tidak ada sisa slot untuk refund.")
            # hapus chest
            active.remove(chest)
            save_sedekah_data(data)
            await cq.answer("⏳ Chest sudah expired. Sisa umpan dikembalikan ke pengirim.", show_alert=True)
            return

        # jika sudah ada pemenang, informasikan dan stop
        if chest.get("winner"):
            try:
                winner_uid = chest["winner"]
                await cq.answer("⚠️ Chest sudah dimenangkan.", show_alert=True)
            except Exception:
                pass
            return

        # optional: cegah user yang sama klik berulang kali (supaya tidak spam zonk)
        if user_id in chest.get("attempts", []):
            await cq.answer("⚠️ Kamu sudah mencoba klaim chest ini sebelumnya.", show_alert=True)
            return

        # lakukan roll gacha — 3% win, 97% zonk
        roll = random.random()
        if roll <= 0.01:
            # pemenang -> set winner, beri reward, hapus chest dari active
            chest["winner"] = user_id
            chest["claimed"].append(user_id)
            # beri umpan
            try:
                umpan.add_umpan(user_id, chest["jenis"], chest["amount"])
                print(f"[SEDEKAH][CLAIM][WIN] @{uname} menang dan mendapat {chest['amount']} umpan Type {chest['jenis']} dari chest #{chest_id}")
            except Exception as e:
                print(f"[SEDEKAH][ERROR][ADD_UMPAN] Gagal memberi umpan ke {user_id}: {e}")

            # hapus chest dari active (karena sudah ada pemenang)
            try:
                active.remove(chest)
            except ValueError:
                pass
            save_sedekah_data(data)

            await cq.answer("🎉 Kamu BERUNTUNG! Dapat sedekah umpan!", show_alert=True)
            await cq.message.reply_text(f"🍀 @{uname} BERHASIL mendapatkan {chest['amount']} umpan Type {chest['jenis']} dari sedekah!")
            return
        else:
            # zonk -> catat attempt, tapi chest tetap aktif
            chest.setdefault("attempts", []).append(user_id)
            save_sedekah_data(data)
            print(f"[SEDEKAH][CLAIM][ZONK] @{uname} ZONK saat klaim chest #{chest_id} (will remain active)")
            await cq.answer("😅 ZONK! Tidak dapat apa-apa kali ini. Coba lagi lain waktu.", show_alert=True)
            await asyncio.sleep(random.uniform(1, 3))
            await cq.message.reply_text(f"😜 @{uname} Sian deh lu... makan nih ZONK! 💩")
            return

#TOP UP HISTORY
TOPUP_HISTORY_FILE = "storage/topup_history.json"
os.makedirs(os.path.dirname(TOPUP_HISTORY_FILE), exist_ok=True)

def load_topup_history():
    if not os.path.exists(TOPUP_HISTORY_FILE):
        return {}
    with open(TOPUP_HISTORY_FILE, "r") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}

def save_topup_history(user_id, username, amount, bonus, umpan_type):
    data = load_topup_history()
    uid = str(user_id)
    data.setdefault(uid, [])
    next_id = len(data[uid]) + 1
    data[uid].append({
        "id": next_id,
        "username": username,
        "amount": amount,
        "bonus": bonus,
        "type": umpan_type,
        "timestamp": datetime.utcnow().timestamp()
    })
    with open(TOPUP_HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- DATA HANDLER ---------------- #
def load_sedekah_data():
    if not os.path.exists(SEDEKAH_FILE):
        return {"active": []}
    with open(SEDEKAH_FILE, "r") as f:
        return json.load(f)

def save_sedekah_data(data):
    with open(SEDEKAH_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- MENU SEDEKAH ---------------- #
async def handle_sedekah_menu(client, cq):
    """Menu Sedekah Treasure Chest — 1 slot, biaya 5 umpan A"""
    user_id = cq.from_user.id
    jenis = "A"
    amount = 10

    # Cek apakah ada sedekah aktif yang belum expired
    data = load_sedekah_data()
    now = time.time()
    for chest in data.get("active", []):
        if now - chest["created_at"] < SEDEKAH_EXPIRE_SECONDS and len(chest["claimed"]) < chest["slot"]:
            await cq.answer("⚠️ Masih ada Sedekah Chest aktif! Tunggu sampai habis atau expired dulu.", show_alert=True)
            return

    # Cek apakah punya cukup umpan
    if umpan.get_umpan(user_id, jenis) < amount:
        await cq.answer(f"❌ Umpan Type {jenis} tidak cukup (butuh {amount}).", show_alert=True)
        return

    slot = 5  # hanya 5 orang bisa klaim
    await send_sedekah_to_group(client, user_id, jenis, amount, slot, cq.message)

# ---------------- HELPER LOAD / SAVE ---------------- #
def _load_db() -> dict:
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        print(f"[DEBUG] fizz_coin DB created at {DB_FILE}")
        return {}

    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
        print(f"[DEBUG] fizz_coin loaded: {data}")
        return data
    except Exception as e:
        print(f"[DEBUG] fizz_coin load error: {e}")
        return {}

def _save_db(db: dict):
    try:
        with _LOCK:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
        print(f"[DEBUG] fizz_coin saved: {db}")
    except Exception as e:
        print(f"[DEBUG] fizz_coin save error: {e}")

# ---------------- PUBLIC FUNCTIONS ---------------- #
def add_coin(user_id: int, amount: int) -> int:
    """Tambah atau kurangi coin user. Bisa negatif. Kembalikan total baru."""
    db = _load_db()
    uid = str(user_id)
    old = db.get(uid, 0)
    new_total = old + amount
    if new_total < 0:
        new_total = 0
    db[uid] = new_total
    _save_db(db)
    print(f"[DEBUG] add_coin - user:{uid} old:{old} change:{amount} total:{db[uid]}")
    return db[uid]

def get_coin(user_id: int) -> int:
    db = _load_db()
    uid = str(user_id)
    total = db.get(uid, 0)
    print(f"[DEBUG] get_coin - user:{uid} total:{total}")
    return total

def reset_coin(user_id: int):
    db = _load_db()
    uid = str(user_id)
    db[uid] = 0
    _save_db(db)
    return 0

def reset_all():
    db = {}
    _save_db(db)
    return True

# ---------------- SELL / ITEM CONFIG ---------------- #
# inv_key harus cocok dengan key di aquarium_data.json (nama item di DB)
ITEM_PRICES = {
    "SELL_SMALLFISH": {"name": "𓆝 Small Fish", "price": 1, "inv_key": "Small Fish"},
    "SELL_SLIME": {"name": "🦠 Slime", "price": 1, "inv_key": "Slime"},
    "SELL_SNAIL": {"name": "🐌 Snail", "price": 2, "inv_key": "Snail"},
    "SELL_HERMITCRAB": {"name": "🐚 Hermit Crab", "price": 2, "inv_key": "Hermit Crab"},
    "SELL_CRAB": {"name": "🦀 Crab", "price": 2, "inv_key": "Crab"},
    "SELL_FROG": {"name": "🐸 Frog", "price": 2, "inv_key": "Frog"},
    "SELL_SNAKE": {"name": "🐍 Snake", "price": 2, "inv_key": "Snake"},
    "SELL_OCTOPUS": {"name": "🐙 Octopus", "price": 3, "inv_key": "Octopus"},
    "SELL_JELLYFISH": {"name": "ଳ Jelly Fish", "price": 4, "inv_key": "Jelly Fish"},
    "SELL_GIANTCLAM": {"name": "🦪 Giant Clam", "price": 4, "inv_key": "Giant Clam"},
    "SELL_GOLDFISH": {"name": "🐟 Goldfish", "price": 4, "inv_key": "Goldfish"},
    "SELL_STINGRAYSFISH": {"name": "🐟 Stingrays Fish", "price": 4, "inv_key": "Stingrays Fish"},
    "SELL_CLOWNFISH": {"name": "🐟 Clownfish", "price": 4, "inv_key": "Clownfish"},
    "SELL_DORYFISH": {"name": "🐟 Doryfish", "price": 4, "inv_key": "Doryfish"},
    "SELL_BANNERFISH": {"name": "🐟 Bannerfish", "price": 4, "inv_key": "Bannerfish"},
    "SELL_MOORISHIDOL": {"name": "🐟 Moorish Idol", "price": 4, "inv_key": "Moorish Idol"},
    "SELL_AXOLOTL": {"name": "🐟 Axolotl", "price": 4, "inv_key": "Axolotl"},
    "SELL_BETAFISH": {"name": "🐟 Beta Fish", "price": 4, "inv_key": "Beta Fish"},
    "SELL_ANGLERFISH": {"name": "🐟 Anglerfish", "price": 4, "inv_key": "Anglerfish"},
    "SELL_DUCK": {"name": "🦆 Duck", "price": 4, "inv_key": "Duck"},
    "SELL_CHICKEN": {"name": "🐔 Chicken", "price": 4, "inv_key": "Chicken"},
    "SELL_PUFFER": {"name": "🐡 Pufferfish", "price": 5, "inv_key": "Pufferfish"},
    "SELL_THUNDERELEMENT": {"name": "✨ Thunder Element", "price": 5, "inv_key": "Thunder Element"},
    "SELL_FIREELEMENT": {"name": "✨ Fire Element", "price": 5, "inv_key": "Fire Element"},
    "SELL_WATERELEMENT": {"name": "✨ Water Element", "price": 5, "inv_key": "Water Element"},
    "SELL_WINDELEMENT": {"name": "✨ Wind Element", "price": 5, "inv_key": "Wind Element"},
    "SELL_OWL": {"name": "🦉 Owl", "price": 5, "inv_key": "Owl"},
    "SELL_REDHAMMERCAT": {"name": "🐱 Red Hammer Cat", "price": 8, "inv_key": "Red Hammer Cat"},
    "SELL_PURPLEFISTCAT": {"name": "🐱 Purple Fist Cat", "price": 8, "inv_key": "Purple Fist Cat"},
    "SELL_GREENDINOCAT": {"name": "🐱 Green Dino Cat", "price": 8, "inv_key": "Green Dino Cat"},
    "SELL_WHITEWINTERCAT": {"name": "🐱 White Winter Cat", "price": 8, "inv_key": "White Winter Cat"},
    "SELL_SHARK": {"name": "🐟 Shark", "price": 10, "inv_key": "Shark"},
    "SELL_SEAHORSE": {"name": "🐟 Seahorse", "price": 10, "inv_key": "Seahorse"},
    "SELL_CROCODILE": {"name": "🐊 Crocodile", "price": 10, "inv_key": "Crocodile"},
    "SELL_SEAL": {"name": "🦦 Seal", "price": 10, "inv_key": "Seal"},
    "SELL_MYSTERIOUSDNA": {"name": "🧬 Mysterious DNA", "price": 10, "inv_key": "Mysterious DNA"},
    "SELL_TURTLE": {"name": "🐢 Turtle", "price": 10, "inv_key": "Turtle"},
    "SELL_LOBSTER": {"name": "🦞 Lobster", "price": 10, "inv_key": "Lobster"},
    "SELL_DEER": {"name": "🦌 Deer", "price": 5, "inv_key": "Deer"},
    "SELL_LUCKYJEWEL": {"name": "📿 Lucky Jewel", "price": 7, "inv_key": "Lucky Jewel"},
    "SELL_ORCA": {"name": "🐋 Orca", "price": 15, "inv_key": "Orca"},
    "SELL_MONKEY": {"name": "🐒 Monkey", "price": 15, "inv_key": "Monkey"},
    "SELL_GORILLA": {"name": "🦍 Gorilla", "price": 15, "inv_key": "GORILLA"},
    "SELL_PANDA": {"name": "🐼 Panda", "price": 15, "inv_key": "PANDA"},
    "SELL_BEAR": {"name": "🐻 Bear", "price": 15, "inv_key": "BEAR"},
    "SELL_DOG": {"name": "🐶 Dog", "price": 15, "inv_key": "DOG"},
    "SELL_BAT": {"name": "🦇 bat", "price": 15, "inv_key": "BAT"},
    "SELL_DOLPHIN": {"name": "🐬 Dolphin", "price": 15, "inv_key": "Dolphin"},
    "SELL_PIKACHU": {"name": "🐹⚡ Pikachu", "price": 30, "inv_key": "Pikachu"},
    "SELL_BULBASAUR": {"name": "🐸🍀 Bulbasaur", "price": 30, "inv_key": "Bulbasaur"},
    "SELL_SQUIRTLE": {"name": "🐢💧 Squirtle", "price": 30, "inv_key": "Squirtle"},
    "SELL_CHARMANDER": {"name": "🐉🔥 Charmander", "price": 30, "inv_key": "Charmander"},
    "SELL_KYOGRE": {"name": "🐋⚡ Kyogre", "price": 30, "inv_key": "Kyogre"},
    "SELL_BABYDRAGON": {"name": "🐉 Baby Dragon", "price": 100, "inv_key": "Baby Dragon"},
    "SELL_BABYSPIRITDRAGON": {"name": "🐉 Baby Spirit Dragon", "price": 100, "inv_key": "Baby Spirit Dragon"},
    "SELL_BABYMAGMADRAGON": {"name": "🐉 Baby Magma Dragon", "price": 100, "inv_key": "Baby Magma Dragon"},
    "SELL_SKULLDRAGON": {"name": "🐉 Skull Dragon", "price": 200, "inv_key": "Skull Dragon"},
    "SELL_BLUEDRAGON": {"name": "🐉 Blue Dragon", "price": 200, "inv_key": "Blue Dragon"},
    "SELL_YELLOWDRAGON": {"name": "🐉 Yellow Dragon", "price": 200, "inv_key": "Yellow Dragon"},
    "SELL_BLACKDRAGON": {"name": "🐉 Black Dragon", "price": 200, "inv_key": "Black Dragon"},
    "SELL_MERMAIDBOY": {"name": "🧜‍♀️ Mermaid Boy", "price": 200, "inv_key": "Mermaid Boy"},
    "SELL_MERMAIDGIRL": {"name": "🧜‍♀️ Mermaid Girl", "price": 200, "inv_key": "Mermaid Girl"},
    "SELL_CUPIDDRAGON": {"name": "🐉 Cupid Dragon", "price": 300, "inv_key": "Cupid Dragon"},
    "SELL_WEREWOLF": {"name": "🐺 Werewolf", "price": 300, "inv_key": "Werewolf"},
    "SELL_RAINBOWANGELCAT": {"name": "🐱 Rainbow Angel Cat", "price": 300, "inv_key": "Rainbow Angel Cat"},
    "SELL_FIREPHOENIX": {"name": "🐦‍🔥 Fire Phoenix", "price": 300, "inv_key": "Fire Phoenix"},
    "SELL_FROSTPHOENIX": {"name": "🐦❄️ Frost Phoenix", "price": 300, "inv_key": "Frost Phoenix"},
    "SELL_DARKPHOENIX": {"name": "🐦🌌 Dark Phoenix", "price": 300, "inv_key": "Dark Phoenix"},
    "SELL_CHIMERA": {"name": "🦁🐍 Chimera", "price": 300, "inv_key": "Chimera"},
    "SELL_WHITETIGER": {"name": "🐯 White Tiger", "price": 300, "inv_key": "White Tiger"},
    "SELL_DARKLORDDEMON": {"name": "👹 Dark Lord Demon", "price": 500, "inv_key": "Dark Lord Demon"},
    "SELL_PRINCESSOFNINETAIL": {"name": "🦊 Princess of Nine Tail", "price": 500, "inv_key": "Princess of Nine Tail"},
    "SELL_DARKKNIGHTDRAGON": {"name": "🐉 Dark Knight Dragon", "price": 500, "inv_key": "Dark Knight Dragon"},
    "SELL_DARKFISHWARRIOR": {"name": "👹 Dark Fish Warrior", "price": 3000, "inv_key": "Dark Fish Warrior"},
    "SELL_SNAILDRAGON": {"name": "🐉 Snail Dragon", "price": 5000, "inv_key": "Snail Dragon"},
    "SELL_QUEENOFHERMIT": {"name": "👑 Queen Of Hermit", "price": 5000, "inv_key": "Queen Of Hermit"},
    "SELL_MECHAFROG": {"name": "🤖 Mecha Frog", "price": 5000, "inv_key": "Mecha Frog"},
    "SELL_QUEENOFMEDUSA": {"name": "👑 Queen Of Medusa 🐍", "price": 5000, "inv_key": "Queen Of Medusa"},
    "SELL_PRINCESSMERMAID": {"name": "👑🧜‍♀️ Princess Mermaid", "price": 10000, "inv_key": "Princess Mermaid"},
    "SELL_SEAFAIRY": {"name": "🧚 Sea Fairy", "price": 15000, "inv_key": "Sea Fairy"},
    "SELL_RAICHU": {"name": "🐹⚡ Raichu", "price": 10000, "inv_key": "Raichu"},
}
# sementara user -> item_code waiting for amount input (chat)
SELL_WAITING = {}  # user_id: item_code

# Optional aliases: jika DB berisi emoji atau variasi penulisan,
# kita bisa map nama yang sering muncul ke bentuk canonical.
INV_KEY_ALIASES = {
    "🤧 Zonk": "Zonk",
    "zonk": "zonk",
    "𓆝 Small Fish": "Small Fish",
    "small fish": "Small Fish",
    "🐌 snail": "Snail",
    "snail": "Snail",
    "🐚 Hermit Crab": "Hermit Crab",
    "hermit crab": "Hermit Crab",
    "🐸 Frog": "Frog",
    "frog": "Frog",
    "🐍 Snake": "🐍 Snake",
    "snake": "Snake",
    "🐙 octopus": "Octopus",
    "octopus": "Octopus",
    "🐡 Pufferfish": "Pufferfish",
    "pufferfish": "Pufferfish",
    "🦠 Slime": "Slime",
    "slime": "Slime",
    "🦉 Owl": "Owl",
    "owl": "Owl",
    "🦌 Deer": "Deer",
    "deer": "Deer",
    "✨ Thunder Element": "Thunder Element",
    "thunder element": "Thunder Element",
    "✨ Fire Element": "Fire Element",
    "fire element": "Fire Element",
    "✨ Water Element": "Water Element",
    "water element": "Water Element",
    "✨ Wind Element": "Wind Element",
    "wind element": "Wind Element",
    "ଳ Jelly Fish": "Jelly Fish",
    "jelly fish": "Jelly Fish",
    "🐋 Orca": "Orca",
    "orca": "Orca",
    "🐒 Monkey": "Monkey",
    "monkey": "Monkey",
    "🦍 Gorilla": "Gorilla",
    "gorilla": "Gorilla",
    "🐼 Panda": "Panda",
    "panda": "Panda",
    "🐻 Bear": "Bear",
    "bear": "Bear",
    "🐶 Dog": "Dog",
    "dog": "Dog",
    "🦇 Bat": "Bat",
    "bat": "Bat",
    "🐬 Dolphin": "Dolphin",
    "dolphin": "Dolphin",
    "🐱 Red Hammer Cat": "Red Hammer Cat",
    "red hammer cat": "Red Hammer Cat",
    "🐱 Purple Fist Cat": "🐱 Purple Fist Cat",
    "purple fist cat": "Purple Fist Cat",
    "🐱 Green Dino Cat": "🐱 Green Dino Cat",
    "green dino cat": "Green Dino Cat",
    "🐱 White Winter Cat": "🐱 White Winter Cat",
    "white winter cat": "White Winter Cat",
    "🐉 Baby Dragon": "Baby Dragon",
    "baby dragon": "Baby Dragon",
    "🐉 Baby Spirit Dragon": "🐉 Baby Spirit Dragon",
    "baby spirit dragon": "Baby Spirit Dragon",
    "🐉 Baby Magma Dragon": "Baby Magma Dragon",
    "baby magma dragon": "Baby Magma Dragon",
    "📿 Lucky Jewel": "Lucky Jewel",
    "lucky jewel": "Lucky Jewel",
    "🐉 Skull Dragon": "Skull Dragon",
    "skull dragon": "Skull Dragon",
    "🐉 Blue Dragon": "Blue Dragon",
    "black dragon": "Black Dragon",
    "🐉 Yellow Dragon": "Yellow Dragon",
    "yellow dragon": "Yellow Dragon",
    "🐉 Black Dragon": "Black Dragon",
    "blue dragon": "Blue Dragon",
    "🐉 Cupid Dragon": "Cupid Dragon",
    "cupid dragon": "Cupid Dragon",
    "🐉 Dark Knight Dragon": "🐉 Dark Knight Dragon",
    "dark knight dragon": "Dark Knight Dragon",
    "🐯 White Tiger": "White Tiger",
    "white tiger": "White Tiger",
    "🐺 Werewolf": "🐺 Werewolf",
    "werewolf": "Werewolf",
    "🐱 Rainbow Angel Cat": "🐱 Rainbow Angel Cat",
    "rainbow angel cat": "Rainbow Angel Cat",
    "🐦‍🔥 Fire Phoenix": "🐦‍🔥 Fire Phoenix",
    "fire phoenix": "Fire Phoenix",
    "🐦❄️ Frost Phoenix": "🐦❄️ Frost Phoenix",
    "frost phoenix": "Frost Phoenix",
    "🐦🌌 Dark Phoenix": "🐦🌌 Dark Phoenix",
    "🦁🐍 Chimera": "Chimera",
    "chimera": "Chimera",
    "dark phoenix": "Dark Phoenix",
    "👹 Dark Lord Demon": "👹 Dark Lord Demon",
    "dark lord demon": "Dark Lord Demon",
    "🦊 Princess of Nine Tail": "🦊 Princess of Nine Tail",
    "princess of nine tail": "Princess of Nine Tail",
    "👹 Dark Fish Warrior": "Dark Fish Warrior",
    "dark fish warrior": "Dark Fish Warrior",
    "👑 Queen Of Hermit": "Queen Of Hermit",
    "queen of hermit": "Queen Of Hermit",
    "🐉 Snail Dragon": "Snail Dragon",
    "snail dragon": "Snail Dragon",
    "🤖 Mecha Frog": "Mecha Frog",
    "🤖 Mecha Frog": "Mecha Frog",
    "👑 Queen Of Medusa 🐍": "Queen Of Medusa",
    "queen of medusa": "Queen Of Medusa",
    "🐸 Frog": "Frog",
    "Frog": "Frog",
    "🐟 Goldfish": "Goldfish",
    "goldfish": "Goldfish",
    "🐟 Stingrays Fish": "🐟 Stingrays Fish",
    "stingrays fish": "Stingrays Fish",
    "🐟 Clownfish": "Clownfish",
    "clownfish": "Clownfish",
    "🐟 Doryfish":"Doryfish",
    "doryfish": "Doryfish",
    "🐟 Bannerfish": "Bannerfish",
    "bannerfish": "Bannerfish",
    "🐟 Beta Fish":"Beta Fish",
    "beta fish":"Beta Fish",
    "🐟 Moorish Idol": "Moorish Idol",
    "moorish idol": "Moorish Idol",
    "🐟 Axolotl": "Axolotl",
    "axolotl": "Axolotl",
    "🐟 Anglerfish": "Anglerfish",
    "anglerfish": "Anglerfish",
    "🦆 Duck": "Duck",
    "duck": "Duck",
    "🐔 Chicken": "Chicken",
    "Chicken": "Chicken",
    "🦪 Giant Clam": "Giant Clam",
    "giant clam": "Giant Clam",
    "🐟 Shark": "Shark",
    "Shark": "Shark",
    "🐟 Seahorse": "Seahorse",
    "seahorse": "Seahorse",
    "🐹⚡ Pikachu": "Pikachu",
    "Pikachu": "Pikachu",
    "🐸🍀 Bulbasaur": "Bulbasaur",
    "bulbasaur": "Bulbasaur",
    "🐢💧 Squirtle": "🐢💧 Squirtle",
    "squirtle": "Squirtle",
    "🐉🔥 Charmander": "Charmander",
    "charmander": "Charmander",
    "🐋⚡ Kyogre": "Kyogre",
    "kyogre": "Kyogre",
    "🐊 Crocodile": "Crocodile",
    "crocodile": "Crocodile",
    "🦦 Seal": "Seal",
    "seal": "Seal",
    "🧬 Mysterious DNA": "Mysterious DNA",
    "mysterious dna": "Mysterious DNA",
    "🐢 Turtle": "🐢 Turtle",
    "turtle": "Turtle",
    "🦞 Lobster": "🦞 Lobster",
    "lobster": "Lobster",
    "🧜‍♀️ Mermaid Boy": "Mermaid Boy",
    "mermaid boy": "Mermaid Boy",
    "🧜‍♀️ Mermaid Girl": "Mermaid Girl",
    "mermaid girl": "Mermaid Girl",
    "👑🧜‍♀️ Princess Mermaid": "Princess Mermaid",
    "princess Mermaid": "Princess Mermaid",
    "🧚 Sea Fairy": "🧚 Sea Fairy",
    "sea fairy": "Sea Fairy",
    "🐹⚡ Raichu": "Raichu",
    "raichu": "Raichu"
    # tambahkan sesuai kebutuhan 
}

# ---------------- KEYBOARD / MENU STRUCTURE ---------------- #
MENU_STRUCTURE = {
    # MAIN MENU
    "main": {
        "title": "📋 [Menu Utama]",
        "buttons": [
            ("UMPAN", "A"),
            ("YAPPING", "B"),
            ("REGISTER", "C"),
            ("🛒STORE", "D"),
            ("CATCH", "E"),
            ("HASIL TANGKAPAN", "F"),
            ("LOGIN CHECK IN", "G"),
            ("TREASURE CHEST", "H"),
            ("🧬 EVOLVE", "I"),
            ("💎 TRANSFER MONSTER", "J")
        ]
    },
    
    # =============== UMPAN =============== #
    "A": {
        "title": "📋 Menu UMPAN",
        "buttons": [
            ("COMMON 🐛", "AA_COMMON"),
            ("RARE 🐌", "AA_RARE"),
            ("LEGENDARY 🧇", "AA_LEGEND"),
            ("MYTHIC 🐟", "AA_MYTHIC"),
            ("⬅️ Back", "main")
        ]
    },
    "AA_COMMON": {
        "title": "📋 TRANSFER UMPAN KE (Common)",
        "buttons": [
            ("Klik OK untuk transfer", "TRANSFER_COMMON_OK"),
            ("⬅️ Back", "A")
        ]
    },
    "AA_RARE": {
        "title": "📋 TRANSFER UMPAN KE (Rare)",
        "buttons": [
            ("Klik OK untuk transfer", "TRANSFER_RARE_OK"),
            ("⬅️ Back", "A")
        ]
    },
    "AA_LEGEND": {
        "title": "📋 TRANSFER UMPAN KE (Legend)",
        "buttons": [
            ("Klik OK untuk transfer", "TRANSFER_LEGEND_OK"),
            ("⬅️ Back", "A")
        ]
    },
    "AA_MYTHIC": {
        "title": "📋 TRANSFER UMPAN KE (Mythic)",
        "buttons": [
            ("Klik OK untuk transfer", "TRANSFER_MYTHIC_OK"),
            ("⬅️ Back", "A")
        ]
    },

    # =============== FISHING =============== #
    "E": {
        "title": "🎣 CATCHING",
        "buttons": [
            ("PILIH UMPAN", "EE"),
            ("⬅️ Back", "main")
        ]
    },
    "EE": {
        "title": "📋 PILIH UMPAN",
        "buttons": [
            ("Lanjut Pilih Jenis", "EEE"),
            ("⬅️ Back", "E")
        ]
    },
    "EEE": {
        "title": "📋 Pilih Jenis Umpan",
        "buttons": [
            ("COMMON 🐛", "EEE_COMMON"),
            ("RARE 🐌", "EEE_RARE"),
            ("LEGENDARY 🧇", "EEE_LEGEND"),
            ("MYTHIC 🐟", "EEE_MYTHIC"),
            ("⬅️ Back", "EE")
        ]
    },

    # =============== REGISTER =============== #
    "C": {
        "title": "📋 MENU REGISTER",
        "buttons": [
            ("NEXT", "CC"),
            ("⬅️ Back", "main")
        ]
    },
    "CC": {
        "title": "📋 APAKAH KAMU YAKIN INGIN MENJADI PLAYER LOOT?",
        "buttons": [
            ("REGIS NOW!!", "CCC"),
            ("⬅️ Back", "C")
        ]
    },
    "CCC": {
        "title": "📋 Are You Sure?:",
        "buttons": [
            ("YES!", "REGISTER_YES"),
            ("NO", "REGISTER_NO")
        ]
    },

    # =============== STORE =============== #
    "D": {
        "title": "🛒STORE",
        "buttons": [
            ("BUY UMPAN", "D1"),
            ("SELL ITEM", "D2"),
            ("TUKAR POINT", "D3"),
            ("⬅️ Back", "main")
        ]
    },
    "D1": {
        "title": "📋 BUY UMPAN",
        "buttons": [
            ("TOPUP QRIS UMPAN A", "D1A"),
            ("TOPUP QRIS UMPAN B", "D1B"),
            ("📜 HISTORY TOP UP", "D1H"),
            ("⬅️ Back", "D")
        ]
    },
    "D2": {
        "title": "📋 SELL ITEM",
        "buttons": [
            ("💰 CEK COIN", "D2C"),
            ("📦 CEK INVENTORY", "D2A"),
            ("💰 DAFTAR HARGA", "D2B"),
            ("⬅️ Back", "D")
        ]
    },
    # Submenu untuk CEK COIN
    "D2C_MENU": {
        "title": "💰 CEK COIN & PENUKARAN",
        "buttons": [
            ("🐛 TUKAR UMPAN COMMON A", "D2C_COMMON_A"),
            ("🪱 TUKAR UMPAN COMMON B", "D2C_COMMON_B"),
            ("⬅️ Back", "D2")
        ]
    },
    "D2A": {
        "title": "📦 CEK INVENTORY",
        "buttons": [
            ("⬅️ Back", "D2")
        ]
    },
    # DAFTAR HARGA -> note: callback format SELL_DETAIL:<code>
    "D2B": {
        "title": "💰 DAFTAR HARGA",
        "buttons": [
            ("𓆝 Small Fish", "SELL_DETAIL:SELL_SMALLFISH"),
            ("🦠 Slime", "SELL_DETAIL:SELL_SLIME"),
            ("🐌 Snail", "SELL_DETAIL:SELL_SNAIL"),
            ("🐚 Hermit Crab", "SELL_DETAIL:SELL_HERMITCRAB"),
            ("🦀 Crab", "SELL_DETAIL:SELL_CRAB"),
            ("🐸 Frog", "SELL_DETAIL:SELL_FROG"),
            ("🐍 Snake", "SELL_DETAIL:SELL_SNAKE"),
            ("🐙 Octopus", "SELL_DETAIL:SELL_OCTOPUS"),
            ("ଳ Jelly Fish", "SELL_DETAIL:SELL_JELLYFISH"),
            ("🦪 Giant Clam", "SELL_DETAIL:SELL_GIANTCLAM"),
            ("🐟 Goldfish", "SELL_DETAIL:SELL_GOLDFISH"),
            ("🐟 Clownfish", "SELL_DETAIL:SELL_CLOWNFISH"),
            ("🐟 Stingrays Fish", "SELL_DETAIL:SELL_STINGRAYSFISH"),
            ("🐟 Doryfish", "SELL_DETAIL:SELL_DORYFISH"),
            ("🐟 Bannerfish", "SELL_DETAIL:SELL_BANNERFISH"),
            ("🐟 Beta Fish", "SELL_DETAIL:SELL_BETAFISH"),
            ("🐟 Moorish Idol", "SELL_DETAIL:SELL_MOORISHIDOL"),
            ("🐟 Anglerfish", "SELL_DETAIL:SELL_ANGLERFISH"),
            ("🐟 Axolotl", "SELL_DETAIL:SELL_AXOLOTL"),
            ("🐱 Red Hammer Cat", "SELL_DETAIL:SELL_REDHAMMERCAT"),
            ("🐱 Purple Fist Cat", "SELL_DETAIL:SELL_PURPLEFISTCAT"),
            ("🐱 Green Dino Cat", "SELL_DETAIL:SELL_GREENDINOCAT"),
            ("🐱 White Winter Cat", "SELL_DETAIL:SELL_WHITEWINTERCAT"),
            ("🦆 Duck", "SELL_DETAIL:SELL_DUCK"),
            ("🐔 Chicken", "SELL_DETAIL:SELL_CHICKEN"),
            ("🐡 Pufferfish", "SELL_DETAIL:SELL_PUFFER"),
            ("✨ Thunder Element", "SELL_DETAIL:SELL_THUNDERELEMENT"),
            ("✨ Fire Element", "SELL_DETAIL:SELL_FIREELEMENT"),
            ("✨ Water Element", "SELL_DETAIL:SELL_WATERELEMENT"),
            ("✨ Wind Element", "SELL_DETAIL:SELL_SELL_WINDELEMENT"),
            ("🦉 Owl", "SELL_DETAIL:SELL_OWL"),
            ("🐟 Shark", "SELL_DETAIL:SELL_SHARK"),
            ("🐟 Seahorse", "SELL_DETAIL:SELL_SEAHORSE"),
            ("🐹⚡ Pikachu", "SELL_DETAIL:SELL_PIKACHU"),
            ("🐸🍀 Bulbasaur", "SELL_DETAIL:SELL_BULBASAUR"),
            ("🐢💧 Squirtle", "SELL_DETAIL:SELL_SQUIRTLE"),
            ("🐉🔥 Charmander", "SELL_DETAIL:SELL_CHARMANDER"),
            ("🐋⚡ Kyogre", "SELL_DETAIL:SELL_KYOGRE"),
            ("🐊 Crocodile", "SELL_DETAIL:SELL_CROCODILE"),
            ("🦦 Seal", "SELL_DETAIL:SELL_SEAL"),
            ("🧬 Mysterious DNA", "SELL_DETAIL:SELL_MYSTERIOUS"),
            ("🐢 Turtle", "SELL_DETAIL:SELL_TURTLE"),
            ("🦞 Lobster", "SELL_DETAIL:SELL_LOBSTER"),
            ("🦌 Deer", "SELL_DETAIL:SELL_DEER"),
            ("📿 Lucky Jewel", "SELL_DETAIL:SELL_LUCKYJEWEL"),
            ("🐋 Orca", "SELL_DETAIL:SELL_ORCA"),
            ("🐒 Monkey", "SELL_DETAIL:SELL_MONKEY"),
            ("🦍 Gorilla", "SELL_DETAIL:SELL_GORILLA"),
            ("🐼 Panda", "SELL_DETAIL:SELL_PANDA"),
            ("🐻 Bear", "SELL_DETAIL:SELL_BEAR"),
            ("🐶 Dog", "SELL_DETAIL:SELL_DOG"),
            ("🦇 bat", "SELL_DETAIL:SELL_BAT"),
            ("🐬 Dolphin", "SELL_DETAIL:SELL_DOLPHIN"),
            ("🐉 Baby Dragon", "SELL_DETAIL:SELL_BABYDRAGON"),
            ("🐉 Baby Spirit Dragon", "SELL_DETAIL:SELL_BABYSPIRITDRAGON"),
            ("🐉 Baby Magma Dragon", "SELL_DETAIL:SELL_BABYMAGMADRAGON"),
            ("🐉 Skull Dragon", "SELL_DETAIL:SELL_SKULLDRAGON"),
            ("🐉 Blue Dragon", "SELL_DETAIL:SELL_BLUEDRAGON"),
            ("🐉 Yellow Dragon", "SELL_DETAIL:SELL_YELLOWDRAGON"),
            ("🐉 Black Dragon", "SELL_DETAIL:SELL_BLACKDRAGON"),
            ("🧜‍♀️ Mermaid Boy", "SELL_DETAIL:SELL_MERMAIDBOY"),
            ("🧜‍♀️ Mermaid Girl", "SELL_DETAIL:SELL_MERMAIDGIRL"),
            ("🐉 Cupid Dragon", "SELL_DETAIL:SELL_CUPIDDRAGON"),
            ("🐺 Werewolf", "SELL_DETAIL:SELL_WEREWOLF"),
            ("🐱 Rainbow Angel Cat", "SELL_DETAIL:SELL_RAINBOWANGELCAT"),
            ("🐦‍🔥 Fire Phoenix", "SELL_DETAIL:SELL_FIREPHOENIX"),
            ("🐦❄️ Frost Phoenix", "SELL_DETAIL:SELL_FROSTPHOENIX"),
            ("🐦🌌 Dark Phoenix", "SELL_DETAIL:SELL_DARKPHOENIX"),
            ("🦁🐍 Chimera", "SELL_DETAIL:SELL_CHIMERA"),
            ("🐯 White Tiger", "SELL_DETAIL:SELL_WHITETIGER"),
            ("👹 Dark Lord Demon", "SELL_DETAIL:SELL_DARKLORDDEMON"),
            ("🦊 Princess of Nine Tail", "SELL_DETAIL:SELL_PRINCESSOFNINETAIL"),
            ("🐉 Dark Knight Dragon", "SELL_DETAIL:SELL_DARKKNIGHTDRAGON"),
            ("👹 Dark Fish Warrior", "SELL_DETAIL:SELL_DARKFISHWARRIOR"),
            ("🐉 Snail Dragon", "SELL_DETAIL:SELL_SNAILDRAGON"),
            ("👑 Queen Of Hermit", "SELL_DETAIL:SELL_QUEENOFHERMIT"),
            ("🤖 Mecha Frog", "SELL_DETAIL:SELL_MECHAFROG"),
            ("👑 Queen Medusa 🐍", "SELL_DETAIL:SELL_QUEENOFMEDUSA"),
            ("👑🧜‍♀️ Princess Mermaid", "SELL_DETAIL:SELL_PRINCESSMERMAID"),
            ("🧚 Sea Fairy", "SELL_DETAIL:SELL_SEAFAIRY"),
            ("🐹⚡ Raichu", "SELL_DETAIL:SELL_RAICHU"),
            ("⬅️ Back", "D2"),
        ]
    },
    "D3": {
        "title": "📋 TUKAR POINT",
        "buttons": [
            ("Lihat Poin & Tukar", "D3A"),
            ("⬅️ Back", "D")
        ]
    },
    "D3LA": {
        "title": "📋 🔄 POINT CHAT",
        "buttons": [
            ("TUKAR 🔄 UMPAN COMMON 🐛", "TUKAR_POINT"),
            ("⬅️ Back", "D3")
        ]
    },

    # =============== YAPPING =============== #
    "B": {
        "title": "📋 YAPPING",
        "buttons": [
            ("Poin Pribadi", "BB"),
            ("➡️ Leaderboard", "BBB"),
            ("⬅️ Back", "main")
        ]
    },
    "BB": {
        "title": "📋 Poin Pribadi",
        "buttons": [
            ("⬅️ Back", "B")
        ]
    },
    "BBB": {
        "title": "📋 Leaderboard Yapping",
        "buttons": [
            ("⬅️ Back", "B")
        ]
    },

    # =============== HASIL TANGKAPAN =============== #
    "F": {
        "title": "📋 HASIL TANGKAPAN",
        "buttons": [
            ("CEK INVENTORY", "FF"),
            ("⬅️ Back", "main")
        ]
    },
    "FF": {
        "title": "📋 CEK INVENTORY",
        "buttons": [
            ("LIHAT HASIL TANGKAPAN", "FFF"),
            ("⬅️ Back", "F")
        ]
    }
}

# Tambahan confirm untuk catching
for jenis in ["COMMON", "RARE", "LEGEND", "MYTHIC"]:
    MENU_STRUCTURE[f"EEE_{jenis}"] = {
        "title": f"📋 Are you want to catch using this {jenis}?",
        "buttons": [
            ("✅ YES", f"FISH_CONFIRM_{jenis}"),
            ("❌ NO", "EEE")
        ]
    }

# ---------------- LOGIN / ABSEN HARIAN ---------------- #
MENU_STRUCTURE["G"] = {
    "title": "📋 LOGIN HARIAN",
    "buttons": [
        ("✅ Absen Hari Ini", "LOGIN_TODAY"),
        ("📅 Lihat Status Login 7 Hari", "LOGIN_STATUS"),
        ("🔄 Reset Login (OWNER)", "LOGIN_RESET") if OWNER_ID else None,
        ("⬅️ Back", "main")
    ]
}

# di bawah LOGIN CHECK IN (G)
MENU_STRUCTURE["H"] = {
    "title": "📦 TREASURE CHEST",
    "buttons": [
        ("📤 OWNER Only", "TREASURE_SEND_NOW"),
        ("🎁 SEDEKAH TREASURE CHEST", "SEDEKAH_TREASURE"),
        ("⬅️ Back", "main")
    ]
}
# ===== SUBMENU EVOLVE =====
# ===== SUBMENU EVOLVE =====
MENU_STRUCTURE["I"] = {
    "title": "🧬 [EVOLVE]",
    "buttons": [
        ("𓆝 Small Fish", "I_SMALLFISH"),
        ("🐌 Snail", "I_SNAIL"),
        ("🐚 Hermit Crab", "I_HERMITCRAB"),
        ("🐸 Frog", "I_FROG"),
        ("🐍 Snake", "I_SNAKE"),
        ("🧜‍♀️ Mermaid Girl", "I_MERMAIDGIRL"),
        ("🧚 Sea Fairy", "I_SEAFAIRY"),
        ("Raichu ⚡", "I_RAICHU"),  # 🔹 tombol baru
        ("⬅️ Back", "main")
    ]
}


# Submenu Small Fish
MENU_STRUCTURE["I_SMALLFISH"] = {
    "title": "🧬 Evolve 𓆝 Small Fish",
    "buttons": [
        ("🧬 Evolve jadi 👹 Dark Fish Warrior (-1000)", "EVOLVE_SMALLFISH_CONFIRM"),
        ("COMING SOON", "COMING_SOON"),
        ("⬅️ Back", "I")
    ]
}

# Submenu Snail
MENU_STRUCTURE["I_SNAIL"] = {
    "title": "🧬 Evolve 🐌 Snail",
    "buttons": [
        ("🧬 Evolve jadi 🐉 Snail Dragon (-1000)", "EVOLVE_SNAIL_CONFIRM"),
        ("⬅️ Back", "I")
    ]
}

# Submenu Hermit Crab
MENU_STRUCTURE["I_HERMITCRAB"] = {
    "title": "🧬 Evolve 🐚 Hermit Crab",
    "buttons": [
        ("🧬 Evolve jadi 👑 Queen of Hermit (-1000)", "EVOLVE_HERMITCRAB_CONFIRM"),
        ("⬅️ Back", "I")
    ]
}

# Submenu Frog
MENU_STRUCTURE["I_FROG"] = {
    "title": "🧬 Evolve 🐸 Frog",
    "buttons": [
        ("🧬 Evolve jadi 🤖 Mecha Frog (-1000)", "EVOLVE_FROG_CONFIRM"),
        ("⬅️ Back", "I")
    ]
}

# Submenu Snake
MENU_STRUCTURE["I_SNAKE"] = {
    "title": "🧬 Evolve 🐍 Snake",
    "buttons": [
        ("🧬 Evolve jadi 👑 Queen Of Medusa 🐍 (-1000)", "EVOLVE_QUEENOFMEDUSA_CONFIRM"),
        ("⬅️ Back", "I")
    ]
}
# Submenu Mermaid
MENU_STRUCTURE["I_MERMAIDGIRL"] = {
    "title": "🧬 Evolve 🧜‍♀️ Mermaid Girl",
    "buttons": [
        ("🧬 Evolve jadi 👑🧜‍♀️ Princess Mermaid (-1000)", "EVOLVE_PRINCESSMERMAID_CONFIRM"),
        ("⬅️ Back", "I")
    ]
}
# Submenu Mermaid
MENU_STRUCTURE["I_SEAFAIRY"] = {
    "title": "🧬 Evolve Sea Creatures",
    "buttons": [
        ("🧬 Evolve jadi 🧚 Sea Fairy", "EVOLVE_SEAFAIRY_CONFIRM"),
        ("⬅️ Back", "I")
    ]
}
# Submenu 🐹⚡ Raichu
MENU_STRUCTURE["I_RAICHU"] = {
    "title": "🧬 Evolve Pikachu",
    "buttons": [
        ("🧬 Evolve jadi 🐹⚡ Raichu", "EVOLVE_RAICHU_CONFIRM"),
        ("⬅️ Kembali", "I")
    ]
}

# hapus None
MENU_STRUCTURE["G"]["buttons"] = [b for b in MENU_STRUCTURE["G"]["buttons"] if b is not None]

# ---------------- Helper untuk normalisasi key ---------------- #

def normalize_key(key: str) -> str:
    """
    Normalisasi nama item dari inventory agar cocok dengan inv_key.
    - Lowercase
    - Hilangkan emoji dan karakter non-alnum (kecuali spasi)
    - Trim spasi berlebih
    """
    if not isinstance(key, str):
        return ""
    # ubah ke lowercase
    s = key.strip().lower()
    # replace non-alphanumeric (tetap simpan spasi)
    s = re.sub(r"[^0-9a-z\s]", "", s)
    # collapse multiple spaces
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def canonical_inv_key_from_any(key: str) -> str:
    """Coba konversi nama key inventory (dari DB) menjadi bentuk canonical yang dipakai di ITEM_PRICES.
    Menggunakan INV_KEY_ALIASES dulu, jika tidak ditemukan, coba normalisasi dan cocokkan dengan
    semua ITEM_PRICES inv_key yang dinormalisasi.
    """
    if not key:
        return ""
    norm = normalize_key(key)
    # cek aliases
    if norm in INV_KEY_ALIASES:
        return INV_KEY_ALIASES[norm]

    # coba match dengan inv_key pada ITEM_PRICES
    for cfg in ITEM_PRICES.values():
        canon = cfg.get("inv_key")
        if normalize_key(canon) == norm:
            return canon
    # fallback - return original key (caller harus tetap handle absence)
    return key

# ---------------- KEYBOARD BUILDER ---------------- #
def make_keyboard(menu_key: str, user_id=None, page: int = 0) -> InlineKeyboardMarkup:
    buttons = []

    # LEADERBOARD
    if menu_key == "BBB" and user_id:
        points = yapping.load_points()
        sorted_pts = sorted(points.items(), key=lambda x: x[1]["points"], reverse=True)
        total_pages = max((len(sorted_pts) - 1) // 10, 0) if len(sorted_pts) > 0 else 0
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"BBB_PAGE_{page-1}"))
        if page < total_pages:
            nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"BBB_PAGE_{page+1}"))
        if nav:
            buttons.append(nav)
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="B")])

    # MENU UMPAN
    elif menu_key in ["A", "AA_COMMON", "AA_RARE", "AA_LEGEND", "AA_MYTHIC"] and user_id:
        user_umpan = umpan.get_user(user_id) or {"A": {"umpan": 0}, "B": {"umpan": 0},
                                                 "C": {"umpan": 0}, "D": {"umpan": 0}}
        type_map = {"AA_COMMON": "A", "AA_RARE": "B", "AA_LEGEND": "C", "AA_MYTHIC": "D"}
        for text, cb in MENU_STRUCTURE.get(menu_key, {}).get("buttons", []):
            if cb.startswith("TRANSFER_"):
                jenis = cb.split("_")[1]
                jumlah = 999 if user_id == OWNER_ID else user_umpan.get(type_map.get(menu_key, "A"), {}).get("umpan", 0)
                text = f"{text} ({jumlah} pcs)"
            buttons.append([InlineKeyboardButton(text, callback_data=cb)])

    # FISHING PILIH UMPAN
    elif menu_key == "EEE" and user_id:
        user_umpan = umpan.get_user(user_id) or {"A": {"umpan": 0}, "B": {"umpan": 0},
                                                 "C": {"umpan": 0}, "D": {"umpan": 0}}
        if user_id == OWNER_ID:
            user_umpan = {"A": {"umpan": 999}, "B": {"umpan": 999}, "C": {"umpan": 999}, "D": {"umpan": 999}}
        map_type = {"EEE_COMMON": ("COMMON 🐛", "A"), "EEE_RARE": ("RARE 🐌", "B"),
                    "EEE_LEGEND": ("LEGENDARY 🧇", "C"), "EEE_MYTHIC": ("MYTHIC 🐟", "D")}
        for cb, (label, tkey) in map_type.items():
            jumlah = user_umpan.get(tkey, {}).get("umpan", 0)
            buttons.append([InlineKeyboardButton(f"{label} ({jumlah} pcs)", callback_data=cb)])
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="EE")])

    # STORE TUKAR POINT
    elif menu_key == "D3A" and user_id:
        pts = yapping.load_points().get(str(user_id), {}).get("points", 0)
        buttons.append([InlineKeyboardButton(f"TUKAR 🔄 UMPAN COMMON 🐛 (Anda: {pts} pts)", callback_data="TUKAR_POINT")])
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="D3")])

    # HASIL TANGKAPAN INVENTORY
    elif menu_key == "FFF" and user_id:
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="F")])

    # STORE CEK INVENTORY
    elif menu_key == "D2A" and user_id:
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="D2")])

    # DEFAULT
    else:
        for text, cb in MENU_STRUCTURE.get(menu_key, {}).get("buttons", []):
            buttons.append([InlineKeyboardButton(text, callback_data=cb)])
        if not buttons:
            # fallback minimal supaya selalu valid
            buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="main")])

    return InlineKeyboardMarkup(buttons)

# ================== FULL INVENTORY LIST (urut berdasarkan jumlah terbanyak) ==================
def list_full_inventory(user_id: int) -> str:
    """Gabungkan semua item dari ITEM_PRICES + hasil pancingan user.
    Item yang belum didapat akan tampil dengan jumlah 0.
    Urutkan berdasarkan jumlah terbanyak, lalu nama.
    """
    # Ambil data ikan user
    inv = aquarium.get_user_fish(user_id) or {}

    # Ambil semua nama item dari ITEM_PRICES
    all_items = []
    for cfg in ITEM_PRICES.values():
        if cfg["name"] not in all_items:
            all_items.append(cfg["name"])

    # Tambahkan item dasar (Zonk, Small Fish) jika belum ada
    base_items = ["🤧 Zonk", "𓆝 Small Fish"]
    for b in base_items:
        if b not in all_items:
            all_items.insert(0, b)

    # Gabungkan hasil user (jika item tidak ada, beri nilai 0)
    item_data = []
    for name in all_items:
        qty = inv.get(name, 0)
        item_data.append((name, qty))

    # Urutkan berdasarkan jumlah terbanyak, lalu nama (ascending)
    item_data.sort(key=lambda x: (-x[1], x[0].lower()))

    # Format teks hasil
    lines = [f"{name} : {qty}" for name, qty in item_data]
    result = "🎣 **HASIL TANGKAPANMU:**\n\n" + "\n".join(lines)
    return result

# ===========================================================
# HITUNG BONUS & BULATKAN KE NOMINAL SAWERIA
# ===========================================================
def get_umpan_bonus(amount):
    valid_nominals = [1000, 5000, 10000, 50000]
    rounded_amount = min(valid_nominals, key=lambda x: abs(x - amount))
    bonus_map = {1000: 20, 5000: 105, 10000: 210, 50000: 1100}
    return rounded_amount, bonus_map.get(rounded_amount, 0)

# ---------------- CALLBACK HANDLER ---------------- #
async def callback_handler(client, cq):
    data = cq.data
    user_id = cq.from_user.id
    uname = cq.from_user.username or f"user{user_id}"

    # ===== TOPUP QRIS UMPAN A =====
    if data == "D1A":
        saweria_url = f"https://saweria.co/axeliandrea?user={user_id}&username={uname}&type=umpanA"
        text = (
            "💳 **TOPUP QRIS - UMPAN A (🐛)**\n\n"
            "Silakan pilih nominal dan lakukan pembayaran melalui link berikut.\n\n"
            "📦 Konversi otomatis (1 Umpan A = Rp50):\n"
            "• 1K → 20 Umpan A 🐛\n"
            "• 5K → 100 Umpan A 🐛 (bonus)\n"
            "• 10K → 200 Umpan A 🐛 (bonus)\n"
            "• 50K → 1000 Umpan A 🐛 (bonus)\n\n"
            "_Nominal lain seperti 1,1K akan otomatis dikonversi proporsional._\n"
            "_Umpan akan dikirim otomatis setelah pembayaran berhasil._"
        )
        await cq.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 TOP UP SEKARANG", url=saweria_url)],
                [InlineKeyboardButton("⬅️ Kembali", callback_data="D1")]
            ]),
            disable_web_page_preview=True
        )
        return

    # ===== TOPUP QRIS UMPAN B =====
    if data == "D1B":
        saweria_url = f"https://saweria.co/axeliandrea?user={user_id}&username={uname}&type=umpanB"
        text = (
            "💳 **TOPUP QRIS - UMPAN B (🐌)**\n\n"
            "Silakan pilih nominal dan lakukan pembayaran melalui link berikut.\n\n"
            "📦 Konversi otomatis (1 Umpan B = Rp500):\n"
            "• 1K → 2 Umpan B 🐌\n"
            "• 5K → 10 Umpan B 🐌 (bonus)\n"
            "• 10K → 20 Umpan B 🐌 (bonus)\n"
            "• 50K → 100 Umpan B 🐌 (bonus)\n\n"
            "_Nominal seperti 1,1K akan dikonversi otomatis ke 2,2 Umpan B._\n"
            "_Umpan akan dikirim otomatis setelah pembayaran berhasil._"
        )
        await cq.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 TOP UP SEKARANG", url=saweria_url)],
                [InlineKeyboardButton("⬅️ Kembali", callback_data="D1")]
            ]),
            disable_web_page_preview=True
        )
        return

    # ===== HISTORY TOP UP =====
    if data == "D1H":
        history_data = load_history()
        user_history = history_data.get(str(user_id), [])

        if not user_history:
            history_text = "📜 Kamu belum pernah melakukan top-up."
        else:
            lines = []
            for h in user_history[-10:]:
                ts = datetime.fromtimestamp(h.get("timestamp", 0)).strftime("%d-%m-%Y %H:%M")
                amount = h.get("amount", 0)
                bonus = h.get("bonus", 0)
                tipe = h.get("type", "?")
                status = h.get("status", "unknown")
                lines.append(f"{ts} | Rp{int(amount):,} → {bonus} Umpan {tipe} | Status: {status}")

            history_text = "📜 **Riwayat Top-Up Terakhir:**\n" + "\n".join(lines)

        await cq.message.edit_text(
            history_text,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Kembali", callback_data="D1")]]
            )
        )
        return

    
    # ====== MENU TRANSFER MONSTER ======
    if data == "J":
        inv = aquarium.get_user_fish(user_id) or {}
        buttons = []

        # Tambahkan semua item kecuali Zonk & yang jumlahnya 0
        for name, qty in inv.items():
            if name != "🤧 Zonk" and qty > 0:
                buttons.append([InlineKeyboardButton(f"{name} ({qty})", callback_data=f"TRANSFER_SELECT|{name}")])

        # Jika user tak punya monster lain
        if not buttons:
            await cq.message.edit_text(
                "❌ Kamu tidak punya monster yang bisa ditransfer.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main")]])
            )
            return

        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="main")])
        kb = InlineKeyboardMarkup(buttons)
        await cq.message.edit_text("💎 Pilih monster yang ingin kamu transfer:", reply_markup=kb)
        return

    # ====== PILIH MONSTER UNTUK TRANSFER ======
    if data.startswith("TRANSFER_SELECT|"):
        monster_name = data.split("|", 1)[1]
        await cq.message.edit_text(
            f"🧾 Kamu memilih {monster_name}\n\n"
            f"Ketik format berikut di chat pribadi bot ini:\n"
            f"`@username trade jumlah`\n"
            f"Contoh: `@justforfun_admin trade 5` atau `@username 3`"
        )
        TRANSFER_STATE[user_id] = {"jenis": "monster", "monster": monster_name}
        return

    #TREASURE CHEST CALLBACK HANDLER
    if data == "TREASURE_SEND_NOW":
        if user_id != OWNER_ID:
            await cq.answer("❌ Hanya owner yang bisa kirim Treasure Chest!", show_alert=True)
            return
        await send_treasure_chest(client, cq)
        return

    # === PLAYER CLAIM TREASURE ===
    if data == "TREASURE_CLAIM":
        await handle_treasure_claim(client, cq)
        return

# === MENU SEDEKAH $$$ ===
    # ---------------- CALLBACK HANDLER ---------------- #
    if data == "SEDEKAH_TREASURE":
        await handle_sedekah_menu(client, cq)
        
    elif data == "SEDEKAH_SLOT_INPUT":
        # Minta user input slot di chat private
        await cq.message.reply(
            "💬 Silakan ketik jumlah slot penerima (5-100) di chat private."
        )

    elif data == "SEDEKAH_SEND":
        await handle_sedekah_send_menu(client, cq)
    elif data == "SEDEKAH_CANCEL":
        await handle_sedekah_cancel(client, cq)

        # === HANDLER KLAIM SEDEKAH ===
# callback_data format: "SEDEKAH_CLAIM:<chest_id>"
    if data.startswith("SEDEKAH_CLAIM"):
        try:
            # panggil handler klaim (fungsi sudah ada di file)
            await handle_sedekah_claim(client, cq)
        except Exception as e:
            logger.error(f"[SEDEKAH][ERROR] saat handle_sedekah_claim: {e}")
            # beri feedback ke user jika terjadi error
            try:
                await cq.answer("❌ Terjadi error saat klaim. Coba lagi nanti.", show_alert=True)
            except Exception:
                pass
        return


    # ====== MENU HASIL TANGKAPAN (LIHAT INVENTORY LENGKAP) ======
    if data == "FFF":
        inv_text = aquarium.list_inventory(user_id)
        kb = make_keyboard("FFF", user_id)
        await cq.message.edit_text(f"🎣 HASIL TANGKAPANMU:\n\n{inv_text}", reply_markup=kb)
        return
    
#Revisi Part ini aja
    # ===== EVOLVE SMALL FISH CONFIRM =====
    if data == "EVOLVE_SMALLFISH_CONFIRM":
        inv = aquarium.get_user_fish(user_id)
        small_fish_qty = inv.get("𓆝 Small Fish", 0)
        zonk_qty = inv.get("🤧 Zonk", 0)
        dna_qty = inv.get("🧬 Mysterious DNA", 0)

        if small_fish_qty < 1000:
            await cq.answer("❌ Small Fish kamu kurang (butuh 1000)", show_alert=True)
            return
        if zonk_qty < 50:
            await cq.answer("❌ 🤧 Zonk kamu kurang (butuh 100)", show_alert=True)
            return
        if dna_qty < 30:
            await cq.answer("❌ 🧬 Mysterious DNA kamu kurang (butuh 20)", show_alert=True)
            return

        # ✅ Kurangi stok bahan
        inv["𓆝 Small Fish"] = small_fish_qty - 1000
        if inv["𓆝 Small Fish"] <= 0: inv.pop("𓆝 Small Fish")
        inv["🤧 Zonk"] = zonk_qty - 50
        if inv["🤧 Zonk"] <= 0: inv.pop("🤧 Zonk")
        inv["🧬 Mysterious DNA"] = dna_qty - 30
        if inv["🧬 Mysterious DNA"] <= 0: inv.pop("🧬 Mysterious DNA")

        # ✅ Tambahkan hasil evolve
        inv["👹 Dark Fish Warrior"] = inv.get("👹 Dark Fish Warrior", 0) + 1

        # ✅ Simpan ke DB
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)

        uname = cq.from_user.username or f"user{user_id}"

        # ✅ Balasan private
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"✅ Evolve berhasil!\n"
            f"𓆝 Small Fish -1000\n"
            f"🤧 Zonk -50\n"
            f"🧬 Mysterious DNA -30\n"
            f"Dark Fish Warrior +1\n\n"
            f"📦 Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )

        # ✅ Info ke group + pin
        try:
            msg = await client.send_message(
                TARGET_GROUP,
                f"🧬 @{uname} berhasil evolve!\n"
                f"Small Fish → 👹 Dark Fish Warrior 🎉"
            )
            await client.pin_chat_message(TARGET_GROUP, msg.id, disable_notification=True)
        except Exception as e:
            logger.error(f"Gagal kirim atau pin info evolve ke group: {e}")

    # ===== EVOLVE HERMIT CRAB CONFIRM =====
    if data == "EVOLVE_SNAIL_CONFIRM":
        inv = aquarium.get_user_fish(user_id)
        snail_qty = inv.get("🐌 Snail", 0)
        zonk_qty = inv.get("🤧 Zonk", 0)
        dna_qty = inv.get("🧬 Mysterious DNA", 0)

        if snail_qty < 1000:
            await cq.answer("❌ Snail kamu kurang (butuh 1000)", show_alert=True)
            return
        if zonk_qty < 50:
            await cq.answer("❌ 🤧 Zonk kamu kurang (butuh 100)", show_alert=True)
            return
        if dna_qty < 30:
            await cq.answer("❌ 🧬 Mysterious DNA kamu kurang (butuh 20)", show_alert=True)
            return

        # ✅ Kurangi stok bahan
        inv["🐌 Snail"] = snail_qty - 1000
        if inv["🐌 Snail"] <= 0: inv.pop("🐌 Snail")
        inv["🤧 Zonk"] = zonk_qty - 50
        if inv["🤧 Zonk"] <= 0: inv.pop("🤧 Zonk")
        inv["🧬 Mysterious DNA"] = dna_qty - 30
        if inv["🧬 Mysterious DNA"] <= 0: inv.pop("🧬 Mysterious DNA")

        # ✅ Tambahkan hasil evolve
        inv["🐉 Snail Dragon"] = inv.get("🐉 Snail Dragon", 0) + 1

        # ✅ Simpan ke DB
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)

        uname = cq.from_user.username or f"user{user_id}"

        # ✅ Balasan private
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"✅ Evolve berhasil!\n"
            f"🐌 Snail -1000\n"
            f"🤧 Zonk -50\n"
            f"🧬 Mysterious DNA -30\n"
            f"🐉 Snail Dragon +1\n\n"
            f"📦 Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )

        # ✅ Info ke group + pin
        try:
            msg = await client.send_message(
                TARGET_GROUP,
                f"🧬 @{uname} berhasil evolve!\n"
                f"Snail → 🐉 Snail Dragon 🎉"
            )
            await client.pin_chat_message(TARGET_GROUP, msg.id, disable_notification=True)
        except Exception as e:
            logger.error(f"Gagal kirim atau pin info evolve ke group: {e}")

    # ===== EVOLVE HERMIT CRAB CONFIRM =====
    if data == "EVOLVE_HERMITCRAB_CONFIRM":
        inv = aquarium.get_user_fish(user_id)
        hermit_crab_qty = inv.get("🐚 Hermit Crab", 0)
        zonk_qty = inv.get("🤧 Zonk", 0)
        dna_qty = inv.get("🧬 Mysterious DNA", 0)

        if hermit_crab_qty < 1000:
            await cq.answer("❌ Hermit Crab kamu kurang (butuh 1000)", show_alert=True)
            return
        if zonk_qty < 50:
            await cq.answer("❌ 🤧 Zonk kamu kurang (butuh 100)", show_alert=True)
            return
        if dna_qty < 30:
            await cq.answer("❌ 🧬 Mysterious DNA kamu kurang (butuh 20)", show_alert=True)
            return

        # ✅ Kurangi stok bahan
        inv["🐚 Hermit Crab"] = hermit_crab_qty - 1000
        if inv["🐚 Hermit Crab"] <= 0: inv.pop("🐚 Hermit Crab")
        inv["🤧 Zonk"] = zonk_qty - 50
        if inv["🤧 Zonk"] <= 0: inv.pop("🤧 Zonk")
        inv["🧬 Mysterious DNA"] = dna_qty - 30
        if inv["🧬 Mysterious DNA"] <= 0: inv.pop("🧬 Mysterious DNA")

        # ✅ Tambahkan hasil evolve
        inv["👑 Queen of Hermit"] = inv.get("👑 Queen of Hermit", 0) + 1

        # ✅ Simpan ke DB
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)

        uname = cq.from_user.username or f"user{user_id}"

        # ✅ Balasan private
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"✅ Evolve berhasil!\n"
            f"🐚 Hermit Crab -1000\n"
            f"🤧 Zonk -50\n"
            f"🧬 Mysterious DNA -30\n"
            f"👑 Queen of Hermit +1\n\n"
            f"📦 Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )

        # ✅ Info ke group + pin
        try:
            msg = await client.send_message(
                TARGET_GROUP,
                f"🧬 @{uname} berhasil evolve!\n"
                f"Hermit Crab → 👑 Queen of Hermit 🎉"
            )
            await client.pin_chat_message(TARGET_GROUP, msg.id, disable_notification=True)
        except Exception as e:
            logger.error(f"Gagal kirim atau pin info evolve ke group: {e}")

    # ===== EVOLVE FROG CONFIRM =====
    if data == "EVOLVE_FROG_CONFIRM":
        inv = aquarium.get_user_fish(user_id)
        frog_qty = inv.get("🐸 Frog", 0)
        zonk_qty = inv.get("🤧 Zonk", 0)
        dna_qty = inv.get("🧬 Mysterious DNA", 0)

        if frog_qty < 1000:
            await cq.answer("❌ Frog kamu kurang (butuh 1000)", show_alert=True)
            return
        if zonk_qty < 50:
            await cq.answer("❌ 🤧 Zonk kamu kurang (butuh 100)", show_alert=True)
            return
        if dna_qty < 30:
            await cq.answer("❌ 🧬 Mysterious DNA kamu kurang (butuh 20)", show_alert=True)
            return

        # ✅ Kurangi stok bahan
        inv["🐸 Frog"] = frog_qty - 1000
        if inv["🐸 Frog"] <= 0: inv.pop("🐸 Frog")
        inv["🤧 Zonk"] = zonk_qty - 50
        if inv["🤧 Zonk"] <= 0: inv.pop("🤧 Zonk")
        inv["🧬 Mysterious DNA"] = dna_qty - 30
        if inv["🧬 Mysterious DNA"] <= 0: inv.pop("🧬 Mysterious DNA")

        # ✅ Tambahkan hasil evolve
        inv["🤖 Mecha Frog"] = inv.get("🤖 Mecha Frog", 0) + 1

        # ✅ Simpan ke DB
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)

        uname = cq.from_user.username or f"user{user_id}"

        # ✅ Balasan private
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"✅ Evolve berhasil!\n"
            f"🐸 Frog -1000\n"
            f"🤧 Zonk -50\n"
            f"🧬 Mysterious DNA -30\n"
            f"🤖 Mecha Frog +1\n\n"
            f"📦 Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )

        # ✅ Info ke group + pin
        try:
            msg = await client.send_message(
                TARGET_GROUP,
                f"🧬 @{uname} berhasil evolve!\n"
                f"Frog → 🤖 Mecha Frog 🎉"
            )
            await client.pin_chat_message(TARGET_GROUP, msg.id, disable_notification=True)
        except Exception as e:
            logger.error(f"Gagal kirim atau pin info evolve ke group: {e}")

    # ===== EVOLVE SNAKE CONFIRM =====
    if data == "EVOLVE_QUEENOFMEDUSA_CONFIRM":
        inv = aquarium.get_user_fish(user_id)
        snake_qty = inv.get("🐍 Snake", 0)
        zonk_qty = inv.get("🤧 Zonk", 0)
        dna_qty = inv.get("🧬 Mysterious DNA", 0)

        if snake_qty < 1000:
            await cq.answer("❌ Snake kamu kurang (butuh 1000)", show_alert=True)
            return
        if zonk_qty < 50:
            await cq.answer("❌ 🤧 Zonk kamu kurang (butuh 100)", show_alert=True)
            return
        if dna_qty < 30:
            await cq.answer("❌ 🧬 Mysterious DNA kamu kurang (butuh 20)", show_alert=True)
            return

        # ✅ Kurangi stok bahan
        inv["🐍 Snake"] = snake_qty - 1000
        if inv["🐍 Snake"] <= 0: inv.pop("🐍 Snake")
        inv["🤧 Zonk"] = zonk_qty - 50
        if inv["🤧 Zonk"] <= 0: inv.pop("🤧 Zonk")
        inv["🧬 Mysterious DNA"] = dna_qty - 30
        if inv["🧬 Mysterious DNA"] <= 0: inv.pop("🧬 Mysterious DNA")

        # ✅ Tambahkan hasil evolve
        inv["👑 Queen Of Medusa 🐍"] = inv.get("👑 Queen Of Medusa 🐍", 0) + 1

        # ✅ Simpan ke DB
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)

        uname = cq.from_user.username or f"user{user_id}"

        # ✅ Balasan private
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"✅ Evolve berhasil!\n"
            f"🐍 Snake -1000\n"
            f"🤧 Zonk -50\n"
            f"🧬 Mysterious DNA -30\n"
            f"👑 Queen Of Medusa 🐍 +1\n\n"
            f"📦 Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )

        # ✅ Info ke group + pin
        try:
            msg = await client.send_message(
                TARGET_GROUP,
                f"🧬 @{uname} berhasil evolve!\n"
                f"Snake → 👑 Queen Of Medusa 🐍 🎉"
            )
            await client.pin_chat_message(TARGET_GROUP, msg.id, disable_notification=True)
        except Exception as e:
            logger.error(f"Gagal kirim atau pin info evolve ke group: {e}")

    # ===== EVOLVE SNAKE CONFIRM =====
    if data == "EVOLVE_PRINCESSMERMAID_CONFIRM":
        inv = aquarium.get_user_fish(user_id)
        mermaidgirl_qty = inv.get("🧜‍♀️ Mermaid Girl", 0)
        axolotl_qty = inv.get("🐟 Axolotl", 0)
        doryfish_qty = inv.get("🐟 Doryfish", 0)
        dna_qty = inv.get("🧬 Mysterious DNA", 0)

        if mermaidgirl_qty < 5:
            await cq.answer("❌ 🧜‍♀️ Mermaid Girl kamu kurang (butuh 5)", show_alert=True)
            return
        if axolotl_qty < 50:
            await cq.answer("❌ 🐟 Axolotl kamu kurang (butuh 50)", show_alert=True)
            return
        if doryfish_qty < 50:
            await cq.answer("❌ 🐟 Doryfish kamu kurang (butuh 50)", show_alert=True)
            return
        if dna_qty < 30:
            await cq.answer("❌ 🧬 Mysterious DNA kamu kurang (butuh 50)", show_alert=True)
            return

        # ✅ Kurangi stok bahan
        inv["🧜‍♀️ Mermaid Girl"] = mermaidgirl_qty - 5
        if inv["🧜‍♀️ Mermaid Girl"] <= 0: inv.pop("🧜‍♀️ Mermaid Girl")
        inv["🐟 Axolotl"] = axolotl_qty - 50
        if inv["🐟 Axolotl"] <= 0: inv.pop("🐟 Axolotl")
        inv["🐟 Doryfish"] = doryfish_qty - 50
        if inv["🐟 Doryfish"] <= 0: inv.pop("🐟 Doryfish")
        inv["🧬 Mysterious DNA"] = dna_qty - 50
        if inv["🧬 Mysterious DNA"] <= 0: inv.pop("🧬 Mysterious DNA")

        # ✅ Tambahkan hasil evolve
        inv["👑 Princess Mermaid"] = inv.get("👑 Princess Mermaid", 0) + 1

        # ✅ Simpan ke DB
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)

        uname = cq.from_user.username or f"user{user_id}"

        # ✅ Balasan private
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"✅ Evolve berhasil!\n"
            f"🧜‍♀️ Mermaid Girl -5\n"
            f"🐟 Axolotl -50\n"
            f"🐟 Doryfish -50\n"
            f"🧬 Mysterious DNA -50\n"
            f"👑 Princess Mermaid +1\n\n"
            f"📦 Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )

        # ✅ Info ke group + pin
        try:
            msg = await client.send_message(
                TARGET_GROUP,
                f"🧬 @{uname} berhasil evolve!\n"
                f"Mermaid Girl → 👑🧜‍♀️ Princess Mermaid 🎉"
            )
            await client.pin_chat_message(TARGET_GROUP, msg.id, disable_notification=True)
        except Exception as e:
            logger.error(f"Gagal kirim atau pin info evolve ke group: {e}")

    # ===== EVOLVE 🧚 Sea Fairy CONFIRM =====
    if data == "EVOLVE_SEAFAIRY_CONFIRM":
        inv = aquarium.get_user_fish(user_id)
        goldfish_qty = inv.get("🐟 Goldfish", 0)
        stingrays_qty = inv.get("🐟 Stingrays Fish", 0)
        clownfish_qty = inv.get("🐟 Clownfish", 0)
        doryfish_qty = inv.get("🐟 Doryfish", 0)
        bannerfish_qty = inv.get("🐟 Bannerfish", 0)
        anglerfish_qty = inv.get("🐟 Anglerfish", 0)
        pufferfish_qty = inv.get("🐡 Pufferfish", 0)
        mermaidboy_qty = inv.get("🧜‍♀️ Mermaid Boy", 0)
        mermaidgirl_qty = inv.get("🧜‍♀️ Mermaid Girl", 0)
        zonk_qty = inv.get("🤧 Zonk", 0)
        dna_qty = inv.get("🧬 Mysterious DNA", 0)
        waterelement_qty = inv.get("✨ Water Element", 0)
    
        # ✅ Validasi stok bahan
        if mermaidboy_qty < 5:
            await cq.answer("❌ 🧜‍♀️ Mermaid Boy kamu kurang (butuh 50)", show_alert=True)
            return
        if mermaidgirl_qty < 5:
            await cq.answer("❌ 🧜‍♀️ Mermaid Girl kamu kurang (butuh 5)", show_alert=True)
            return
        if goldfish_qty < 50:
            await cq.answer("❌ 🐟 Goldfish kamu kurang (butuh 50)", show_alert=True)
            return
        if stingrays_qty < 50:
            await cq.answer("❌ 🐟 Stingrays Fish kamu kurang (butuh 50)", show_alert=True)
            return
        if clownfish_qty < 50:
            await cq.answer("❌ 🐟 Clownfish kamu kurang (butuh 50)", show_alert=True)
            return
        if doryfish_qty < 50:
            await cq.answer("❌ 🐟 Doryfish kamu kurang (butuh 50)", show_alert=True)
            return
        if bannerfish_qty < 50:
            await cq.answer("❌ 🐟 Bannerfish kamu kurang (butuh 50)", show_alert=True)
            return
        if anglerfish_qty < 50:
            await cq.answer("❌ 🐟 Anglerfish kamu kurang (butuh 50)", show_alert=True)
            return
        if pufferfish_qty < 50:
            await cq.answer("❌ 🐡 Pufferfish kamu kurang (butuh 50)", show_alert=True)
            return
        if zonk_qty < 100:
            await cq.answer("❌ 🤧 Zonk kamu kurang (butuh 200)", show_alert=True)
            return
        if dna_qty < 50:
            await cq.answer("❌ 🧬 Mysterious DNA kamu kurang (butuh 50)", show_alert=True)
            return
        if waterelement_qty < 20:
            await cq.answer("❌ ✨ Water Element kamu kurang (butuh 20)", show_alert=True)
            return
    
        # ✅ Kurangi stok bahan
        inv["🧜‍♀️ Mermaid Boy"] = mermaidboy_qty - 5
        if inv["🧜‍♀️ Mermaid Boy"] <= 0: inv.pop("🧜‍♀️ Mermaid Boy")
        inv["🧜‍♀️ Mermaid Girl"] = mermaidgirl_qty - 5
        if inv["🧜‍♀️ Mermaid Girl"] <= 0: inv.pop("🧜‍♀️ Mermaid Girl")
        inv["🐟 Goldfish"] = goldfish_qty - 50
        if inv["🐟 Goldfish"] <= 0: inv.pop("🐟 Goldfish")
        inv["🐟 Stingrays Fish"] = stingrays_qty - 50
        if inv["🐟 Stingrays Fish"] <= 0: inv.pop("🐟 Stingrays Fish")
        inv["🐟 Clownfish"] = clownfish_qty - 50
        if inv["🐟 Clownfish"] <= 0: inv.pop("🐟 Clownfish")
        inv["🐟 Doryfish"] = doryfish_qty - 50
        if inv["🐟 Doryfish"] <= 0: inv.pop("🐟 Doryfish")
        inv["🐟 Bannerfish"] = bannerfish_qty - 50
        if inv["🐟 Bannerfish"] <= 0: inv.pop("🐟 Bannerfish")
        inv["🐟 Anglerfish"] = anglerfish_qty - 50
        if inv["🐟 Anglerfish"] <= 0: inv.pop("🐟 Anglerfish")
        inv["🐡 Pufferfish"] = pufferfish_qty - 50
        if inv["🐡 Pufferfish"] <= 0: inv.pop("🐡 Pufferfish")
        inv["🤧 Zonk"] = zonk_qty - 100
        if inv["🤧 Zonk"] <= 0: inv.pop("🤧 Zonk")
        inv["🧬 Mysterious DNA"] = dna_qty - 50
        if inv["🧬 Mysterious DNA"] <= 0: inv.pop("🧬 Mysterious DNA")
        inv["✨ Water Element"] = waterelement_qty - 20
        if inv["✨ Water Element"] <= 0: inv.pop("✨ Water Element")
    
        # ✅ Tambahkan hasil evolve
        inv["🧚 Sea Fairy"] = inv.get("🧚 Sea Fairy", 0) + 1
    
        # ✅ Simpan ke DB
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)
    
        uname = cq.from_user.username or f"user{user_id}"
    
        # ✅ Balasan private
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"✅ Evolve berhasil!\n"
            f"🧜‍♀️ Mermaid Girl -5\n"
            f"🐟 Goldfish -50\n"
            f"🐟 Stingrays Fish -50\n"
            f"🐟 Clownfish -50\n"
            f"🐟 Doryfish -50\n"
            f"🐟 Bannerfish -50\n"
            f"🐟 Anglerfish -50\n"
            f"🐡 Pufferfish -50\n"
            f"🧜‍♀️ Mermaid Boy -50\n"
            f"🤧 Zonk -100\n"
            f"🧬 Mysterious DNA -50\n"
            f"✨ Water Element -20\n"
            f"🧚 Sea Fairy +1\n\n"
            f"📦 Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )
    
        # ✅ Info ke group + pin
        try:
            msg = await client.send_message(
                TARGET_GROUP,
                f"🧬 @{uname} berhasil evolve!\n"
                f" Sea Creatures → 🧚 Sea Fairy 🎉"
            )
            await client.pin_chat_message(TARGET_GROUP, msg.id, disable_notification=True)
        except Exception as e:
            logger.error(f"Gagal kirim atau pin info evolve ke group: {e}")
#
    # ===== EVOLVE ⚡ Raichu CONFIRM =====
    if data == "EVOLVE_RAICHU_CONFIRM":
        inv = aquarium.get_user_fish(user_id)
        pikachu_qty = inv.get("🐹⚡ Pikachu", 0)
        thunder_qty = inv.get("✨ Thunder Element", 0)
        dna_qty = inv.get("🧬 Mysterious DNA", 0)
    
        if pikachu_qty < 50:
            await cq.answer("❌ 🐹⚡ Pikachu kamu kurang (butuh 50)", show_alert=True)
            return
        if thunder_qty < 30:
            await cq.answer("❌ ✨ Thunder Element kamu kurang (butuh 30)", show_alert=True)
            return
        if dna_qty < 30:
            await cq.answer("❌ 🧬 Mysterious DNA kamu kurang (butuh 30)", show_alert=True)
            return
    
        inv["🐹⚡ Pikachu"] -= 50
        inv["✨ Thunder Element"] -= 30
        inv["🧬 Mysterious DNA"] -= 30
        inv["🐹⚡ Raichu"] = inv.get("🐹⚡ Raichu", 0) + 1
    
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)
    
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"✅ Evolve berhasil!\n"
            f"🐹⚡ Pikachu -50\n✨ Thunder Element -30\n🧬 Mysterious DNA -30\n🐹⚡ Raichu +1\n\n📦 Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )
    
        uname = cq.from_user.username or f"user{user_id}"
        msg = await client.send_message(
            TARGET_GROUP,
            f"⚡ @{uname} berhasil evolve!\nPikachu → 🐹⚡ Raichu 🎉"
        )
        await client.pin_chat_message(TARGET_GROUP, msg.id, disable_notification=True)
        return


    # ===== RESET LOGIN (OWNER ONLY) =====
    if data == "LOGIN_RESET":
        if user_id != OWNER_ID:
            await cq.answer("❌ Hanya owner yang bisa reset login.", show_alert=True)
            return
        LOGIN_STATE.clear()
        await cq.message.edit_text("✅ Semua data login harian telah direset.", reply_markup=make_keyboard("G", user_id))
        return

    elif data == "LOGIN_STATUS":
        # tampilkan 7 hari terakhir streak user
        init_user_login(user_id)
        user_login = LOGIN_STATE[user_id]
        streak = user_login["streak"]

        status_text = "📅 Status LOGIN 7 Hari Terakhir:\n"
        for i in range(7):
            status_text += f"LOGIN-{i+1}: "
            status_text += "✅" if streak >= i + 1 else "❌"
            status_text += "\n"

        await cq.message.edit_text(status_text, reply_markup=make_keyboard("G", user_id))
        return

    # MENU OPEN untuk login, tombol navigasi
    elif data == "G":
        # tampilkan menu LOGIN HARIAN
        buttons = [
            [InlineKeyboardButton("✅ Absen Hari Ini", callback_data="LOGIN_TODAY")],
            [InlineKeyboardButton("📅 Lihat Status Login 7 Hari", callback_data="LOGIN_STATUS")],
            [InlineKeyboardButton("⬅️ Back", callback_data="main")]
        ]
        kb = InlineKeyboardMarkup(buttons)
        await cq.message.edit_text("📋 LOGIN HARIAN", reply_markup=kb)
        return

    # ---------------- REGISTER FLOW ---------------- #
    if data == "REGISTER_YES":
        uname = cq.from_user.username or "TanpaUsername"
        text = "🎉 Selamat kamu menjadi Player Loot!"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📇 SCAN ID & USN", callback_data="REGISTER_SCAN")],
            [InlineKeyboardButton("⬅️ Back", callback_data="main")]
        ])
        await cq.message.edit_text(text, reply_markup=kb)
        user_database.set_player_loot(user_id, True, uname)
        try:
            await client.send_message(
                OWNER_ID,
                f"📢 [REGISTER] Player baru mendaftar!\n\n👤 Username: @{uname}\n🆔 User ID: {user_id}"
            )
        except Exception as e:
            logger.error(f"Gagal kirim notif register ke owner: {e}")
        return

    if data == "REGISTER_SCAN":
        uname = cq.from_user.username or "TanpaUsername"
        text = f"📇 Data Player\n\n👤 Username: @{uname}\n🆔 User ID: {user_id}"
        await cq.message.edit_text(text, reply_markup=make_keyboard("main", user_id))
        return

    # TRANSFER START
    if data.startswith("TRANSFER_"):
        jenis = data.split("_")[1]
        map_jenis = {"COMMON": "A", "RARE": "B", "LEGEND": "C", "MYTHIC": "D"}

        # 🔒 Batasi transfer umpan Rare hanya untuk OWNER
        if jenis == "RARE" and user_id != OWNER_ID:
            await cq.answer("❌ Hanya OWNER yang bisa transfer Umpan Rare 🐌.", show_alert=True)
            return

        TRANSFER_STATE[user_id] = {"jenis": map_jenis.get(jenis)}
        await cq.message.reply("✍️ Masukkan format transfer: `@username jumlah`\nContoh: `@user 2`")
        return

    # CHECK COIN Fizz
    # ================= CEK COIN & SUBMENU ================= #
    if data == "D2C":
        kb = make_keyboard("D2C_MENU", cq.from_user.id)
        await cq.message.edit_text("💰 Pilih menu tukar coin:", reply_markup=kb)
        return

    elif data == "D2C_COMMON_A":
        uid = cq.from_user.id
        total_coin = fizz_coin.get_coin(uid)
        TUKAR_COIN_STATE[uid] = {"jenis": "A"}
        await cq.message.edit_text(
            f"🐛 Kamu punya {total_coin} fizz coin.\n\n"
            f"Masukkan jumlah coin yang ingin kamu tukarkan.\n"
            f"(5 coin = 1 umpan Common Type A)\n\n"
            f"Contoh: `25` untuk menukar 25 coin jadi 5 umpan.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Batal", callback_data="D2C_MENU")]])
        )
        return

    elif data == "D2C_COMMON_B":
        uid = cq.from_user.id
        total_coin = fizz_coin.get_coin(uid)
        TUKAR_COIN_STATE[uid] = {"jenis": "B"}
        await cq.message.edit_text(
            f"🪱 Kamu punya {total_coin} fizz coin.\n\n"
            f"Masukkan jumlah coin yang ingin kamu tukarkan.\n"
            f"(50 coin = 1 umpan Rare Type B)\n\n"
            f"Contoh: `50` untuk menukar 50 coin jadi 1 umpan.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Batal", callback_data="D2C_MENU")]])
        )
        return
    
    # FISHING
# FISHING
    # ----------------- FUNGSI MEMANCING -----------------
    async def fishing_task(client, uname, user_id, jenis, task_id):
        try:
            await asyncio.sleep(2)
            # Pesan di grup sekarang termasuk task_id
           #await client.send_message(TARGET_GROUP, f"```\n🎣 @{uname} trying to catch... task#{task_id}```\n")

            # Jalankan loot system
            loot_result = await fishing_loot(client, None, uname, user_id, umpan_type=jenis)

            # ==== Kurangi umpan setelah hasil drop keluar ====
            jk_map = {"COMMON": "A", "RARE": "B", "LEGEND": "C", "MYTHIC": "D"}
            jk = jk_map.get(jenis, "A")

            if user_id != OWNER_ID:
                ud = umpan.get_user(user_id)
                if not ud or ud.get(jk, {}).get("umpan", 0) <= 0:
                    # kalau ternyata umpan habis (misal paralel auto catching), kasih info
                    await client.send_message(user_id, "❌ Umpanmu habis, hasil pancingan ini batal.")
                    return
                umpan.remove_umpan(user_id, jk, 1)

            await asyncio.sleep(10)
            # Hanya kirim ke grup, hapus private
            msg_group = f"🎣 @{uname} got {loot_result}! from task#{task_id}"
            await client.send_message(TARGET_GROUP, msg_group)

        except Exception as e:
            logger.error(f"[FISHING TASK] Error untuk @{uname}: {e}")

    # ----------------- CALLBACK HANDLER -----------------
    if data.startswith("FISH_CONFIRM_"):
        jenis = data.replace("FISH_CONFIRM_", "")
        uname = cq.from_user.username or f"user{user_id}"

        # Tombol Back
        kb_back = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="E")]])

        # Cek umpan cukup dulu (tanpa mengurangi)
        jk_map = {"COMMON": "A", "RARE": "B", "LEGEND": "C", "MYTHIC": "D"}
        jk = jk_map.get(jenis, "A")
        if user_id != OWNER_ID:
            ud = umpan.get_user(user_id)
            if not ud or ud.get(jk, {}).get("umpan", 0) <= 0:
                await cq.answer("❌ Umpan tidak cukup!", show_alert=True)
                return

        now = asyncio.get_event_loop().time()
        last_time = user_last_fishing[user_id]

        if now - last_time < 10:
            await cq.message.edit_text(
                "⏳ Wait a sec before you catch again..",
                reply_markup=kb_back
            )
            return

        user_last_fishing[user_id] = now
        user_task_count[user_id] += 1
        task_id = f"{user_task_count[user_id]:02d}"
        # di bagian callback FISH_CONFIRM_
        await cq.message.edit_text(
            f"🎣 You successfully threw the bait! {jenis} to loot task#{task_id}!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎣 Catch again", callback_data=f"FISH_CONFIRM_{jenis}")],
                [InlineKeyboardButton("🤖 Auto Catch 20x", callback_data=f"AUTO_FISH_{jenis}")],
                [InlineKeyboardButton("❌ Cancel Auto", callback_data="AUTO_FISH_CANCEL")],  # tombol baru
                [InlineKeyboardButton("⬅️ Back", callback_data="E")]
            ])
        )

        # Jalankan task memancing
        asyncio.create_task(fishing_task(client, uname, user_id, jenis, task_id))

    # ----------------- AUTO MEMANCING 5x -----------------
    # callback handler AUTO_FISH_ 
    elif data == "AUTO_FISH_CANCEL":
        task = AUTO_FISH_TASKS.get(user_id)
        if task and not task.done():
            task.cancel()
            await cq.answer("❌ Auto Fishing cancelled!", show_alert=True)
            AUTO_FISH_TASKS.pop(user_id, None)
        else:
            await cq.answer("❌ Tidak ada auto fishing aktif.", show_alert=True)
        return  # jangan lanjut ke auto fishing

    # 2️⃣ Handle Auto Fishing 20x
    elif data.startswith("AUTO_FISH_"):
        jenis = data.replace("AUTO_FISH_", "")
        uname = cq.from_user.username or f"user{user_id}"

        await cq.answer("🤖 Auto Catching 20x!!! Start!")

        async def auto_fishing():
            try:
                for i in range(20):
                    now = asyncio.get_event_loop().time()
                    if now - user_last_fishing.get(user_id, 0) < 10:
                        break
                    jk_map = {"COMMON": "A", "RARE": "B", "LEGEND": "C", "MYTHIC": "D"}
                    jk = jk_map.get(jenis, "A")
                    if user_id != OWNER_ID:
                        ud = umpan.get_user(user_id)
                        if not ud or ud.get(jk, {}).get("umpan", 0) <= 0:
                            break
                    user_last_fishing[user_id] = now
                    user_task_count[user_id] += 1
                    task_id = f"{user_task_count[user_id]:02d}"
                    await fishing_task(cq._client, uname, user_id, jenis, task_id)
                    await asyncio.sleep(10)
            except asyncio.CancelledError:
                await cq.message.reply("❌ Auto Fishing dibatalkan.")
                return

        # simpan task auto fishing agar bisa cancel
        task_obj = asyncio.create_task(auto_fishing())
        AUTO_FISH_TASKS[user_id] = task_obj

    # LEADERBOARD PAGING
    if data.startswith("BBB_PAGE_"):
        page = int(data.replace("BBB_PAGE_", ""))
        await show_leaderboard(cq, user_id, page)
        return

    # POIN PRIBADI
    if data == "BB":
        pts = yapping.load_points()
        udata = pts.get(str(user_id))
        if not udata:
            text = "❌ Kamu belum punya poin."
        else:
            lvl = udata.get("level", 0)
            badge = yapping.get_badge(lvl)
            text = f"📊 Poin Pribadi\n\n👤 {udata.get('username','Unknown')}\n⭐ {udata.get('points',0)} pts\n🏅 Level {lvl} {badge}"
        await cq.message.edit_text(text, reply_markup=make_keyboard("BB", user_id))
        return

    # LEADERBOARD
    if data == "BBB":
        await show_leaderboard(cq, user_id, 0)
        return

    # TUKAR POINT
    if data == "TUKAR_POINT":
        TUKAR_POINT_STATE[user_id] = {"step": 1, "jumlah_umpan": 0}
        await cq.message.reply("Masukkan jumlah umpan COMMON 🐛 yang ingin ditukar (100 poin = 1 umpan):")
        return

    # ---------------- TUKAR POINT CONFIRM ---------------- #
    if data == "TUKAR_CONFIRM":
        info = TUKAR_POINT_STATE.get(user_id)
        if not info or info.get("step") != 2:
            await cq.answer("❌ Proses tidak valid.", show_alert=True)
            return
        jml = info["jumlah_umpan"]
        pts = yapping.load_points().get(str(user_id), {}).get("points", 0)
        if pts < jml * 100:
            await cq.answer("❌ Point tidak cukup.", show_alert=True)
            TUKAR_POINT_STATE.pop(user_id, None)
            return
        # lakukan tukar
        yapping.update_points(user_id, -jml * 100)
        umpan.add_umpan(user_id, "A", jml)  # ✅ hanya COMMON
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="D3A")]])
        await cq.message.edit_text(
            f"✅ Tukar berhasil! {jml} umpan COMMON 🐛 ditambahkan ke akunmu.", reply_markup=kb
        )
        TUKAR_POINT_STATE.pop(user_id, None)
        return

    # SELL FLOW: DETAIL -> START -> CONFIRM / CANCEL
    # data format: SELL_DETAIL:<code> , SELL_START:<code> , SELL_CONFIRM:<code>:<amount> , SELL_CANCEL
    if data.startswith("SELL_DETAIL:"):
        item_code = data.split(":", 1)[1]
        item = ITEM_PRICES.get(item_code)
        if not item:
            await cq.answer("Item tidak ditemukan.", show_alert=True)
            return
        # show price + opsi jual (mulai)
        text = f"💰 Harga {item['name']}\n1x = {item['price']} coin\n\nKetik jumlah yang ingin kamu jual, atau pilih tombol untuk mulai."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Jual Sekarang (ketik jumlah)", callback_data=f"SELL_START:{item_code}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="D2B")]
        ])
        await cq.message.edit_text(text, reply_markup=kb)
        return

    if data.startswith("SELL_START:"):
        item_code = data.split(":", 1)[1]
        # tandai user menunggu input jumlah via chat
        SELL_WAITING[user_id] = item_code
        item = ITEM_PRICES.get(item_code)
        if not item:
            await cq.answer("Item tidak ditemukan.", show_alert=True)
            SELL_WAITING.pop(user_id, None)
            return
        await cq.message.edit_text(f"📝 Ketik jumlah {item['name']} yang ingin kamu jual (contoh: 2)\nKetik 0 untuk batal.")
        return

    if data.startswith("SELL_CONFIRM:"):
        # format SELL_CONFIRM:<code>:<amount>
        parts = data.split(":")
        if len(parts) != 3:
            await cq.answer("Data konfirmasi tidak valid.", show_alert=True)
            return
        item_code = parts[1]
        try:
            amount = int(parts[2])
        except ValueError:
            await cq.answer("Jumlah tidak valid.", show_alert=True)
            return
        item = ITEM_PRICES.get(item_code)
        if not item:
            await cq.answer("Item tidak ditemukan.", show_alert=True)
            return

        # load DB, cek stok (menggunakan normalisasi key)
        db = aquarium.load_data()
        user_inv = db.get(str(user_id), {}) or {}
        # buat mapping normalized_key -> (orig_key, value)
        normalized_inv = {}
        for k, v in user_inv.items():
            norm = normalize_key(k)
            normalized_inv[norm] = (k, v)

        target_norm = normalize_key(item["inv_key"])  # normalisasi inv_key
        # cek alias mapping juga
        canon_key = None
        if target_norm in normalized_inv:
            canon_key, stock = normalized_inv[target_norm]
        else:
            # coba cari lewat INV_KEY_ALIASES dan perbandingan terhadap normalized ITEM_PRICES
            # attempt: match any inventory key to this item
            stock = 0
            for orig_k, val in user_inv.items():
                if canonical_inv_key_from_any(orig_k) == item["inv_key"]:
                    canon_key = orig_k
                    stock = val
                    break

        if amount <= 0 or amount > stock:
            await cq.answer("Stok tidak cukup atau jumlah salah.", show_alert=True)
            return

        # kurangi stok
        new_stock = stock - amount
        if new_stock > 0:
            user_inv[canon_key or item["inv_key"]] = new_stock
        else:
            # hapus key jika 0
            user_inv.pop(canon_key or item["inv_key"], None)

        db[str(user_id)] = user_inv
        try:
            aquarium.save_data(db)
        except Exception as e:
            logger.error(f"Gagal save aquarium setelah jual: {e}")
            await cq.answer("Gagal menyimpan data. Coba lagi nanti.", show_alert=True)
            return

        earned = amount * item["price"]
        new_total = fizz_coin.add_coin(user_id, earned)  # ✅ simpan ke database
        await cq.message.reply_text(
            f"✅ Berhasil menjual {amount}x {item['name']}.\n"
            f"Kamu mendapatkan {earned} coin fizz.\n"
            f"💰 Total coinmu sekarang: {new_total} fizz coin\n"
            f"Sisa stok {item['name']}: {new_stock}",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("⬅️ Back", callback_data="D2")]
                ]
            )
        )
        return

    if data == "SELL_CANCEL":
        SELL_WAITING.pop(user_id, None)
        # lebih aman fallback ke D2 jika ada, kalau tidak ada ke main
        try:
            await cq.message.edit_text("❌ Penjualan dibatalkan.", reply_markup=make_keyboard("D2", user_id))
        except Exception:
            await cq.message.edit_text("❌ Penjualan dibatalkan.", reply_markup=make_keyboard("main", user_id))
        return

    # CEK INVENTORY STORE
    # CEK INVENTORY STORE (PAKAI FORMAT LIST FULL INVENTORY)
    if data == "D2A":
        inv_text = list_full_inventory(user_id)
        kb = make_keyboard("D2A", user_id)
        await cq.message.edit_text(inv_text, reply_markup=kb)
        return

    # CEK INVENTORY (hasil tangkapan)
    if data == "FFF":
        inv_text = aquarium.list_inventory(user_id)
        kb = make_keyboard("FFF", user_id)
        await cq.message.edit_text(f"🎣 HASIL TANGKAPANMU:\n\n{inv_text}", reply_markup=kb)
        return
 
    # NAVIGASI MENU
    if data in MENU_STRUCTURE:
        await cq.message.edit_text(MENU_STRUCTURE[data]["title"], reply_markup=make_keyboard(data, user_id))
        return

# ---------------- HANDLE TRANSFER, TUKAR & SELL AMOUNT (TEXT INPUT) ---------------- #
async def handle_transfer_message(client: Client, message: Message):
    uid = message.from_user.id
    uname = message.from_user.username or f"user{uid}"

    # SELL AMOUNT via chat (user previously pressed SELL_START -> SELL_WAITING populated)
    if SELL_WAITING.get(uid):
        item_code = SELL_WAITING.pop(uid)
        item = ITEM_PRICES.get(item_code)
        if not item:
            return await message.reply("Item tidak ditemukan. Proses dibatalkan.")
        text = message.text.strip()
        # allow '0' to cancel
        if not text.isdigit():
            return await message.reply("Format salah. Masukkan angka jumlah yang ingin dijual.")
        amount = int(text)
        if amount <= 0:
            return await message.reply("Penjualan dibatalkan (jumlah <= 0).")

        # cek stok menggunakan normalisasi
        db = aquarium.load_data()
        user_inv = db.get(str(uid), {}) or {}
        normalized_inv = {}
        for k, v in user_inv.items():
            normalized_inv[normalize_key(k)] = (k, v)

        target_norm = normalize_key(item["inv_key"])  # target inv_key normal
        canon_key = None
        stock = 0
        if target_norm in normalized_inv:
            canon_key, stock = normalized_inv[target_norm]
        else:
            for orig_k, val in user_inv.items():
                if canonical_inv_key_from_any(orig_k) == item["inv_key"]:
                    canon_key = orig_k
                    stock = val
                    break

        if stock <= 0:
            return await message.reply(f"❌ Kamu tidak memiliki {item['name']} sama sekali.")
        if amount > stock:
            return await message.reply(f"❌ Stok tidak cukup ({stock} pcs).")

        # minta konfirmasi dengan tombol YA/TIDAK
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Ya", callback_data=f"SELL_CONFIRM:{item_code}:{amount}"),
                InlineKeyboardButton("❌ Tidak", callback_data="SELL_CANCEL")
            ]
        ])
        return await message.reply(
            f"📌 Konfirmasi\nApakah kamu yakin ingin menjual {amount}x {item['name']}?\nStok kamu: {stock}",
            reply_markup=kb
        )

# TRANSFER (existing) -> handle both UMPAN and MONSTER
# ================== TRANSFER HANDLER (UMPAN + MONSTER) ================== #
    if TRANSFER_STATE.get(uid):
        try:
            jenis = TRANSFER_STATE[uid]["jenis"]
    
# =====================================================
# 🔹 MONSTER TRANSFER SYSTEM (debug + notif grup)
# =====================================================
            if jenis == "monster":
    
                text = message.text.strip()
                logging.info(f"[DEBUG][TRANSFER_MONSTER] Pesan diterima dari {uid}: {text}")
    
                # Format fleksibel:
                # - @username trade 5
                # - @username 5
                # - 123456789 trade 3
                # - usernameaja 2
                m = re.match(
                    r"^\s*(?P<target>@[A-Za-z0-9_]+|\d+|[A-Za-z0-9_]+)\s*(?:trade\s*)?(?P<amt>\d+)\s*$",
                    text,
                    re.IGNORECASE
                )
                if not m:
                    logging.warning(f"[DEBUG][TRANSFER_MONSTER] Format salah dari user {uid}: {text}")
                    return await message.reply(
                        "❌ Format salah.\nGunakan contoh:\n`@username trade 5` atau `123456789 2`"
                    )
    
                target_raw = m.group("target")
                amt = int(m.group("amt"))
                if amt <= 0:
                    return await message.reply("❌ Jumlah harus lebih dari 0.")
    
                # Dapatkan user target
                try:
                    if target_raw.isdigit():
                        target_user = await client.get_users(int(target_raw))
                    else:
                        if not target_raw.startswith("@"):
                            target_raw = "@" + target_raw
                        target_user = await client.get_users(target_raw)
                except Exception as e:
                    logging.error(f"[DEBUG][TRANSFER_MONSTER] Gagal dapat user target ({target_raw}): {e}")
                    return await message.reply("❌ Username atau user_id tidak valid.")
    
                rid = target_user.id
                monster_name = TRANSFER_STATE[uid].get("monster")
    
                # Load data aquarium
                data = aquarium.load_data()
                str_uid = str(uid)
                str_rid = str(rid)
    
                # Validasi kepemilikan monster
                if str_uid not in data or monster_name not in data[str_uid]:
                    logging.warning(f"[DEBUG][TRANSFER_MONSTER] User {uid} tidak memiliki {monster_name}")
                    return await message.reply("❌ Kamu tidak memiliki monster itu.")
                if data[str_uid][monster_name] < amt:
                    logging.warning(
                        f"[DEBUG][TRANSFER_MONSTER] Stok {monster_name} user {uid} tidak cukup "
                        f"({data[str_uid][monster_name]} tersedia, {amt} diminta)"
                    )
                    return await message.reply(f"❌ Stok {monster_name} kamu tidak cukup ({data[str_uid][monster_name]} tersedia).")
    
                # Kurangi dari pengirim
                old_qty_sender = data[str_uid][monster_name]
                data[str_uid][monster_name] -= amt
                if data[str_uid][monster_name] <= 0:
                    del data[str_uid][monster_name]
                logging.info(f"[DEBUG][TRANSFER_MONSTER] {uid} mengurangi {amt}x {monster_name} "
                             f"(sebelum: {old_qty_sender}, sesudah: {data.get(str_uid, {}).get(monster_name, 0)})")
    
                # Tambahkan ke penerima
                if str_rid not in data:
                    data[str_rid] = {}
                old_qty_receiver = data[str_rid].get(monster_name, 0)
                data[str_rid][monster_name] = old_qty_receiver + amt
                logging.info(f"[DEBUG][TRANSFER_MONSTER] {rid} menambahkan {amt}x {monster_name} "
                             f"(sebelum: {old_qty_receiver}, sesudah: {data[str_rid][monster_name]})")
    
                # Simpan perubahan
                aquarium.save_data(data)
    
                # Notifikasi ke pengirim
                await message.reply(f"✅ Kamu berhasil mentransfer **{amt}x {monster_name}** ke {target_user.mention}!")
    
                # Notifikasi ke penerima
                try:
                    await client.send_message(rid, f"🎁 Kamu menerima **{amt}x {monster_name}** dari {message.from_user.mention}!")
                except Exception as e:
                    logging.warning(f"[DEBUG][TRANSFER_MONSTER] Gagal kirim DM ke penerima ({rid}): {e}")
    
                # Notifikasi ke grup
                try:
                    await client.send_message(
                        TARGET_GROUP,
                        f"📢 {message.from_user.mention} berhasil mentransfer {amt}x {monster_name} ke {target_user.mention}!"
                    )
                except Exception as e:
                    logging.warning(f"[DEBUG][TRANSFER_MONSTER] Gagal kirim notifikasi ke grup: {e}")
    
                # Hapus state transfer
                TRANSFER_STATE.pop(uid, None)
                return

# =====================================================
# 🔹 UMPAN TRANSFER SYSTEM (A/B/C/D)
# =====================================================
            parts = message.text.strip().split()
            if len(parts) != 2:
                return await message.reply("Format salah. Contoh: @username 1")
            rname, amt = parts
            if not rname.startswith("@"):
                return await message.reply("Username harus diawali '@'.")
            try:
                amt = int(amt)
            except ValueError:
                return await message.reply("Jumlah harus angka. Contoh: @username 1")

            if amt <= 0:
                return await message.reply("Jumlah harus > 0.")

            # Cari user target di database
            rid = user_database.get_user_id_by_username(rname)
            if rid is None:
                await message.reply(f"❌ Username {rname} tidak ditemukan di database!")
                TRANSFER_STATE.pop(uid, None)
                return

            # Hanya OWNER yang bisa transfer Umpan Rare (B)
            if jenis == "B" and uid != OWNER_ID:
                await message.reply("❌ Hanya OWNER yang bisa transfer Umpan Rare 🐌.")
                TRANSFER_STATE.pop(uid, None)
                return

            # Jalankan transfer umpan
            if uid == OWNER_ID:
                umpan.add_umpan(rid, jenis, amt)
            else:
                sd = umpan.get_user(uid)
                if sd[jenis]["umpan"] < amt:
                    return await message.reply("❌ Umpan kamu tidak cukup!")
                umpan.remove_umpan(uid, jenis, amt)
                umpan.add_umpan(rid, jenis, amt)

            # Notifikasi pengirim
            await message.reply(
                f"✅ Transfer {amt} umpan ke {rname} berhasil!",
                reply_markup=make_keyboard("main", uid)
            )

            # Notifikasi penerima
            try:
                await asyncio.sleep(0.5)
                await client.send_message(rid, f"🎁 Kamu mendapat {amt} umpan dari @{uname}")
            except Exception as e:
                logger.error(f"Gagal kirim notif ke {rid}: {e}")

            # Notifikasi ke group
            try:
                await asyncio.sleep(2)
                await client.send_message(
                    TARGET_GROUP,
                    f"📢 Transfer Umpan!\n👤 @{uname} memberi {amt} umpan {jenis} ke {rname}"
                )
            except Exception as e:
                logger.error(f"Gagal kirim notif group: {e}")

        except Exception as e:
            await message.reply(f"❌ Error: {e}")
            TRANSFER_STATE.pop(uid, None)
        return

# ================= TUKAR COIN KE UMPAN ================= #
    # TUKAR POINT (existing)
    if TUKAR_POINT_STATE.get(uid):
        step = TUKAR_POINT_STATE[uid].get("step", 0)
        if step != 1:
            return
        try:
            jumlah = int(message.text.strip())
            if jumlah <= 0:
                return await message.reply("Jumlah umpan harus > 0.")
            pts = yapping.load_points().get(str(uid), {}).get("points", 0)
            if pts < jumlah * 100:
                return await message.reply(f"❌ Point tidak cukup ({pts} pts, butuh {jumlah * 100} pts).")
            TUKAR_POINT_STATE[uid]["jumlah_umpan"] = jumlah
            TUKAR_POINT_STATE[uid]["step"] = 2
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ YA", callback_data="TUKAR_CONFIRM")],
                [InlineKeyboardButton("❌ Batal", callback_data="D3A")]
            ])
            await message.reply(f"📊 Yakin ingin menukar {jumlah} umpan COMMON 🐛?\n(100 chat points = 1 umpan)", reply_markup=kb)
        except ValueError:
            await message.reply("Format salah. Masukkan angka jumlah umpan.")
        return

# ================= TUKAR COIN KE UMPAN ================= #
    uid = message.from_user.id

    if TUKAR_COIN_STATE.get(uid):
        jenis = TUKAR_COIN_STATE[uid]["jenis"]
        try:
            jumlah_coin = int(message.text.strip())
            if jumlah_coin <= 0:
                await message.reply("❌ Jumlah coin harus lebih dari 0.")
                return

            total_coin = fizz_coin.get_coin(uid)
            if jumlah_coin > total_coin:
                await message.reply(f"❌ Coin kamu tidak cukup. Kamu hanya punya {total_coin} fizz coin.")
                return

            # Set parameter berdasarkan jenis
            if jenis == "A":
                min_coin, konversi, nama, emoji = 5, 5, "COMMON (Type A)", "🐛"
            elif jenis == "B":
                min_coin, konversi, nama, emoji = 50, 50, "RARE (Type B)", "🪱"
            else:
                await message.reply("❌ Tipe tukar tidak valid.")
                return

            if jumlah_coin < min_coin:
                await message.reply(f"❌ Minimal {min_coin} coin untuk tukar 1 umpan {nama}.")
                return

            # Hitung jumlah umpan yang bisa didapat
            umpan_didapat = jumlah_coin // konversi
            biaya = umpan_didapat * konversi
            sisa_coin = jumlah_coin - biaya  # coin yang tidak habis dibagi tetap tersisa di user

            if umpan_didapat == 0:
                await message.reply(f"❌ Coin tidak cukup untuk ditukar menjadi umpan {nama}.")
                return

            # Kurangi coin & tambahkan umpan
            fizz_coin.add_coin(uid, -biaya)
            umpan.add_umpan(uid, jenis, umpan_didapat)

            await message.reply(
                f"✅ Tukar berhasil!\n\n"
                f"💰 -{biaya} fizz coin\n"
                f"{emoji} +{umpan_didapat} Umpan {nama}\n\n"
                f"Sisa coin: {fizz_coin.get_coin(uid)}",
                reply_markup=make_keyboard("D2C_MENU", uid)
            )

        except ValueError:
            await message.reply("❌ Format salah. Masukkan angka jumlah coin yang ingin ditukar.")
        finally:
            TUKAR_COIN_STATE.pop(uid, None)
        return

# ---------------- SHOW LEADERBOARD ---------------- #
async def show_leaderboard(cq: CallbackQuery, uid: int, page: int = 0):
    pts = yapping.load_points()
    sorted_pts = sorted(pts.items(), key=lambda x: x[1]["points"], reverse=True)
    total_pages = max((len(sorted_pts) - 1) // 10, 0) if len(sorted_pts) > 0 else 0
    start, end = page * 10, page * 10 + 10
    text = f"🏆 Leaderboard Yapping (Page {page+1}/{total_pages+1}) 🏆\n\n"
    for i, (u, pdata) in enumerate(sorted_pts[start:end], start=start + 1):
        text += f"{i}. {pdata.get('username','Unknown')} - {pdata.get('points',0)} pts | Level {pdata.get('level',0)} {yapping.get_badge(pdata.get('level',0))}\n"
    await cq.message.edit_text(text, reply_markup=make_keyboard("BBB", uid, page))

# ---------------- MENU OPEN ---------------- #
async def open_menu(client: Client, message: Message):
    uid = message.from_user.id
    # hapus pengecekan OPEN_MENU_STATE
    await message.reply(MENU_STRUCTURE["main"]["title"], reply_markup=make_keyboard("main", uid))

async def open_menu_pm(client: Client, message: Message):
    uid = message.from_user.id
    # hapus pengecekan OPEN_MENU_STATE
    await message.reply("📋 Menu Utama:", reply_markup=make_keyboard("main", uid))

def get_today_int() -> int:
    """Return integer for today (YYYYMMDD)"""
    return int(date.today().strftime("%Y%m%d"))

def init_user_login(user_id: int):
    if user_id not in LOGIN_STATE:
        LOGIN_STATE[user_id] = {
            "last_login_day": 0,
            "streak": 0,
            "umpan_given": set()
        }

###############
def register(app: Client):
    """
    Registrasi semua handler utama dari menu_utama.
    Pastikan semua fungsi sudah dideklarasikan sebelum fungsi ini dipanggil.
    """

    # ====================================================
    # 🧭 MENU & PERINTAH UTAMA
    # ====================================================
    # Handler untuk membuka menu utama lewat .menufish (debug) atau /menu
    app.add_handler(MessageHandler(open_menu, filters.regex(r"^\.menufish$") & filters.private))
    app.add_handler(MessageHandler(open_menu_pm, filters.command("menu") & filters.private))

    # ====================================================
    # 💰 TRANSFER & INPUT COIN
    # ====================================================
    # Menangani format transfer item / koin antara user
    app.add_handler(MessageHandler(handle_transfer_message, filters.text & filters.private))

def register_sedekah_handlers(app: Client):
    """
    Registrasi handler khusus sedekah.
    Fungsi ini memungkinkan bot menerima input angka (jumlah & slot)
    saat pengguna mengetik di chat private.
    """
    app.add_handler(MessageHandler(handle_sedekah_input, filters.private & filters.text))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("[DEBUG] register_sedekah_handlers() aktif ✅")












