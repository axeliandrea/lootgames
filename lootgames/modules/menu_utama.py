# lootgames/modules/menu_utama.py Test Nonaktif Umpan Rare
import os
import logging
import asyncio
import re
import random
import json
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.modules import yapping, umpan, user_database
from lootgames.modules import fizz_coin
from lootgames.modules import aquarium
from lootgames.modules.gacha_fishing import fishing_loot
from datetime import date

logger = logging.getLogger(__name__)
OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772  # ganti sesuai supergroup bot

# ---------------- STATE ---------------- #
TRANSFER_STATE = {}       # user_id: {"jenis": "A/B/C/D"}
TUKAR_POINT_STATE = {}    # user_id: {"step": step, "jumlah_umpan": n}
OPEN_MENU_STATE = {}      # user_id: True jika menu aktif
LOGIN_STATE = {}  # user_id: {"last_login_day": int, "streak": int, "umpan_given": set()}
STREAK_REWARDS = {1: 0, 2: 5, 3: 6, 4: 7, 5: 8, 6: 9, 7: 10}
CHEST_DB = "storage/treasure_chest.json"  # Simpan info chest aktif dan siapa yang sudah claim
CLAIMED_CHEST_USERS = set()  # user_id yang sudah claim treasure chest saat ini
LAST_TREASURE_MSG_ID = None
USER_CLAIM_LOCKS = {}               # map user_id -> asyncio.Lock()
USER_CLAIM_LOCKS_LOCK = asyncio.Lock()  # lock untuk pembuatan lock per-user
TUKAR_COIN_STATE = {}  # user_id: {"jenis": "A" atau "B"}
# ---------------- PATH DB ---------------- #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # folder modules
DB_FILE = os.path.join(BASE_DIR, "../storage/fizz_coin.json")  # ke folder storage
# pastikan folder storage ada
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

# ----------------- INISIALISASI -----------------
user_last_fishing = defaultdict(lambda: 0)  # cooldown 10 detik per user
user_task_count = defaultdict(lambda: 0)   # generate task ID unik per user

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

# =================== UTIL ===================
def load_chest_data():
    try:
        with open(CHEST_DB, "r") as f:
            return json.load(f)
    except:
        return {}

def save_chest_data(data):
    with open(CHEST_DB, "w") as f:
        json.dump(data, f)

def get_random_item():
    # 90% ZONK, 10% Umpan
    return random.choices(
        ["ZONK", "Umpan Common Type A"],
        weights=[65, 35],
        k=1
    )[0]

# ---------------- SELL / ITEM CONFIG ---------------- #
# inv_key harus cocok dengan key di aquarium_data.json (nama item di DB)
ITEM_PRICES = {
    "SELL_SMALLFISH": {"name": "𓆝 Small Fish", "price": 1, "inv_key": "Small Fish"},
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
    "SELL_REDHAMMERCAT": {"name": "🐱 Red Hammer Cat", "price": 8, "inv_key": "Seahorse"},
    "SELL_PURPLEFISTCAT": {"name": "🐱 Purple Fist Cat", "price": 8, "inv_key": "Seahorse"},
    "SELL_GREENDINOCAT": {"name": "🐱 Green Dino Cat", "price": 8, "inv_key": "Seahorse"},
    "SELL_WHITEWINTERCAT": {"name": "🐱 White Winter Cat", "price": 8, "inv_key": "Seahorse"},
    "SELL_SHARK": {"name": "🐟 Shark", "price": 10, "inv_key": "Shark"},
    "SELL_SEAHORSE": {"name": "🐟 Seahorse", "price": 10, "inv_key": "Seahorse"},
    "SELL_CROCODILE": {"name": "🐊 Crocodile", "price": 10, "inv_key": "Crocodile"},
    "SELL_SEAL": {"name": "🦦 Seal", "price": 10, "inv_key": "Seal"},
    "SELL_TURTLE": {"name": "🐢 Turtle", "price": 10, "inv_key": "Turtle"},
    "SELL_LOBSTER": {"name": "🦞 Lobster", "price": 10, "inv_key": "Lobster"},
    "SELL_LUCKYJEWEL": {"name": "📿 Lucky Jewel", "price": 7, "inv_key": "Lucky Jewel"},
    "SELL_ORCA": {"name": "🐋 Orca", "price": 15, "inv_key": "Orca"},
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
    "SELL_DARKLORDDEMON": {"name": "👹 Dark Lord Demon", "price": 500, "inv_key": "Dark Lord Demon"},
    "SELL_PRINCESSOFNINETAIL": {"name": "🦊 Princess of Nine Tail", "price": 500, "inv_key": "Princess of Nine Tail"},
    "SELL_DARKFISHWARRIOR": {"name": "👹 Dark Fish Warrior", "price": 1500, "inv_key": "Dark Fish Warrior"},
    "SELL_SNAILDRAGON": {"name": "🐉 Snail Dragon", "price": 2700, "inv_key": "Snail Dragon"},
    "SELL_QUEENOFHERMIT": {"name": "👑 Queen Of Hermit", "price": 2700, "inv_key": "Queen Of Hermit"},
    "SELL_MECHAFROG": {"name": "🤖 Mecha Frog", "price": 2700, "inv_key": "Mecha Frog"},
    "SELL_QUEENOFMEDUSA": {"name": "👑 Queen Of Medusa 🐍", "price": 2700, "inv_key": "Queen Of Medusa"},
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
    "ଳ Jelly Fish": "Jelly Fish",
    "jelly fish": "Jelly Fish",
    "🐋 Orca": "Orca",
    "orca": "Orca",
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
    "🐺 Werewolf": "🐺 Werewolf",
    "werewolf": "Werewolf",
    "🐱 Rainbow Angel Cat": "🐱 Rainbow Angel Cat",
    "rainbow angel cat": "Rainbow Angel Cat",
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
    "🐢 Turtle": "🐢 Turtle",
    "turtle": "Turtle",
    "🦞 Lobster": "🦞 Lobster",
    "lobster": "Lobster",
    "🧜‍♀️ Mermaid Boy": "Mermaid Boy",
    "mermaid boy": "Mermaid Boy",
    "🧜‍♀️ Mermaid Girl": "Mermaid Girl",
    "mermaid girl": "Mermaid Girl"
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
            ("🧬 EVOLVE", "I")
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
            ("TOPUP QRIS (cooming soon)", "D1A"),
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
            ("🐟 Shark", "SELL_DETAIL:SELL_SHARK"),
            ("🐟 Seahorse", "SELL_DETAIL:SELL_SEAHORSE"),
            ("🐹⚡ Pikachu", "SELL_DETAIL:SELL_PIKACHU"),
            ("🐸🍀 Bulbasaur", "SELL_DETAIL:SELL_BULBASAUR"),
            ("🐢💧 Squirtle", "SELL_DETAIL:SELL_SQUIRTLE"),
            ("🐉🔥 Charmander", "SELL_DETAIL:SELL_CHARMAN
