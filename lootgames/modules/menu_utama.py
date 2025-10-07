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
    "SELL_MONKEY": {"name": "🐒 Monkey", "price": 15, "inv_key": "Monkey"},
    "SELL_GORILLA": {"name": "🦍 Gorilla", "price": 15, "inv_key": "GORILLA"},
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
    "SELL_DARKFISHWARRIOR": {"name": "👹 Dark Fish Warrior", "price": 2000, "inv_key": "Dark Fish Warrior"},
    "SELL_SNAILDRAGON": {"name": "🐉 Snail Dragon", "price": 4000, "inv_key": "Snail Dragon"},
    "SELL_QUEENOFHERMIT": {"name": "👑 Queen Of Hermit", "price": 4000, "inv_key": "Queen Of Hermit"},
    "SELL_MECHAFROG": {"name": "🤖 Mecha Frog", "price": 4000, "inv_key": "Mecha Frog"},
    "SELL_QUEENOFMEDUSA": {"name": "👑 Queen Of Medusa 🐍", "price": 4000, "inv_key": "Queen Of Medusa"},
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
    "🐒 Monkey": "🐒 Monkey",
    "monkey": "Monkey",
    "🦍 Gorilla": "🦍 Gorilla",
    "gorilla": "Gorilla",
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
            ("🐉🔥 Charmander", "SELL_DETAIL:SELL_CHARMANDER"),
            ("🐋⚡ Kyogre", "SELL_DETAIL:SELL_KYOGRE"),
            ("🐊 Crocodile", "SELL_DETAIL:SELL_CROCODILE"),
            ("🦦 Seal", "SELL_DETAIL:SELL_SEAL"),
            ("🐢 Turtle", "SELL_DETAIL:SELL_TURTLE"),
            ("🦞 Lobster", "SELL_DETAIL:SELL_LOBSTER"),
            ("📿 Lucky Jewel", "SELL_DETAIL:SELL_LUCKYJEWEL"),
            ("🐋 Orca", "SELL_DETAIL:SELL_ORCA"),
            ("🐒 Monkey", "SELL_DETAIL:SELL_MONKEY"),
            ("🦍 Gorilla", "SELL_DETAIL:SELL_GORILLA"),
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
            ("👹 Dark Lord Demon", "SELL_DETAIL:SELL_DARKLORDDEMON"),
            ("🦊 Princess of Nine Tail", "SELL_DETAIL:SELL_PRINCESSOFNINETAIL"),
            ("👹 Dark Fish Warrior", "SELL_DETAIL:SELL_DARKFISHWARRIOR"),
            ("🐉 Snail Dragon", "SELL_DETAIL:SELL_SNAILDRAGON"),
            ("👑 Queen Of Hermit", "SELL_DETAIL:SELL_QUEENOFHERMIT"),
            ("🤖 Mecha Frog", "SELL_DETAIL:SELL_MECHAFROG"),
            ("👑 Queen Medusa 🐍", "SELL_DETAIL:SELL_QUEENOFMEDUSA"),
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
    "D3A": {
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
    "title": "📦 TREASURE CHEST (OWNER ONLY)",
    "buttons": [
        ("KIRIM KE GROUP SEKARANG?", "TREASURE_SEND_NOW"),
        ("⬅️ Back", "main")
    ]
}
# ===== SUBMENU EVOLVE =====
MENU_STRUCTURE["I"] = {
    "title": "🧬 [EVOLVE]",
    "buttons": [
        ("𓆝 Small Fish", "I_SMALLFISH"),
        ("🐌 Snail", "I_SNAIL"),
        ("🐚 Hermit Crab", "I_HERMITCRAB"),
        ("🐸 Frog", "I_FROG"),
        ("🐍 Snake", "I_SNAKE"),
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

# di bagian global module (atas file)
# 🔹 DROP TABLE
def get_treasure_drop():
    """
    Menentukan drop item dan tipe umpan.
    Return: (item_name, jenis_umpan, jumlah)
    """
    drop_table = [
        ("ZONK", None, 0, 40),                  # 40% zonk
        ("Umpan Common", "A", 2, 39),           # 39% common
        ("Umpan Rare", "B", 1, 10),             # 10% rare
        ("Umpan Legend", "C", 0, 0.00000000001),# 1e-11% legend
        ("Umpan Mythic", "D", 0, 0.00000000001),# 1e-11% mythic
    ]

    total = sum(i[3] for i in drop_table)
    roll = random.uniform(0, total)
    current = 0

    for item, jenis, jumlah, chance in drop_table:
        current += chance
        if roll <= current:
            return item, jenis, jumlah
    return "ZONK", None, 0

# ---------------- CALLBACK HANDLER ---------------- #
async def callback_handler(client: Client, cq: CallbackQuery):
    data = cq.data
    user_id = cq.from_user.id
    # <-- Pastikan uname didefinisikan di sini
    uname = cq.from_user.username or f"user{user_id}"
    
    # ===== EVOLVE SMALL FISH CONFIRM =====
    if data == "EVOLVE_SMALLFISH_CONFIRM":
        inv = aquarium.get_user_fish(user_id)
        small_fish_qty = inv.get("𓆝 Small Fish", 0)

        if small_fish_qty < 1000:
            await cq.answer("❌ Small Fish kamu kurang (butuh 1000)", show_alert=True)
            return

        # ✅ Kurangi stok Small Fish
        inv["𓆝 Small Fish"] = small_fish_qty - 1000
        if inv["𓆝 Small Fish"] <= 0:
            inv.pop("𓆝 Small Fish")

        # ✅ Tambahkan Dark Fish Warrior
        inv["👹 Dark Fish Warrior"] = inv.get("👹 Dark Fish Warrior", 0) + 1

        # ✅ Simpan kembali
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)

        uname = cq.from_user.username or f"user{user_id}"

        # ✅ Balasan private ke user
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"✅ Evolve berhasil!\n"
            f"𓆝 Small Fish -1000\n"
            f"🧬 Dark Fish Warrior +1\n\n"
            f"📦 Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )

        # ✅ Info ke group
        # ✅ Info ke group + pin pesan
        try:
            msg = await client.send_message(
                TARGET_GROUP,
                f"🧬 @{uname} berhasil evolve!\n"
                f"🧬 Small Fish → 👹 Dark Fish Warrior 🎉"
            )
            # ✅ Pin pesan ini tanpa menghapus pin lama
            await client.pin_chat_message(TARGET_GROUP, msg.id, disable_notification=True)
        except Exception as e:
            logger.error(f"Gagal kirim atau pin info evolve ke group: {e}")

    # ===== EVOLVE HERMIT CRAB CONFIRM =====
    if data == "EVOLVE_SNAIL_CONFIRM":
        inv = aquarium.get_user_fish(user_id)
        snail_qty = inv.get("🐌 Snail", 0)

        if snail_qty < 1000:
            await cq.answer("❌ Hermit Crab kamu kurang (butuh 1000)", show_alert=True)
            return

        # ✅ Kurangi stok Hermit Crab
        inv["🐌 Snail"] = snail_qty - 1000
        if inv["🐌 Snail"] <= 0:
            inv.pop("🐌 Snail")

        # ✅ Tambahkan 🐉 Snail Dragon
        inv["🐉 Snail Dragon"] = inv.get("🐉 Snail Dragon", 0) + 1

        # ✅ Simpan kembali
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)

        # ✅ Balasan private ke user
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"✅ Evolve berhasil!\n"
            f"🐌 Snail -1000\n"
            f"🧬 🐉 Snail Dragon +1\n\n"
            f"📦 Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )

        # ✅ Info ke group
        try:
            msg = await client.send_message(
                TARGET_GROUP,
                f"🧬 @{uname} berhasil evolve!\n"
                f"🧬 Snail → 🐉 Snail Dragon 🎉"
            )
            await client.pin_chat_message(TARGET_GROUP, msg.id, disable_notification=True)
        except Exception as e:
            logger.error(f"Gagal kirim atau pin info evolve ke group: {e}")
    
    # ===== EVOLVE HERMIT CRAB CONFIRM =====
    if data == "EVOLVE_HERMITCRAB_CONFIRM":
        inv = aquarium.get_user_fish(user_id)
        hermit_crab_qty = inv.get("🐚 Hermit Crab", 0)

        if hermit_crab_qty < 1000:
            await cq.answer("❌ Hermit Crab kamu kurang (butuh 1000)", show_alert=True)
            return

        # ✅ Kurangi stok Hermit Crab
        inv["🐚 Hermit Crab"] = hermit_crab_qty - 1000
        if inv["🐚 Hermit Crab"] <= 0:
            inv.pop("🐚 Hermit Crab")

        # ✅ Tambahkan 👑 Queen of Hermit
        inv["👑 Queen of Hermit"] = inv.get("👑 Queen of Hermit", 0) + 1

        # ✅ Simpan kembali
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)

        # ✅ Balasan private ke user
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"✅ Evolve berhasil!\n"
            f"🐚 Hermit Crab -1000\n"
            f"🧬 👑 Queen of Hermit +1\n\n"
            f"📦 Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )

        # ✅ Info ke group
        try:
            msg = await client.send_message(
                TARGET_GROUP,
                f"🧬 @{uname} berhasil evolve!\n"
                f"🧬 Hermit Crab → 👑 Queen of Hermit 🎉"
            )
            await client.pin_chat_message(TARGET_GROUP, msg.id, disable_notification=True)
        except Exception as e:
            logger.error(f"Gagal kirim atau pin info evolve ke group: {e}")

        # ===== EVOLVE FROG CONFIRM =====
    if data == "EVOLVE_FROG_CONFIRM":
        inv = aquarium.get_user_fish(user_id)
        frog_qty = inv.get("🐸 Frog", 0)

        if frog_qty < 1000:
            await cq.answer("❌ Frog kamu kurang (butuh 1000)", show_alert=True)
            return

        # ✅ Kurangi stok Frog
        inv["🐸 Frog"] = frog_qty - 1000
        if inv["🐸 Frog"] <= 0:
            inv.pop("🐸 Frog")

        # ✅ Tambahkan 🤖 Mecha Frog
        inv["🤖 Mecha Frog"] = inv.get("🤖 Mecha Frog", 0) + 1

        # ✅ Simpan ke database
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)

        uname = cq.from_user.username or f"user{user_id}"

        # ✅ Balasan ke user
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"✅ Evolve berhasil!\n"
            f"🐸 Frog -1000\n"
            f"🧬 🤖 Mecha Frog +1\n\n"
            f"📦 Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )

        # ✅ Info ke group + pin pesan
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

        if snake_qty < 1000:
            await cq.answer("❌ Snake kamu kurang (butuh 1000)", show_alert=True)
            return

        # ✅ Kurangi stok Snake
        inv["🐍 Snake"] = snake_qty - 1000
        if inv["🐍 Snake"] <= 0:
            inv.pop("🐍 Snake")

        # ✅ Tambahkan 👑 Queen Of Medusa 🐍
        inv["👑 Queen Of Medusa 🐍"] = inv.get("👑 Queen Of Medusa 🐍", 0) + 1

        # ✅ Simpan ke database
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)

        uname = cq.from_user.username or f"user{user_id}"

        # ✅ Balasan ke user
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"✅ Evolve berhasil!\n"
            f"🐍 Snake -1000\n"
            f"🧬 👑 Queen Of Medusa 🐍 +1\n\n"
            f"📦 Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )

        # ✅ Info ke group + pin pesan
        try:
            msg = await client.send_message(
                TARGET_GROUP,
                f"🧬 @{uname} berhasil evolve!\n"
                f"Snake → 👑 Queen Of Medusa 🐍 🎉"
            )
            await client.pin_chat_message(TARGET_GROUP, msg.id, disable_notification=True)
        except Exception as e:
            logger.error(f"Gagal kirim atau pin info evolve ke group: {e}")

    # di dalam async def callback_handler(client: Client, cq: CallbackQuery):
    # ================== PLAYER CLAIM CHEST ==================
    if data == "treasure_chest":
        # pastikan ada lock per user
        async with USER_CLAIM_LOCKS_LOCK:
            lock = USER_CLAIM_LOCKS.get(user_id)
            if lock is None:
                lock = asyncio.Lock()
                USER_CLAIM_LOCKS[user_id] = lock

        async with lock:
            if user_id in CLAIMED_CHEST_USERS:
                await cq.answer("❌ Kamu sudah mengklaim Treasure Chest ini sebelumnya!", show_alert=True)
                return

            await asyncio.sleep(3)  # efek dramatis

            # 🎲 Tentukan drop
            item, jenis, jumlah = get_treasure_drop()

            if item == "ZONK":
                msg = f"😢 @{uname} mendapatkan ZONK!"
            else:
                msg = f"🎉 @{uname} mendapatkan {jumlah} pcs 🐛{item}!"
                try:
                    umpan.add_umpan(user_id, jenis, jumlah)
                except Exception as e:
                    logger.error(f"Gagal tambah umpan ke user {user_id}: {e}")

            # tandai user sudah claim
            CLAIMED_CHEST_USERS.add(user_id)

            await cq.message.reply(msg)
            return

    # ================== TREASURE CHEST OWNER ==================
    if data == "TREASURE_SEND_NOW":
        global LAST_TREASURE_MSG_ID

        if user_id != OWNER_ID:
            await cq.answer("❌ Hanya owner yang bisa akses menu ini.", show_alert=True)
            return

        # 🔹 Reset claim
        CLAIMED_CHEST_USERS.clear()

        # 🔹 Hapus pesan chest lama
        if LAST_TREASURE_MSG_ID is not None:
            try:
                await cq._client.delete_messages(TARGET_GROUP, LAST_TREASURE_MSG_ID)
            except Exception as e:
                logger.warning(f"Gagal hapus Treasure Chest lama: {e}")

        # 🔹 Kirim Treasure Chest baru
        try:
            msg = await cq._client.send_message(
                TARGET_GROUP,
                "📦 **Treasure Chest telah dikirim oleh OWNER!**\n"
                "Cepat klaim sebelum terlambat! 🎁",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔑 Buka Treasure Chest", callback_data="treasure_chest")]]
                )
            )
            LAST_TREASURE_MSG_ID = msg.id
        except Exception as e:
            logger.error(f"Gagal kirim Treasure Chest: {e}")

        await cq.message.edit_text(
            "✅ Treasure Chest berhasil dikirim ke group!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Kembali", callback_data="H")]]
            )
        )
        return

    # ===== LOGIN HARIAN CALLBACK =====
    if data == "LOGIN_TODAY":
        init_user_login(user_id)
        today = get_today_int()
        user_login = LOGIN_STATE[user_id]
        if user_login["last_login_day"] == today:
            await cq.answer("❌ Kamu sudah absen hari ini!", show_alert=True)
            return

        # update streak dan hari terakhir
        user_login["streak"] += 1
        user_login["last_login_day"] = today

        # berikan 1 Umpan COMMON A jika belum pernah diterima
        reward = STREAK_REWARDS.get(user_login["streak"], 10)  # max 10 umpan
        reward_key = f"COMMON_{user_login['streak']}"  # track per streak
        if reward_key not in user_login["umpan_given"]:
            umpan.add_umpan(user_id, "A", reward)
            user_login["umpan_given"].add(reward_key)
            msg = f"🎉 Absen berhasil! Kamu mendapatkan {reward} Umpan COMMON 🐛. Streak: {user_login['streak']} hari."
        else:
            msg = f"✅ Absen berhasil! Tapi umpan sudah diterima sebelumnya. Streak: {user_login['streak']} hari."

        await cq.message.edit_text(msg, reply_markup=make_keyboard("G", user_id))
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
            f"Contoh: `50` untuk menukar 50 coin jadi 2 umpan.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Batal", callback_data="D2C_MENU")]])
        )
        return
    
    # FISHING
    # ----------------- FUNGSI MEMANCING -----------------
    async def fishing_task(client, uname, user_id, jenis, task_id):
        try:
            await asyncio.sleep(2)
            # Pesan di grup sekarang termasuk task_id
            await client.send_message(TARGET_GROUP, f"```\n🎣 @{uname} trying to catch... task#{task_id}```\n")

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
            msg_group = f"🎣 @{uname} got {loot_result}! from task#{task_id}"
            msg_private = f"🎣 You got {loot_result}! from ask#{task_id}"
            await client.send_message(TARGET_GROUP, msg_group)
            await client.send_message(user_id, msg_private)

        except Exception as e:
            logger.error(f"Gagal fishing_task: {e}")
        
    # ----------------- CALLBACK HANDLER -----------------
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

        await cq.message.edit_text(
            f"🎣 You successfully threw the bait! {jenis} to loot task#{task_id}!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎣 Catch again", callback_data=f"FISH_CONFIRM_{jenis}")],
                [InlineKeyboardButton("🤖 Auto Catch 5x", callback_data=f"AUTO_FISH_{jenis}")],
                [InlineKeyboardButton("⬅️ Back", callback_data="E")]
            ])
        )

        # Jalankan task memancing
        asyncio.create_task(fishing_task(client, uname, user_id, jenis, task_id))


    # ----------------- AUTO MEMANCING 5x -----------------
    elif data.startswith("AUTO_FISH_"):
        jenis = data.replace("AUTO_FISH_", "")
        uname = cq.from_user.username or f"user{user_id}"

        now = asyncio.get_event_loop().time()
        last_time = user_last_fishing[user_id]

        if now - last_time < 10:
            await cq.answer("⏳ Wait cooldown 10 sec before auto catching!", show_alert=True)
            return

        await cq.answer("🤖 Auto Catching 5x Start!")

        async def auto_fishing():
            for i in range(5):
                now = asyncio.get_event_loop().time()
                if now - user_last_fishing[user_id] < 10:
                    break  # stop kalau masih cooldown

                # cek stok umpan dulu (tanpa mengurangi)
                jk_map = {"COMMON": "A", "RARE": "B", "LEGEND": "C", "MYTHIC": "D"}
                jk = jk_map.get(jenis, "A")
                if user_id != OWNER_ID:
                    ud = umpan.get_user(user_id)
                    if not ud or ud.get(jk, {}).get("umpan", 0) <= 0:
                        await cq.message.reply("❌ Umpan habis! Auto Catching stop.")
                        break

                user_last_fishing[user_id] = now
                user_task_count[user_id] += 1
                task_id = f"{user_task_count[user_id]:02d}"

                # Info auto-fishing
                await cq.message.reply(
                    f"🎣 Auto Catching {i+1}/5: You successfully threw the bait {jenis} to loot task#{task_id}!"
                )

                # Jalankan task memancing (umpan dikurangi saat hasil drop)
                asyncio.create_task(fishing_task(client, uname, user_id, jenis, task_id))

                await asyncio.sleep(10)  # jeda tiap lemparan

        asyncio.create_task(auto_fishing())

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
    if data == "D2A":
        inv_text = aquarium.list_inventory(user_id)
        kb = make_keyboard("D2A", user_id)
        await cq.message.edit_text(f"📦 Inventorymu:\n\n{inv_text}", reply_markup=kb)
        return

    # CEK INVENTORY (hasil tangkapan)
    if data == "FFF":
        inv_text = aquarium.list_inventory(user_id)
        kb = make_keyboard("FFF", user_id)
        await cq.message.edit_text(f"🎣 Inventorymu:\n\n{inv_text}", reply_markup=kb)
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

    # TRANSFER (existing)
    # TRANSFER (revisi dengan delay & info ke group)
    if TRANSFER_STATE.get(uid):
        try:
            jenis = TRANSFER_STATE[uid]["jenis"]
            parts = message.text.strip().split()
            if len(parts) != 2:
                return await message.reply("Format salah. Contoh: @username 1")
            rname, amt = parts
            if not rname.startswith("@"):
                return await message.reply("Username harus diawali '@'.")
            amt = int(amt)
            if amt <= 0:
                return await message.reply("Jumlah harus > 0.")
            rid = user_database.get_user_id_by_username(rname)
            if rid is None:
                await message.reply(f"❌ Username {rname} tidak ada di database!")
                TRANSFER_STATE.pop(uid, None)
                return

            # ====== PROSES TRANSFER ====== #
            # ====== PROSES TRANSFER ====== #
            # 🔒 Batasi transfer umpan Rare hanya untuk OWNER
            if jenis == "B" and uid != OWNER_ID:
                await message.reply("❌ Hanya OWNER yang bisa transfer Umpan Rare 🐌.")
                TRANSFER_STATE.pop(uid, None)
                return

            if uid == OWNER_ID:
                umpan.add_umpan(rid, jenis, amt)
            else:
                sd = umpan.get_user(uid)
                if sd[jenis]["umpan"] < amt:
                    return await message.reply("❌ Umpan tidak cukup!")
                umpan.remove_umpan(uid, jenis, amt)
                umpan.add_umpan(rid, jenis, amt)

            # Info ke OWNER (langsung)
            await message.reply(
                f"✅ Transfer {amt} umpan ke {rname} berhasil!",
                reply_markup=make_keyboard("main", uid)
            )

            # Info ke penerima (delay 0.5 detik)
            try:
                await asyncio.sleep(0.5)
                await client.send_message(
                    rid,
                    f"🎁 Kamu mendapat {amt} umpan dari @{uname}"
                )
            except Exception as e:
                logger.error(f"Gagal notif penerima {rid}: {e}")

            # Info ke GROUP (delay 2 detik)
            try:
                await asyncio.sleep(2)
                await client.send_message(
                    TARGET_GROUP,
                    f"```\n📢 Transfer Umpan!\n👤 @{uname} memberi {amt} umpan ke {rname}```\n"
                )
            except Exception as e:
                logger.error(f"Gagal notif group: {e}")

        except Exception as e:
            await message.reply(f"❌ Error: {e}")

        TRANSFER_STATE.pop(uid, None)
        return

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
    # ================= TUKAR COIN KE UMPAN ================= #
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
                min_coin, konversi, nama, emoji = 25, 25, "RARE (Type B)", "🪱"
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

# ---------------- REGISTER HANDLERS ---------------- #
def register(app: Client):
    # register handlers already expected by your app:
    app.add_handler(MessageHandler(open_menu, filters.regex(r"^\.menufish$") & filters.private))
    app.add_handler(MessageHandler(open_menu_pm, filters.command("menu") & filters.private))
    # this handler will also handle SELL amount input because SELL_WAITING is checked inside
    app.add_handler(MessageHandler(handle_transfer_message, filters.text & filters.private))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(handle_transfer_message, filters.text & filters.private))

    logger.info("[MENU] Handler menu_utama terdaftar.")
