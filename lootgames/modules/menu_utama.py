#FIX 05:52
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
    "SELL_SMALLFISH": {"name": "ð“† Small Fish", "price": 1, "inv_key": "Small Fish"},
    "SELL_SNAIL": {"name": "ðŸŒ Snail", "price": 2, "inv_key": "Snail"},
    "SELL_HERMITCRAB": {"name": "ðŸš Hermit Crab", "price": 2, "inv_key": "Hermit Crab"},
    "SELL_CRAB": {"name": "ðŸ¦€ Crab", "price": 2, "inv_key": "Crab"},
    "SELL_FROG": {"name": "ðŸ¸ Frog", "price": 2, "inv_key": "Frog"},
    "SELL_SNAKE": {"name": "ðŸ Snake", "price": 2, "inv_key": "Snake"},
    "SELL_OCTOPUS": {"name": "ðŸ™ Octopus", "price": 3, "inv_key": "Octopus"},
    "SELL_JELLYFISH": {"name": "à¬³ Jelly Fish", "price": 4, "inv_key": "Jelly Fish"},
    "SELL_GIANTCLAM": {"name": "ðŸ¦ª Giant Clam", "price": 4, "inv_key": "Giant Clam"},
    "SELL_GOLDFISH": {"name": "ðŸŸ Goldfish", "price": 4, "inv_key": "Goldfish"},
    "SELL_STINGRAYSFISH": {"name": "ðŸŸ Stingrays Fish", "price": 4, "inv_key": "Stingrays Fish"},
    "SELL_CLOWNFISH": {"name": "ðŸŸ Clownfish", "price": 4, "inv_key": "Clownfish"},
    "SELL_DORYFISH": {"name": "ðŸŸ Doryfish", "price": 4, "inv_key": "Doryfish"},
    "SELL_BANNERFISH": {"name": "ðŸŸ Bannerfish", "price": 4, "inv_key": "Bannerfish"},
    "SELL_MOORISHIDOL": {"name": "ðŸŸ Moorish Idol", "price": 4, "inv_key": "Moorish Idol"},
    "SELL_AXOLOTL": {"name": "ðŸŸ Axolotl", "price": 4, "inv_key": "Axolotl"},
    "SELL_BETAFISH": {"name": "ðŸŸ Beta Fish", "price": 4, "inv_key": "Beta Fish"},
    "SELL_ANGLERFISH": {"name": "ðŸŸ Anglerfish", "price": 4, "inv_key": "Anglerfish"},
    "SELL_DUCK": {"name": "ðŸ¦† Duck", "price": 4, "inv_key": "Duck"},
    "SELL_CHICKEN": {"name": "ðŸ” Chicken", "price": 4, "inv_key": "Chicken"},
    "SELL_PUFFER": {"name": "ðŸ¡ Pufferfish", "price": 5, "inv_key": "Pufferfish"},
    "SELL_REDHAMMERCAT": {"name": "ðŸ± Red Hammer Cat", "price": 8, "inv_key": "Seahorse"},
    "SELL_PURPLEFISTCAT": {"name": "ðŸ± Purple Fist Cat", "price": 8, "inv_key": "Seahorse"},
    "SELL_GREENDINOCAT": {"name": "ðŸ± Green Dino Cat", "price": 8, "inv_key": "Seahorse"},
    "SELL_WHITEWINTERCAT": {"name": "ðŸ± White Winter Cat", "price": 8, "inv_key": "Seahorse"},
    "SELL_SHARK": {"name": "ðŸŸ Shark", "price": 10, "inv_key": "Shark"},
    "SELL_SEAHORSE": {"name": "ðŸŸ Seahorse", "price": 10, "inv_key": "Seahorse"},
    "SELL_CROCODILE": {"name": "ðŸŠ Crocodile", "price": 10, "inv_key": "Crocodile"},
    "SELL_SEAL": {"name": "ðŸ¦¦ Seal", "price": 10, "inv_key": "Seal"},
    "SELL_TURTLE": {"name": "ðŸ¢ Turtle", "price": 10, "inv_key": "Turtle"},
    "SELL_LOBSTER": {"name": "ðŸ¦ž Lobster", "price": 10, "inv_key": "Lobster"},
    "SELL_LUCKYJEWEL": {"name": "ðŸ“¿ Lucky Jewel", "price": 7, "inv_key": "Lucky Jewel"},
    "SELL_ORCA": {"name": "ðŸ‹ Orca", "price": 15, "inv_key": "Orca"},
    "SELL_MONKEY": {"name": "ðŸ’ Monkey", "price": 15, "inv_key": "Monkey"},
    "SELL_GORILLA": {"name": "ðŸ¦ Gorilla", "price": 15, "inv_key": "GORILLA"},
    "SELL_PANDA": {"name": "ðŸ¼ Panda", "price": 15, "inv_key": "PANDA"},
    "SELL_BEAR": {"name": "ðŸ» Bear", "price": 15, "inv_key": "BEAR"},
    "SELL_DOG": {"name": "ðŸ¶ Dog", "price": 15, "inv_key": "DOG"},
    "SELL_BAT": {"name": "ðŸ¦‡ bat", "price": 15, "inv_key": "BAT"},
    "SELL_DOLPHIN": {"name": "ðŸ¬ Dolphin", "price": 15, "inv_key": "Dolphin"},
    "SELL_PIKACHU": {"name": "ðŸ¹âš¡ Pikachu", "price": 30, "inv_key": "Pikachu"},
    "SELL_BULBASAUR": {"name": "ðŸ¸ðŸ€ Bulbasaur", "price": 30, "inv_key": "Bulbasaur"},
    "SELL_SQUIRTLE": {"name": "ðŸ¢ðŸ’§ Squirtle", "price": 30, "inv_key": "Squirtle"},
    "SELL_CHARMANDER": {"name": "ðŸ‰ðŸ”¥ Charmander", "price": 30, "inv_key": "Charmander"},
    "SELL_KYOGRE": {"name": "ðŸ‹âš¡ Kyogre", "price": 30, "inv_key": "Kyogre"},
    "SELL_BABYDRAGON": {"name": "ðŸ‰ Baby Dragon", "price": 100, "inv_key": "Baby Dragon"},
    "SELL_BABYSPIRITDRAGON": {"name": "ðŸ‰ Baby Spirit Dragon", "price": 100, "inv_key": "Baby Spirit Dragon"},
    "SELL_BABYMAGMADRAGON": {"name": "ðŸ‰ Baby Magma Dragon", "price": 100, "inv_key": "Baby Magma Dragon"},
    "SELL_SKULLDRAGON": {"name": "ðŸ‰ Skull Dragon", "price": 200, "inv_key": "Skull Dragon"},
    "SELL_BLUEDRAGON": {"name": "ðŸ‰ Blue Dragon", "price": 200, "inv_key": "Blue Dragon"},
    "SELL_YELLOWDRAGON": {"name": "ðŸ‰ Yellow Dragon", "price": 200, "inv_key": "Yellow Dragon"},
    "SELL_BLACKDRAGON": {"name": "ðŸ‰ Black Dragon", "price": 200, "inv_key": "Black Dragon"},
    "SELL_MERMAIDBOY": {"name": "ðŸ§œâ€â™€ï¸ Mermaid Boy", "price": 200, "inv_key": "Mermaid Boy"},
    "SELL_MERMAIDGIRL": {"name": "ðŸ§œâ€â™€ï¸ Mermaid Girl", "price": 200, "inv_key": "Mermaid Girl"},
    "SELL_CUPIDDRAGON": {"name": "ðŸ‰ Cupid Dragon", "price": 300, "inv_key": "Cupid Dragon"},
    "SELL_WEREWOLF": {"name": "ðŸº Werewolf", "price": 300, "inv_key": "Werewolf"},
    "SELL_RAINBOWANGELCAT": {"name": "ðŸ± Rainbow Angel Cat", "price": 300, "inv_key": "Rainbow Angel Cat"},
    "SELL_FIREPHOENIX": {"name": "ðŸ¦â€ðŸ”¥ Fire Phoenix", "price": 300, "inv_key": "Fire Phoenix"},
    "SELL_FROSTPHOENIX": {"name": "ðŸ¦â„ï¸ Frost Phoenix", "price": 300, "inv_key": "Frost Phoenix"},
    "SELL_DARKPHOENIX": {"name": "ðŸ¦ðŸŒŒ Dark Phoenix", "price": 300, "inv_key": "Dark Phoenix"},
    "SELL_CHIMERA": {"name": "ðŸ¦ðŸ Chimera", "price": 300, "inv_key": "Chimera"},
    "SELL_WHITETIGER": {"name": "ðŸ¯ White Tiger", "price": 300, "inv_key": "White Tiger"},
    "SELL_DARKLORDDEMON": {"name": "ðŸ‘¹ Dark Lord Demon", "price": 500, "inv_key": "Dark Lord Demon"},
    "SELL_PRINCESSOFNINETAIL": {"name": "ðŸ¦Š Princess of Nine Tail", "price": 500, "inv_key": "Princess of Nine Tail"},
    "SELL_DARKKNIGHTDRAGON": {"name": "ðŸ‰ Dark Knight Dragon", "price": 500, "inv_key": "Dark Knight Dragon"},
    "SELL_DARKFISHWARRIOR": {"name": "ðŸ‘¹ Dark Fish Warrior", "price": 2000, "inv_key": "Dark Fish Warrior"},
    "SELL_SNAILDRAGON": {"name": "ðŸ‰ Snail Dragon", "price": 4000, "inv_key": "Snail Dragon"},
    "SELL_QUEENOFHERMIT": {"name": "ðŸ‘‘ Queen Of Hermit", "price": 4000, "inv_key": "Queen Of Hermit"},
    "SELL_MECHAFROG": {"name": "ðŸ¤– Mecha Frog", "price": 4000, "inv_key": "Mecha Frog"},
    "SELL_QUEENOFMEDUSA": {"name": "ðŸ‘‘ Queen Of Medusa ðŸ", "price": 4000, "inv_key": "Queen Of Medusa"},
}
# sementara user -> item_code waiting for amount input (chat)
SELL_WAITING = {}  # user_id: item_code

# Optional aliases: jika DB berisi emoji atau variasi penulisan,
# kita bisa map nama yang sering muncul ke bentuk canonical.
INV_KEY_ALIASES = {
    "ðŸ¤§ Zonk": "Zonk",
    "zonk": "zonk",
    "ð“† Small Fish": "Small Fish",
    "small fish": "Small Fish",
    "ðŸŒ snail": "Snail",
    "snail": "Snail",
    "ðŸš Hermit Crab": "Hermit Crab",
    "hermit crab": "Hermit Crab",
    "ðŸ¸ Frog": "Frog",
    "frog": "Frog",
    "ðŸ Snake": "ðŸ Snake",
    "snake": "Snake",
    "ðŸ™ octopus": "Octopus",
    "octopus": "Octopus",
    "ðŸ¡ Pufferfish": "Pufferfish",
    "pufferfish": "Pufferfish",
    "à¬³ Jelly Fish": "Jelly Fish",
    "jelly fish": "Jelly Fish",
    "ðŸ‹ Orca": "Orca",
    "orca": "Orca",
    "ðŸ’ Monkey": "Monkey",
    "monkey": "Monkey",
    "ðŸ¦ Gorilla": "Gorilla",
    "gorilla": "Gorilla",
    "ðŸ¼ Panda": "Panda",
    "panda": "Panda",
    "ðŸ» Bear": "Bear",
    "bear": "Bear",
    "ðŸ¶ Dog": "Dog",
    "dog": "Dog",
    "ðŸ¦‡ Bat": "Bat",
    "bat": "Bat",
    "ðŸ¬ Dolphin": "Dolphin",
    "dolphin": "Dolphin",
    "ðŸ± Red Hammer Cat": "Red Hammer Cat",
    "red hammer cat": "Red Hammer Cat",
    "ðŸ± Purple Fist Cat": "ðŸ± Purple Fist Cat",
    "purple fist cat": "Purple Fist Cat",
    "ðŸ± Green Dino Cat": "ðŸ± Green Dino Cat",
    "green dino cat": "Green Dino Cat",
    "ðŸ± White Winter Cat": "ðŸ± White Winter Cat",
    "white winter cat": "White Winter Cat",
    "ðŸ‰ Baby Dragon": "Baby Dragon",
    "baby dragon": "Baby Dragon",
    "ðŸ‰ Baby Spirit Dragon": "ðŸ‰ Baby Spirit Dragon",
    "baby spirit dragon": "Baby Spirit Dragon",
    "ðŸ‰ Baby Magma Dragon": "Baby Magma Dragon",
    "baby magma dragon": "Baby Magma Dragon",
    "ðŸ“¿ Lucky Jewel": "Lucky Jewel",
    "lucky jewel": "Lucky Jewel",
    "ðŸ‰ Skull Dragon": "Skull Dragon",
    "skull dragon": "Skull Dragon",
    "ðŸ‰ Blue Dragon": "Blue Dragon",
    "black dragon": "Black Dragon",
    "ðŸ‰ Yellow Dragon": "Yellow Dragon",
    "yellow dragon": "Yellow Dragon",
    "ðŸ‰ Black Dragon": "Black Dragon",
    "blue dragon": "Blue Dragon",
    "ðŸ‰ Cupid Dragon": "Cupid Dragon",
    "cupid dragon": "Cupid Dragon",
    "ðŸ‰ Dark Knight Dragon": "ðŸ‰ Dark Knight Dragon",
    "dark knight dragon": "Dark Knight Dragon",
    "ðŸ¯ White Tiger": "White Tiger",
    "white tiger": "White Tiger",
    "ðŸº Werewolf": "ðŸº Werewolf",
    "werewolf": "Werewolf",
    "ðŸ± Rainbow Angel Cat": "ðŸ± Rainbow Angel Cat",
    "rainbow angel cat": "Rainbow Angel Cat",
    "ðŸ¦â€ðŸ”¥ Fire Phoenix": "ðŸ¦â€ðŸ”¥ Fire Phoenix",
    "fire phoenix": "Fire Phoenix",
    "ðŸ¦â„ï¸ Frost Phoenix": "ðŸ¦â„ï¸ Frost Phoenix",
    "frost phoenix": "Frost Phoenix",
    "ðŸ¦ðŸŒŒ Dark Phoenix": "ðŸ¦ðŸŒŒ Dark Phoenix",
    "ðŸ¦ðŸ Chimera": "Chimera",
    "chimera": "Chimera",
    "dark phoenix": "Dark Phoenix",
    "ðŸ‘¹ Dark Lord Demon": "ðŸ‘¹ Dark Lord Demon",
    "dark lord demon": "Dark Lord Demon",
    "ðŸ¦Š Princess of Nine Tail": "ðŸ¦Š Princess of Nine Tail",
    "princess of nine tail": "Princess of Nine Tail",
    "ðŸ‘¹ Dark Fish Warrior": "Dark Fish Warrior",
    "dark fish warrior": "Dark Fish Warrior",
    "ðŸ‘‘ Queen Of Hermit": "Queen Of Hermit",
    "queen of hermit": "Queen Of Hermit",
    "ðŸ‰ Snail Dragon": "Snail Dragon",
    "snail dragon": "Snail Dragon",
    "ðŸ¤– Mecha Frog": "Mecha Frog",
    "ðŸ¤– Mecha Frog": "Mecha Frog",
    "ðŸ‘‘ Queen Of Medusa ðŸ": "Queen Of Medusa",
    "queen of medusa": "Queen Of Medusa",
    "ðŸ¸ Frog": "Frog",
    "Frog": "Frog",
    "ðŸŸ Goldfish": "Goldfish",
    "goldfish": "Goldfish",
    "ðŸŸ Stingrays Fish": "ðŸŸ Stingrays Fish",
    "stingrays fish": "Stingrays Fish",
    "ðŸŸ Clownfish": "Clownfish",
    "clownfish": "Clownfish",
    "ðŸŸ Doryfish":"Doryfish",
    "doryfish": "Doryfish",
    "ðŸŸ Bannerfish": "Bannerfish",
    "bannerfish": "Bannerfish",
    "ðŸŸ Beta Fish":"Beta Fish",
    "beta fish":"Beta Fish",
    "ðŸŸ Moorish Idol": "Moorish Idol",
    "moorish idol": "Moorish Idol",
    "ðŸŸ Axolotl": "Axolotl",
    "axolotl": "Axolotl",
    "ðŸŸ Anglerfish": "Anglerfish",
    "anglerfish": "Anglerfish",
    "ðŸ¦† Duck": "Duck",
    "duck": "Duck",
    "ðŸ” Chicken": "Chicken",
    "Chicken": "Chicken",
    "ðŸ¦ª Giant Clam": "Giant Clam",
    "giant clam": "Giant Clam",
    "ðŸŸ Shark": "Shark",
    "Shark": "Shark",
    "ðŸŸ Seahorse": "Seahorse",
    "seahorse": "Seahorse",
    "ðŸ¹âš¡ Pikachu": "Pikachu",
    "Pikachu": "Pikachu",
    "ðŸ¸ðŸ€ Bulbasaur": "Bulbasaur",
    "bulbasaur": "Bulbasaur",
    "ðŸ¢ðŸ’§ Squirtle": "ðŸ¢ðŸ’§ Squirtle",
    "squirtle": "Squirtle",
    "ðŸ‰ðŸ”¥ Charmander": "Charmander",
    "charmander": "Charmander",
    "ðŸ‹âš¡ Kyogre": "Kyogre",
    "kyogre": "Kyogre",
    "ðŸŠ Crocodile": "Crocodile",
    "crocodile": "Crocodile",
    "ðŸ¦¦ Seal": "Seal",
    "seal": "Seal",
    "ðŸ¢ Turtle": "ðŸ¢ Turtle",
    "turtle": "Turtle",
    "ðŸ¦ž Lobster": "ðŸ¦ž Lobster",
    "lobster": "Lobster",
    "ðŸ§œâ€â™€ï¸ Mermaid Boy": "Mermaid Boy",
    "mermaid boy": "Mermaid Boy",
    "ðŸ§œâ€â™€ï¸ Mermaid Girl": "Mermaid Girl",
    "mermaid girl": "Mermaid Girl"
    # tambahkan sesuai kebutuhan 
}

# ---------------- KEYBOARD / MENU STRUCTURE ---------------- #
MENU_STRUCTURE = {
    # MAIN MENU
    "main": {
        "title": "ðŸ“‹ [Menu Utama]",
        "buttons": [
            ("UMPAN", "A"),
            ("YAPPING", "B"),
            ("REGISTER", "C"),
            ("ðŸ›’STORE", "D"),
            ("CATCH", "E"),
            ("HASIL TANGKAPAN", "F"),
            ("LOGIN CHECK IN", "G"),
            ("TREASURE CHEST", "H"),
            ("ðŸ§¬ EVOLVE", "I")
        ]
    },
    
    # =============== UMPAN =============== #
    "A": {
        "title": "ðŸ“‹ Menu UMPAN",
        "buttons": [
            ("COMMON ðŸ›", "AA_COMMON"),
            ("RARE ðŸŒ", "AA_RARE"),
            ("LEGENDARY ðŸ§‡", "AA_LEGEND"),
            ("MYTHIC ðŸŸ", "AA_MYTHIC"),
            ("â¬…ï¸ Back", "main")
        ]
    },
    "AA_COMMON": {
        "title": "ðŸ“‹ TRANSFER UMPAN KE (Common)",
        "buttons": [
            ("Klik OK untuk transfer", "TRANSFER_COMMON_OK"),
            ("â¬…ï¸ Back", "A")
        ]
    },
    "AA_RARE": {
        "title": "ðŸ“‹ TRANSFER UMPAN KE (Rare)",
        "buttons": [
            ("Klik OK untuk transfer", "TRANSFER_RARE_OK"),
            ("â¬…ï¸ Back", "A")
        ]
    },
    "AA_LEGEND": {
        "title": "ðŸ“‹ TRANSFER UMPAN KE (Legend)",
        "buttons": [
            ("Klik OK untuk transfer", "TRANSFER_LEGEND_OK"),
            ("â¬…ï¸ Back", "A")
        ]
    },
    "AA_MYTHIC": {
        "title": "ðŸ“‹ TRANSFER UMPAN KE (Mythic)",
        "buttons": [
            ("Klik OK untuk transfer", "TRANSFER_MYTHIC_OK"),
            ("â¬…ï¸ Back", "A")
        ]
    },

    # =============== FISHING =============== #
    "E": {
        "title": "ðŸŽ£ CATCHING",
        "buttons": [
            ("PILIH UMPAN", "EE"),
            ("â¬…ï¸ Back", "main")
        ]
    },
    "EE": {
        "title": "ðŸ“‹ PILIH UMPAN",
        "buttons": [
            ("Lanjut Pilih Jenis", "EEE"),
            ("â¬…ï¸ Back", "E")
        ]
    },
    "EEE": {
        "title": "ðŸ“‹ Pilih Jenis Umpan",
        "buttons": [
            ("COMMON ðŸ›", "EEE_COMMON"),
            ("RARE ðŸŒ", "EEE_RARE"),
            ("LEGENDARY ðŸ§‡", "EEE_LEGEND"),
            ("MYTHIC ðŸŸ", "EEE_MYTHIC"),
            ("â¬…ï¸ Back", "EE")
        ]
    },

    # =============== REGISTER =============== #
    "C": {
        "title": "ðŸ“‹ MENU REGISTER",
        "buttons": [
            ("NEXT", "CC"),
            ("â¬…ï¸ Back", "main")
        ]
    },
    "CC": {
        "title": "ðŸ“‹ APAKAH KAMU YAKIN INGIN MENJADI PLAYER LOOT?",
        "buttons": [
            ("REGIS NOW!!", "CCC"),
            ("â¬…ï¸ Back", "C")
        ]
    },
    "CCC": {
        "title": "ðŸ“‹ Are You Sure?:",
        "buttons": [
            ("YES!", "REGISTER_YES"),
            ("NO", "REGISTER_NO")
        ]
    },

    # =============== STORE =============== #
    "D": {
        "title": "ðŸ›’STORE",
        "buttons": [
            ("BUY UMPAN", "D1"),
            ("SELL ITEM", "D2"),
            ("TUKAR POINT", "D3"),
            ("â¬…ï¸ Back", "main")
        ]
    },
    "D1": {
        "title": "ðŸ“‹ BUY UMPAN",
        "buttons": [
            ("TOPUP QRIS (cooming soon)", "D1A"),
            ("â¬…ï¸ Back", "D")
        ]
    },
    "D2": {
        "title": "ðŸ“‹ SELL ITEM",
        "buttons": [
            ("ðŸ’° CEK COIN", "D2C"),
            ("ðŸ“¦ CEK INVENTORY", "D2A"),
            ("ðŸ’° DAFTAR HARGA", "D2B"),
            ("â¬…ï¸ Back", "D")
        ]
    },
    # Submenu untuk CEK COIN
    "D2C_MENU": {
        "title": "ðŸ’° CEK COIN & PENUKARAN",
        "buttons": [
            ("ðŸ› TUKAR UMPAN COMMON A", "D2C_COMMON_A"),
            ("ðŸª± TUKAR UMPAN COMMON B", "D2C_COMMON_B"),
            ("â¬…ï¸ Back", "D2")
        ]
    },
    "D2A": {
        "title": "ðŸ“¦ CEK INVENTORY",
        "buttons": [
            ("â¬…ï¸ Back", "D2")
        ]
    },
    # DAFTAR HARGA -> note: callback format SELL_DETAIL:<code>
    "D2B": {
        "title": "ðŸ’° DAFTAR HARGA",
        "buttons": [
            ("ð“† Small Fish", "SELL_DETAIL:SELL_SMALLFISH"),
            ("ðŸŒ Snail", "SELL_DETAIL:SELL_SNAIL"),
            ("ðŸš Hermit Crab", "SELL_DETAIL:SELL_HERMITCRAB"),
            ("ðŸ¦€ Crab", "SELL_DETAIL:SELL_CRAB"),
            ("ðŸ¸ Frog", "SELL_DETAIL:SELL_FROG"),
            ("ðŸ Snake", "SELL_DETAIL:SELL_SNAKE"),
            ("ðŸ™ Octopus", "SELL_DETAIL:SELL_OCTOPUS"),
            ("à¬³ Jelly Fish", "SELL_DETAIL:SELL_JELLYFISH"),
            ("ðŸ¦ª Giant Clam", "SELL_DETAIL:SELL_GIANTCLAM"),
            ("ðŸŸ Goldfish", "SELL_DETAIL:SELL_GOLDFISH"),
            ("ðŸŸ Clownfish", "SELL_DETAIL:SELL_CLOWNFISH"),
            ("ðŸŸ Stingrays Fish", "SELL_DETAIL:SELL_STINGRAYSFISH"),
            ("ðŸŸ Doryfish", "SELL_DETAIL:SELL_DORYFISH"),
            ("ðŸŸ Bannerfish", "SELL_DETAIL:SELL_BANNERFISH"),
            ("ðŸŸ Beta Fish", "SELL_DETAIL:SELL_BETAFISH"),
            ("ðŸŸ Moorish Idol", "SELL_DETAIL:SELL_MOORISHIDOL"),
            ("ðŸŸ Anglerfish", "SELL_DETAIL:SELL_ANGLERFISH"),
            ("ðŸŸ Axolotl", "SELL_DETAIL:SELL_AXOLOTL"),
            ("ðŸ± Red Hammer Cat", "SELL_DETAIL:SELL_REDHAMMERCAT"),
            ("ðŸ± Purple Fist Cat", "SELL_DETAIL:SELL_PURPLEFISTCAT"),
            ("ðŸ± Green Dino Cat", "SELL_DETAIL:SELL_GREENDINOCAT"),
            ("ðŸ± White Winter Cat", "SELL_DETAIL:SELL_WHITEWINTERCAT"),
            ("ðŸ¦† Duck", "SELL_DETAIL:SELL_DUCK"),
            ("ðŸ” Chicken", "SELL_DETAIL:SELL_CHICKEN"),
            ("ðŸ¡ Pufferfish", "SELL_DETAIL:SELL_PUFFER"),
            ("ðŸŸ Shark", "SELL_DETAIL:SELL_SHARK"),
            ("ðŸŸ Seahorse", "SELL_DETAIL:SELL_SEAHORSE"),
            ("ðŸ¹âš¡ Pikachu", "SELL_DETAIL:SELL_PIKACHU"),
            ("ðŸ¸ðŸ€ Bulbasaur", "SELL_DETAIL:SELL_BULBASAUR"),
            ("ðŸ¢ðŸ’§ Squirtle", "SELL_DETAIL:SELL_SQUIRTLE"),
            ("ðŸ‰ðŸ”¥ Charmander", "SELL_DETAIL:SELL_CHARMANDER"),
            ("ðŸ‹âš¡ Kyogre", "SELL_DETAIL:SELL_KYOGRE"),
            ("ðŸŠ Crocodile", "SELL_DETAIL:SELL_CROCODILE"),
            ("ðŸ¦¦ Seal", "SELL_DETAIL:SELL_SEAL"),
            ("ðŸ¢ Turtle", "SELL_DETAIL:SELL_TURTLE"),
            ("ðŸ¦ž Lobster", "SELL_DETAIL:SELL_LOBSTER"),
            ("ðŸ“¿ Lucky Jewel", "SELL_DETAIL:SELL_LUCKYJEWEL"),
            ("ðŸ‹ Orca", "SELL_DETAIL:SELL_ORCA"),
            ("ðŸ’ Monkey", "SELL_DETAIL:SELL_MONKEY"),
            ("ðŸ¦ Gorilla", "SELL_DETAIL:SELL_GORILLA"),
            ("ðŸ¼ Panda", "SELL_DETAIL:SELL_PANDA"),
            ("ðŸ» Bear", "SELL_DETAIL:SELL_BEAR"),
            ("ðŸ¶ Dog", "SELL_DETAIL:SELL_DOG"),
            ("ðŸ¦‡ bat", "SELL_DETAIL:SELL_BAT"),
            ("ðŸ¬ Dolphin", "SELL_DETAIL:SELL_DOLPHIN"),
            ("ðŸ‰ Baby Dragon", "SELL_DETAIL:SELL_BABYDRAGON"),
            ("ðŸ‰ Baby Spirit Dragon", "SELL_DETAIL:SELL_BABYSPIRITDRAGON"),
            ("ðŸ‰ Baby Magma Dragon", "SELL_DETAIL:SELL_BABYMAGMADRAGON"),
            ("ðŸ‰ Skull Dragon", "SELL_DETAIL:SELL_SKULLDRAGON"),
            ("ðŸ‰ Blue Dragon", "SELL_DETAIL:SELL_BLUEDRAGON"),
            ("ðŸ‰ Yellow Dragon", "SELL_DETAIL:SELL_YELLOWDRAGON"),
            ("ðŸ‰ Black Dragon", "SELL_DETAIL:SELL_BLACKDRAGON"),
            ("ðŸ§œâ€â™€ï¸ Mermaid Boy", "SELL_DETAIL:SELL_MERMAIDBOY"),
            ("ðŸ§œâ€â™€ï¸ Mermaid Girl", "SELL_DETAIL:SELL_MERMAIDGIRL"),
            ("ðŸ‰ Cupid Dragon", "SELL_DETAIL:SELL_CUPIDDRAGON"),
            ("ðŸº Werewolf", "SELL_DETAIL:SELL_WEREWOLF"),
            ("ðŸ± Rainbow Angel Cat", "SELL_DETAIL:SELL_RAINBOWANGELCAT"),
            ("ðŸ¦â€ðŸ”¥ Fire Phoenix", "SELL_DETAIL:SELL_FIREPHOENIX"),
            ("ðŸ¦â„ï¸ Frost Phoenix", "SELL_DETAIL:SELL_FROSTPHOENIX"),
            ("ðŸ¦ðŸŒŒ Dark Phoenix", "SELL_DETAIL:SELL_DARKPHOENIX"),
            ("ðŸ¦ðŸ Chimera", "SELL_DETAIL:SELL_CHIMERA"),
            ("ðŸ¯ White Tiger", "SELL_DETAIL:SELL_WHITETIGER"),
            ("ðŸ‘¹ Dark Lord Demon", "SELL_DETAIL:SELL_DARKLORDDEMON"),
            ("ðŸ¦Š Princess of Nine Tail", "SELL_DETAIL:SELL_PRINCESSOFNINETAIL"),
            ("ðŸ‰ Dark Knight Dragon", "SELL_DETAIL:SELL_DARKKNIGHTDRAGON"),
            ("ðŸ‘¹ Dark Fish Warrior", "SELL_DETAIL:SELL_DARKFISHWARRIOR"),
            ("ðŸ‰ Snail Dragon", "SELL_DETAIL:SELL_SNAILDRAGON"),
            ("ðŸ‘‘ Queen Of Hermit", "SELL_DETAIL:SELL_QUEENOFHERMIT"),
            ("ðŸ¤– Mecha Frog", "SELL_DETAIL:SELL_MECHAFROG"),
            ("ðŸ‘‘ Queen Medusa ðŸ", "SELL_DETAIL:SELL_QUEENOFMEDUSA"),
            ("â¬…ï¸ Back", "D2"),
        ]
    },
    "D3": {
        "title": "ðŸ“‹ TUKAR POINT",
        "buttons": [
            ("Lihat Poin & Tukar", "D3A"),
            ("â¬…ï¸ Back", "D")
        ]
    },
    "D3A": {
        "title": "ðŸ“‹ ðŸ”„ POINT CHAT",
        "buttons": [
            ("TUKAR ðŸ”„ UMPAN COMMON ðŸ›", "TUKAR_POINT"),
            ("â¬…ï¸ Back", "D3")
        ]
    },

    # =============== YAPPING =============== #
    "B": {
        "title": "ðŸ“‹ YAPPING",
        "buttons": [
            ("Poin Pribadi", "BB"),
            ("âž¡ï¸ Leaderboard", "BBB"),
            ("â¬…ï¸ Back", "main")
        ]
    },
    "BB": {
        "title": "ðŸ“‹ Poin Pribadi",
        "buttons": [
            ("â¬…ï¸ Back", "B")
        ]
    },
    "BBB": {
        "title": "ðŸ“‹ Leaderboard Yapping",
        "buttons": [
            ("â¬…ï¸ Back", "B")
        ]
    },

    # =============== HASIL TANGKAPAN =============== #
    "F": {
        "title": "ðŸ“‹ HASIL TANGKAPAN",
        "buttons": [
            ("CEK INVENTORY", "FF"),
            ("â¬…ï¸ Back", "main")
        ]
    },
    "FF": {
        "title": "ðŸ“‹ CEK INVENTORY",
        "buttons": [
            ("LIHAT HASIL TANGKAPAN", "FFF"),
            ("â¬…ï¸ Back", "F")
        ]
    }
}

# Tambahan confirm untuk catching
for jenis in ["COMMON", "RARE", "LEGEND", "MYTHIC"]:
    MENU_STRUCTURE[f"EEE_{jenis}"] = {
        "title": f"ðŸ“‹ Are you want to catch using this {jenis}?",
        "buttons": [
            ("âœ… YES", f"FISH_CONFIRM_{jenis}"),
            ("âŒ NO", "EEE")
        ]
    }

# ---------------- LOGIN / ABSEN HARIAN ---------------- #
MENU_STRUCTURE["G"] = {
    "title": "ðŸ“‹ LOGIN HARIAN",
    "buttons": [
        ("âœ… Absen Hari Ini", "LOGIN_TODAY"),
        ("ðŸ“… Lihat Status Login 7 Hari", "LOGIN_STATUS"),
        ("ðŸ”„ Reset Login (OWNER)", "LOGIN_RESET") if OWNER_ID else None,
        ("â¬…ï¸ Back", "main")
    ]
}

# di bawah LOGIN CHECK IN (G)
MENU_STRUCTURE["H"] = {
    "title": "ðŸ“¦ TREASURE CHEST (OWNER ONLY)",
    "buttons": [
        ("KIRIM KE GROUP SEKARANG?", "TREASURE_SEND_NOW"),
        ("â¬…ï¸ Back", "main")
    ]
}
# ===== SUBMENU EVOLVE =====
MENU_STRUCTURE["I"] = {
    "title": "ðŸ§¬ [EVOLVE]",
    "buttons": [
        ("ð“† Small Fish", "I_SMALLFISH"),
        ("ðŸŒ Snail", "I_SNAIL"),
        ("ðŸš Hermit Crab", "I_HERMITCRAB"),
        ("ðŸ¸ Frog", "I_FROG"),
        ("ðŸ Snake", "I_SNAKE"),
        ("â¬…ï¸ Back", "main")
    ]
}

# Submenu Small Fish
MENU_STRUCTURE["I_SMALLFISH"] = {
    "title": "ðŸ§¬ Evolve ð“† Small Fish",
    "buttons": [
        ("ðŸ§¬ Evolve jadi ðŸ‘¹ Dark Fish Warrior (-1000)", "EVOLVE_SMALLFISH_CONFIRM"),
        ("COMING SOON", "COMING_SOON"),
        ("â¬…ï¸ Back", "I")
    ]
}

# Submenu Snail
MENU_STRUCTURE["I_SNAIL"] = {
    "title": "ðŸ§¬ Evolve ðŸŒ Snail",
    "buttons": [
        ("ðŸ§¬ Evolve jadi ðŸ‰ Snail Dragon (-1000)", "EVOLVE_SNAIL_CONFIRM"),
        ("â¬…ï¸ Back", "I")
    ]
}

# Submenu Hermit Crab
MENU_STRUCTURE["I_HERMITCRAB"] = {
    "title": "ðŸ§¬ Evolve ðŸš Hermit Crab",
    "buttons": [
        ("ðŸ§¬ Evolve jadi ðŸ‘‘ Queen of Hermit (-1000)", "EVOLVE_HERMITCRAB_CONFIRM"),
        ("â¬…ï¸ Back", "I")
    ]
}

# Submenu Frog
MENU_STRUCTURE["I_FROG"] = {
    "title": "ðŸ§¬ Evolve ðŸ¸ Frog",
    "buttons": [
        ("ðŸ§¬ Evolve jadi ðŸ¤– Mecha Frog (-1000)", "EVOLVE_FROG_CONFIRM"),
        ("â¬…ï¸ Back", "I")
    ]
}

# Submenu Snake
MENU_STRUCTURE["I_SNAKE"] = {
    "title": "ðŸ§¬ Evolve ðŸ Snake",
    "buttons": [
        ("ðŸ§¬ Evolve jadi ðŸ‘‘ Queen Of Medusa ðŸ (-1000)", "EVOLVE_QUEENOFMEDUSA_CONFIRM"),
        ("â¬…ï¸ Back", "I")
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
            nav.append(InlineKeyboardButton("â¬…ï¸ Prev", callback_data=f"BBB_PAGE_{page-1}"))
        if page < total_pages:
            nav.append(InlineKeyboardButton("âž¡ï¸ Next", callback_data=f"BBB_PAGE_{page+1}"))
        if nav:
            buttons.append(nav)
        buttons.append([InlineKeyboardButton("â¬…ï¸ Back", callback_data="B")])

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
        map_type = {"EEE_COMMON": ("COMMON ðŸ›", "A"), "EEE_RARE": ("RARE ðŸŒ", "B"),
                    "EEE_LEGEND": ("LEGENDARY ðŸ§‡", "C"), "EEE_MYTHIC": ("MYTHIC ðŸŸ", "D")}
        for cb, (label, tkey) in map_type.items():
            jumlah = user_umpan.get(tkey, {}).get("umpan", 0)
            buttons.append([InlineKeyboardButton(f"{label} ({jumlah} pcs)", callback_data=cb)])
        buttons.append([InlineKeyboardButton("â¬…ï¸ Back", callback_data="EE")])

    # STORE TUKAR POINT
    elif menu_key == "D3A" and user_id:
        pts = yapping.load_points().get(str(user_id), {}).get("points", 0)
        buttons.append([InlineKeyboardButton(f"TUKAR ðŸ”„ UMPAN COMMON ðŸ› (Anda: {pts} pts)", callback_data="TUKAR_POINT")])
        buttons.append([InlineKeyboardButton("â¬…ï¸ Back", callback_data="D3")])

    # HASIL TANGKAPAN INVENTORY
    elif menu_key == "FFF" and user_id:
        buttons.append([InlineKeyboardButton("â¬…ï¸ Back", callback_data="F")])

    # STORE CEK INVENTORY
    elif menu_key == "D2A" and user_id:
        buttons.append([InlineKeyboardButton("â¬…ï¸ Back", callback_data="D2")])

    # DEFAULT
    else:
        for text, cb in MENU_STRUCTURE.get(menu_key, {}).get("buttons", []):
            buttons.append([InlineKeyboardButton(text, callback_data=cb)])
        if not buttons:
            # fallback minimal supaya selalu valid
            buttons.append([InlineKeyboardButton("â¬…ï¸ Back", callback_data="main")])

    return InlineKeyboardMarkup(buttons)

# di bagian global module (atas file)
# ðŸ”¹ DROP TABLE
def get_treasure_drop():
    """
    Menentukan drop item dan tipe umpan.
    Return: (item_name, jenis_umpan, jumlah)
    """
    drop_table = [
        ("ZONK", None, 0, 10),                  # 40% zonk
        ("Umpan Common", "A", 2, 50),           # 39% common
        ("Umpan Rare", "B", 1, 29),             # 10% rare
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
    base_items = ["ðŸ¤§ Zonk", "ð“† Small Fish"]
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
    result = "ðŸŽ£ **HASIL TANGKAPANMU:**\n\n" + "\n".join(lines)
    return result

# ---------------- CALLBACK HANDLER ---------------- #
async def callback_handler(client: Client, cq: CallbackQuery):
    data = cq.data
    user_id = cq.from_user.id
    # <-- Pastikan uname didefinisikan di sini
    uname = cq.from_user.username or f"user{user_id}"

    # ====== MENU HASIL TANGKAPAN (LIHAT INVENTORY LENGKAP) ======
    if data == "FFF":
        full_text = list_full_inventory(user_id)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("â¬…ï¸ Back", callback_data="F")]])
        await cq.message.edit_text(full_text, reply_markup=kb)
        return
    
    # ===== EVOLVE SMALL FISH CONFIRM =====
    if data == "EVOLVE_SMALLFISH_CONFIRM":
        inv = aquarium.get_user_fish(user_id)
        small_fish_qty = inv.get("ð“† Small Fish", 0)

        if small_fish_qty < 1000:
            await cq.answer("âŒ Small Fish kamu kurang (butuh 1000)", show_alert=True)
            return

        # âœ… Kurangi stok Small Fish
        inv["ð“† Small Fish"] = small_fish_qty - 1000
        if inv["ð“† Small Fish"] <= 0:
            inv.pop("ð“† Small Fish")

        # âœ… Tambahkan Dark Fish Warrior
        inv["ðŸ‘¹ Dark Fish Warrior"] = inv.get("ðŸ‘¹ Dark Fish Warrior", 0) + 1

        # âœ… Simpan kembali
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)

        uname = cq.from_user.username or f"user{user_id}"

        # âœ… Balasan private ke user
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"âœ… Evolve berhasil!\n"
            f"ð“† Small Fish -1000\n"
            f"ðŸ§¬ Dark Fish Warrior +1\n\n"
            f"ðŸ“¦ Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )

        # âœ… Info ke group
        # âœ… Info ke group + pin pesan
        try:
            msg = await client.send_message(
                TARGET_GROUP,
                f"ðŸ§¬ @{uname} berhasil evolve!\n"
                f"ðŸ§¬ Small Fish â†’ ðŸ‘¹ Dark Fish Warrior ðŸŽ‰"
            )
            # âœ… Pin pesan ini tanpa menghapus pin lama
            await client.pin_chat_message(TARGET_GROUP, msg.id, disable_notification=True)
        except Exception as e:
            logger.error(f"Gagal kirim atau pin info evolve ke group: {e}")

    # ===== EVOLVE HERMIT CRAB CONFIRM =====
    if data == "EVOLVE_SNAIL_CONFIRM":
        inv = aquarium.get_user_fish(user_id)
        snail_qty = inv.get("ðŸŒ Snail", 0)

        if snail_qty < 1000:
            await cq.answer("âŒ Hermit Crab kamu kurang (butuh 1000)", show_alert=True)
            return

        # âœ… Kurangi stok Hermit Crab
        inv["ðŸŒ Snail"] = snail_qty - 1000
        if inv["ðŸŒ Snail"] <= 0:
            inv.pop("ðŸŒ Snail")

        # âœ… Tambahkan ðŸ‰ Snail Dragon
        inv["ðŸ‰ Snail Dragon"] = inv.get("ðŸ‰ Snail Dragon", 0) + 1

        # âœ… Simpan kembali
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)

        # âœ… Balasan private ke user
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"âœ… Evolve berhasil!\n"
            f"ðŸŒ Snail -1000\n"
            f"ðŸ§¬ ðŸ‰ Snail Dragon +1\n\n"
            f"ðŸ“¦ Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )

        # âœ… Info ke group
        try:
            msg = await client.send_message(
                TARGET_GROUP,
                f"ðŸ§¬ @{uname} berhasil evolve!\n"
                f"ðŸ§¬ Snail â†’ ðŸ‰ Snail Dragon ðŸŽ‰"
            )
            await client.pin_chat_message(TARGET_GROUP, msg.id, disable_notification=True)
        except Exception as e:
            logger.error(f"Gagal kirim atau pin info evolve ke group: {e}")
    
    # ===== EVOLVE HERMIT CRAB CONFIRM =====
    if data == "EVOLVE_HERMITCRAB_CONFIRM":
        inv = aquarium.get_user_fish(user_id)
        hermit_crab_qty = inv.get("ðŸš Hermit Crab", 0)

        if hermit_crab_qty < 1000:
            await cq.answer("âŒ Hermit Crab kamu kurang (butuh 1000)", show_alert=True)
            return

        # âœ… Kurangi stok Hermit Crab
        inv["ðŸš Hermit Crab"] = hermit_crab_qty - 1000
        if inv["ðŸš Hermit Crab"] <= 0:
            inv.pop("ðŸš Hermit Crab")

        # âœ… Tambahkan ðŸ‘‘ Queen of Hermit
        inv["ðŸ‘‘ Queen of Hermit"] = inv.get("ðŸ‘‘ Queen of Hermit", 0) + 1

        # âœ… Simpan kembali
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)

        # âœ… Balasan private ke user
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"âœ… Evolve berhasil!\n"
            f"ðŸš Hermit Crab -1000\n"
            f"ðŸ§¬ ðŸ‘‘ Queen of Hermit +1\n\n"
            f"ðŸ“¦ Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )

        # âœ… Info ke group
        try:
            msg = await client.send_message(
                TARGET_GROUP,
                f"ðŸ§¬ @{uname} berhasil evolve!\n"
                f"ðŸ§¬ Hermit Crab â†’ ðŸ‘‘ Queen of Hermit ðŸŽ‰"
            )
            await client.pin_chat_message(TARGET_GROUP, msg.id, disable_notification=True)
        except Exception as e:
            logger.error(f"Gagal kirim atau pin info evolve ke group: {e}")

        # ===== EVOLVE FROG CONFIRM =====
    if data == "EVOLVE_FROG_CONFIRM":
        inv = aquarium.get_user_fish(user_id)
        frog_qty = inv.get("ðŸ¸ Frog", 0)

        if frog_qty < 1000:
            await cq.answer("âŒ Frog kamu kurang (butuh 1000)", show_alert=True)
            return

        # âœ… Kurangi stok Frog
        inv["ðŸ¸ Frog"] = frog_qty - 1000
        if inv["ðŸ¸ Frog"] <= 0:
            inv.pop("ðŸ¸ Frog")

        # âœ… Tambahkan ðŸ¤– Mecha Frog
        inv["ðŸ¤– Mecha Frog"] = inv.get("ðŸ¤– Mecha Frog", 0) + 1

        # âœ… Simpan ke database
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)

        uname = cq.from_user.username or f"user{user_id}"

        # âœ… Balasan ke user
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"âœ… Evolve berhasil!\n"
            f"ðŸ¸ Frog -1000\n"
            f"ðŸ§¬ ðŸ¤– Mecha Frog +1\n\n"
            f"ðŸ“¦ Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )

        # âœ… Info ke group + pin pesan
        try:
            msg = await client.send_message(
                TARGET_GROUP,
                f"ðŸ§¬ @{uname} berhasil evolve!\n"
                f"Frog â†’ ðŸ¤– Mecha Frog ðŸŽ‰"
            )
            await client.pin_chat_message(TARGET_GROUP, msg.id, disable_notification=True)
        except Exception as e:
            logger.error(f"Gagal kirim atau pin info evolve ke group: {e}")


    # ===== EVOLVE SNAKE CONFIRM =====
    if data == "EVOLVE_QUEENOFMEDUSA_CONFIRM":
        inv = aquarium.get_user_fish(user_id)
        snake_qty = inv.get("ðŸ Snake", 0)

        if snake_qty < 1000:
            await cq.answer("âŒ Snake kamu kurang (butuh 1000)", show_alert=True)
            return

        # âœ… Kurangi stok Snake
        inv["ðŸ Snake"] = snake_qty - 1000
        if inv["ðŸ Snake"] <= 0:
            inv.pop("ðŸ Snake")

        # âœ… Tambahkan ðŸ‘‘ Queen Of Medusa ðŸ
        inv["ðŸ‘‘ Queen Of Medusa ðŸ"] = inv.get("ðŸ‘‘ Queen Of Medusa ðŸ", 0) + 1

        # âœ… Simpan ke database
        db = aquarium.load_data()
        db[str(user_id)] = inv
        aquarium.save_data(db)

        uname = cq.from_user.username or f"user{user_id}"

        # âœ… Balasan ke user
        inv_text = aquarium.list_inventory(user_id)
        await cq.message.edit_text(
            f"âœ… Evolve berhasil!\n"
            f"ðŸ Snake -1000\n"
            f"ðŸ§¬ ðŸ‘‘ Queen Of Medusa ðŸ +1\n\n"
            f"ðŸ“¦ Inventory terbaru:\n{inv_text}",
            reply_markup=make_keyboard("I", user_id)
        )

        # âœ… Info ke group + pin pesan
        try:
            msg = await client.send_message(
                TARGET_GROUP,
                f"ðŸ§¬ @{uname} berhasil evolve!\n"
                f"Snake â†’ ðŸ‘‘ Queen Of Medusa ðŸ ðŸŽ‰"
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
                await cq.answer("âŒ Kamu sudah mengklaim Treasure Chest ini sebelumnya!", show_alert=True)
                return

            await asyncio.sleep(3)  # efek dramatis

            # ðŸŽ² Tentukan drop
            item, jenis, jumlah = get_treasure_drop()

            if item == "ZONK":
                msg = f"ðŸ˜¢ @{uname} mendapatkan ZONK!"
            else:
                msg = f"ðŸŽ‰ @{uname} mendapatkan {jumlah} pcs ðŸ›{item}!"
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
            await cq.answer("âŒ Hanya owner yang bisa akses menu ini.", show_alert=True)
            return

        # ðŸ”¹ Reset claim
        CLAIMED_CHEST_USERS.clear()

        # ðŸ”¹ Hapus pesan chest lama
        if LAST_TREASURE_MSG_ID is not None:
            try:
                await cq._client.delete_messages(TARGET_GROUP, LAST_TREASURE_MSG_ID)
            except Exception as e:
                logger.warning(f"Gagal hapus Treasure Chest lama: {e}")

        # ðŸ”¹ Kirim Treasure Chest baru
        try:
            msg = await cq._client.send_message(
                TARGET_GROUP,
                "ðŸ“¦ **Treasure Chest telah dikirim oleh OWNER!**\n"
                "Cepat klaim sebelum terlambat! ðŸŽ",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("ðŸ”‘ Buka Treasure Chest", callback_data="treasure_chest")]]
                )
            )
            LAST_TREASURE_MSG_ID = msg.id
        except Exception as e:
            logger.error(f"Gagal kirim Treasure Chest: {e}")

        await cq.message.edit_text(
            "âœ… Treasure Chest berhasil dikirim ke group!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("â¬…ï¸ Kembali", callback_data="H")]]
            )
        )
        return

    # ===== LOGIN HARIAN CALLBACK =====
    if data == "LOGIN_TODAY":
        init_user_login(user_id)
        today = get_today_int()
        user_login = LOGIN_STATE[user_id]
        if user_login["last_login_day"] == today:
            await cq.answer("âŒ Kamu sudah absen hari ini!", show_alert=True)
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
            msg = f"ðŸŽ‰ Absen berhasil! Kamu mendapatkan {reward} Umpan COMMON ðŸ›. Streak: {user_login['streak']} hari."
        else:
            msg = f"âœ… Absen berhasil! Tapi umpan sudah diterima sebelumnya. Streak: {user_login['streak']} hari."

        await cq.message.edit_text(msg, reply_markup=make_keyboard("G", user_id))
        return

    # ===== RESET LOGIN (OWNER ONLY) =====
    if data == "LOGIN_RESET":
        if user_id != OWNER_ID:
            await cq.answer("âŒ Hanya owner yang bisa reset login.", show_alert=True)
            return
        LOGIN_STATE.clear()
        await cq.message.edit_text("âœ… Semua data login harian telah direset.", reply_markup=make_keyboard("G", user_id))
        return

    elif data == "LOGIN_STATUS":
        # tampilkan 7 hari terakhir streak user
        init_user_login(user_id)
        user_login = LOGIN_STATE[user_id]
        streak = user_login["streak"]

        status_text = "ðŸ“… Status LOGIN 7 Hari Terakhir:\n"
        for i in range(7):
            status_text += f"LOGIN-{i+1}: "
            status_text += "âœ…" if streak >= i + 1 else "âŒ"
            status_text += "\n"

        await cq.message.edit_text(status_text, reply_markup=make_keyboard("G", user_id))
        return

    # MENU OPEN untuk login, tombol navigasi
    elif data == "G":
        # tampilkan menu LOGIN HARIAN
        buttons = [
            [InlineKeyboardButton("âœ… Absen Hari Ini", callback_data="LOGIN_TODAY")],
            [InlineKeyboardButton("ðŸ“… Lihat Status Login 7 Hari", callback_data="LOGIN_STATUS")],
            [InlineKeyboardButton("â¬…ï¸ Back", callback_data="main")]
        ]
        kb = InlineKeyboardMarkup(buttons)
        await cq.message.edit_text("ðŸ“‹ LOGIN HARIAN", reply_markup=kb)
        return

    # ---------------- REGISTER FLOW ---------------- #
    if data == "REGISTER_YES":
        uname = cq.from_user.username or "TanpaUsername"
        text = "ðŸŽ‰ Selamat kamu menjadi Player Loot!"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("ðŸ“‡ SCAN ID & USN", callback_data="REGISTER_SCAN")],
            [InlineKeyboardButton("â¬…ï¸ Back", callback_data="main")]
        ])
        await cq.message.edit_text(text, reply_markup=kb)
        user_database.set_player_loot(user_id, True, uname)
        try:
            await client.send_message(
                OWNER_ID,
                f"ðŸ“¢ [REGISTER] Player baru mendaftar!\n\nðŸ‘¤ Username: @{uname}\nðŸ†” User ID: {user_id}"
            )
        except Exception as e:
            logger.error(f"Gagal kirim notif register ke owner: {e}")
        return

    if data == "REGISTER_SCAN":
        uname = cq.from_user.username or "TanpaUsername"
        text = f"ðŸ“‡ Data Player\n\nðŸ‘¤ Username: @{uname}\nðŸ†” User ID: {user_id}"
        await cq.message.edit_text(text, reply_markup=make_keyboard("main", user_id))
        return

    # TRANSFER START
    if data.startswith("TRANSFER_"):
        jenis = data.split("_")[1]
        map_jenis = {"COMMON": "A", "RARE": "B", "LEGEND": "C", "MYTHIC": "D"}

        # ðŸ”’ Batasi transfer umpan Rare hanya untuk OWNER
        if jenis == "RARE" and user_id != OWNER_ID:
            await cq.answer("âŒ Hanya OWNER yang bisa transfer Umpan Rare ðŸŒ.", show_alert=True)
            return

        TRANSFER_STATE[user_id] = {"jenis": map_jenis.get(jenis)}
        await cq.message.reply("âœï¸ Masukkan format transfer: `@username jumlah`\nContoh: `@user 2`")
        return

    # CHECK COIN Fizz
    # ================= CEK COIN & SUBMENU ================= #
    if data == "D2C":
        kb = make_keyboard("D2C_MENU", cq.from_user.id)
        await cq.message.edit_text("ðŸ’° Pilih menu tukar coin:", reply_markup=kb)
        return

    elif data == "D2C_COMMON_A":
        uid = cq.from_user.id
        total_coin = fizz_coin.get_coin(uid)
        TUKAR_COIN_STATE[uid] = {"jenis": "A"}
        await cq.message.edit_text(
            f"ðŸ› Kamu punya {total_coin} fizz coin.\n\n"
            f"Masukkan jumlah coin yang ingin kamu tukarkan.\n"
            f"(5 coin = 1 umpan Common Type A)\n\n"
            f"Contoh: `25` untuk menukar 25 coin jadi 5 umpan.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("â¬…ï¸ Batal", callback_data="D2C_MENU")]])
        )
        return

    elif data == "D2C_COMMON_B":
        uid = cq.from_user.id
        total_coin = fizz_coin.get_coin(uid)
        TUKAR_COIN_STATE[uid] = {"jenis": "B"}
        await cq.message.edit_text(
            f"ðŸª± Kamu punya {total_coin} fizz coin.\n\n"
            f"Masukkan jumlah coin yang ingin kamu tukarkan.\n"
            f"(50 coin = 1 umpan Rare Type B)\n\n"
            f"Contoh: `50` untuk menukar 50 coin jadi 1 umpan.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("â¬…ï¸ Batal", callback_data="D2C_MENU")]])
        )
        return
    
    # FISHING
    # FISHING
    # ----------------- FUNGSI MEMANCING -----------------
    async def fishing_task(client, uname, user_id, jenis, task_id):
        try:
            await asyncio.sleep(2)
            # Pesan di grup sekarang termasuk task_id
           #await client.send_message(TARGET_GROUP, f"```\nðŸŽ£ @{uname} trying to catch... task#{task_id}```\n")

            # Jalankan loot system
            loot_result = await fishing_loot(client, None, uname, user_id, umpan_type=jenis)

            # ==== Kurangi umpan setelah hasil drop keluar ====
            jk_map = {"COMMON": "A", "RARE": "B", "LEGEND": "C", "MYTHIC": "D"}
            jk = jk_map.get(jenis, "A")

            if user_id != OWNER_ID:
                ud = umpan.get_user(user_id)
                if not ud or ud.get(jk, {}).get("umpan", 0) <= 0:
                    # kalau ternyata umpan habis (misal paralel auto catching), kasih info
                    await client.send_message(user_id, "âŒ Umpanmu habis, hasil pancingan ini batal.")
                    return
                umpan.remove_umpan(user_id, jk, 1)

            await asyncio.sleep(10)
            # Hanya kirim ke grup, hapus private
            msg_group = f"ðŸŽ£ @{uname} got {loot_result}! from task#{task_id}"
            await client.send_message(TARGET_GROUP, msg_group)

        except Exception as e:
            logger.error(f"[FISHING TASK] Error untuk @{uname}: {e}")

    # ----------------- CALLBACK HANDLER -----------------
    if data.startswith("FISH_CONFIRM_"):
        jenis = data.replace("FISH_CONFIRM_", "")
        uname = cq.from_user.username or f"user{user_id}"

        # Tombol Back
        kb_back = InlineKeyboardMarkup([[InlineKeyboardButton("â¬…ï¸ Back", callback_data="E")]])

        # Cek umpan cukup dulu (tanpa mengurangi)
        jk_map = {"COMMON": "A", "RARE": "B", "LEGEND": "C", "MYTHIC": "D"}
        jk = jk_map.get(jenis, "A")
        if user_id != OWNER_ID:
            ud = umpan.get_user(user_id)
            if not ud or ud.get(jk, {}).get("umpan", 0) <= 0:
                await cq.answer("âŒ Umpan tidak cukup!", show_alert=True)
                return

        now = asyncio.get_event_loop().time()
        last_time = user_last_fishing[user_id]

        if now - last_time < 10:
            await cq.message.edit_text(
                "â³ Wait a sec before you catch again..",
                reply_markup=kb_back
            )
            return

        user_last_fishing[user_id] = now
        user_task_count[user_id] += 1
        task_id = f"{user_task_count[user_id]:02d}"

        await cq.message.edit_text(
            f"ðŸŽ£ You successfully threw the bait! {jenis} to loot task#{task_id}!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("ðŸŽ£ Catch again", callback_data=f"FISH_CONFIRM_{jenis}")],
                [InlineKeyboardButton("ðŸ¤– Auto Catch 50x", callback_data=f"AUTO_FISH_{jenis}")],
                [InlineKeyboardButton("â¬…ï¸ Back", callback_data="E")]
            ])
        )

        # Jalankan task memancing
        asyncio.create_task(fishing_task(client, uname, user_id, jenis, task_id))


    # ----------------- AUTO MEMANCING 5x -----------------
    # ----------------- AUTO MEMANCING 5x -----------------
    elif data.startswith("AUTO_FISH_"):
        jenis = data.replace("AUTO_FISH_", "")
        uname = cq.from_user.username or f"user{user_id}"

        now = asyncio.get_event_loop().time()
        last_time = user_last_fishing.get(user_id, 0)

        if now - last_time < 10:
            await cq.answer("â³ Wait cooldown 10 sec before auto catching!", show_alert=True)
            return

        await cq.answer("ðŸ¤– Auto Catching 50x!!! Start!")

        async def auto_fishing():
            for i in range(50):
                now = asyncio.get_event_loop().time()
                if now - user_last_fishing.get(user_id, 0) < 10:
                    break  # stop kalau masih cooldown

                # cek stok umpan dulu (tanpa mengurangi)
                jk_map = {"COMMON": "A", "RARE": "B", "LEGEND": "C", "MYTHIC": "D"}
                jk = jk_map.get(jenis, "A")
                if user_id != OWNER_ID:
                    ud = umpan.get_user(user_id)
                    if not ud or ud.get(jk, {}).get("umpan", 0) <= 0:
                        # Stop jika umpan habis, tapi tidak mengirim pesan
                        break

                user_last_fishing[user_id] = now
                user_task_count[user_id] += 1
                task_id = f"{user_task_count[user_id]:02d}"

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
            text = "âŒ Kamu belum punya poin."
        else:
            lvl = udata.get("level", 0)
            badge = yapping.get_badge(lvl)
            text = f"ðŸ“Š Poin Pribadi\n\nðŸ‘¤ {udata.get('username','Unknown')}\nâ­ {udata.get('points',0)} pts\nðŸ… Level {lvl} {badge}"
        await cq.message.edit_text(text, reply_markup=make_keyboard("BB", user_id))
        return

    # LEADERBOARD
    if data == "BBB":
        await show_leaderboard(cq, user_id, 0)
        return

    # TUKAR POINT
    if data == "TUKAR_POINT":
        TUKAR_POINT_STATE[user_id] = {"step": 1, "jumlah_umpan": 0}
        await cq.message.reply("Masukkan jumlah umpan COMMON ðŸ› yang ingin ditukar (100 poin = 1 umpan):")
        return

    # ---------------- TUKAR POINT CONFIRM ---------------- #
    if data == "TUKAR_CONFIRM":
        info = TUKAR_POINT_STATE.get(user_id)
        if not info or info.get("step") != 2:
            await cq.answer("âŒ Proses tidak valid.", show_alert=True)
            return
        jml = info["jumlah_umpan"]
        pts = yapping.load_points().get(str(user_id), {}).get("points", 0)
        if pts < jml * 100:
            await cq.answer("âŒ Point tidak cukup.", show_alert=True)
            TUKAR_POINT_STATE.pop(user_id, None)
            return
        # lakukan tukar
        yapping.update_points(user_id, -jml * 100)
        umpan.add_umpan(user_id, "A", jml)  # âœ… hanya COMMON
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("â¬…ï¸ Back", callback_data="D3A")]])
        await cq.message.edit_text(
            f"âœ… Tukar berhasil! {jml} umpan COMMON ðŸ› ditambahkan ke akunmu.", reply_markup=kb
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
        text = f"ðŸ’° Harga {item['name']}\n1x = {item['price']} coin\n\nKetik jumlah yang ingin kamu jual, atau pilih tombol untuk mulai."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("ðŸ›’ Jual Sekarang (ketik jumlah)", callback_data=f"SELL_START:{item_code}")],
            [InlineKeyboardButton("â¬…ï¸ Back", callback_data="D2B")]
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
        await cq.message.edit_text(f"ðŸ“ Ketik jumlah {item['name']} yang ingin kamu jual (contoh: 2)\nKetik 0 untuk batal.")
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
        new_total = fizz_coin.add_coin(user_id, earned)  # âœ… simpan ke database
        await cq.message.reply_text(
            f"âœ… Berhasil menjual {amount}x {item['name']}.\n"
            f"Kamu mendapatkan {earned} coin fizz.\n"
            f"ðŸ’° Total coinmu sekarang: {new_total} fizz coin\n"
            f"Sisa stok {item['name']}: {new_stock}",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("â¬…ï¸ Back", callback_data="D2")]
                ]
            )
        )
        return

    if data == "SELL_CANCEL":
        SELL_WAITING.pop(user_id, None)
        # lebih aman fallback ke D2 jika ada, kalau tidak ada ke main
        try:
            await cq.message.edit_text("âŒ Penjualan dibatalkan.", reply_markup=make_keyboard("D2", user_id))
        except Exception:
            await cq.message.edit_text("âŒ Penjualan dibatalkan.", reply_markup=make_keyboard("main", user_id))
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
        await cq.message.edit_text(f"ðŸŽ£ Inventorymu:\n\n{inv_text}", reply_markup=kb)
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
            return await message.reply(f"âŒ Kamu tidak memiliki {item['name']} sama sekali.")
        if amount > stock:
            return await message.reply(f"âŒ Stok tidak cukup ({stock} pcs).")

        # minta konfirmasi dengan tombol YA/TIDAK
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("âœ… Ya", callback_data=f"SELL_CONFIRM:{item_code}:{amount}"),
                InlineKeyboardButton("âŒ Tidak", callback_data="SELL_CANCEL")
            ]
        ])
        return await message.reply(
            f"ðŸ“Œ Konfirmasi\nApakah kamu yakin ingin menjual {amount}x {item['name']}?\nStok kamu: {stock}",
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
                await message.reply(f"âŒ Username {rname} tidak ada di database!")
                TRANSFER_STATE.pop(uid, None)
                return

            # ====== PROSES TRANSFER ====== #
            # ====== PROSES TRANSFER ====== #
            # ðŸ”’ Batasi transfer umpan Rare hanya untuk OWNER
            if jenis == "B" and uid != OWNER_ID:
                await message.reply("âŒ Hanya OWNER yang bisa transfer Umpan Rare ðŸŒ.")
                TRANSFER_STATE.pop(uid, None)
                return

            if uid == OWNER_ID:
                umpan.add_umpan(rid, jenis, amt)
            else:
                sd = umpan.get_user(uid)
                if sd[jenis]["umpan"] < amt:
                    return await message.reply("âŒ Umpan tidak cukup!")
                umpan.remove_umpan(uid, jenis, amt)
                umpan.add_umpan(rid, jenis, amt)

            # Info ke OWNER (langsung)
            await message.reply(
                f"âœ… Transfer {amt} umpan ke {rname} berhasil!",
                reply_markup=make_keyboard("main", uid)
            )

            # Info ke penerima (delay 0.5 detik)
            try:
                await asyncio.sleep(0.5)
                await client.send_message(
                    rid,
                    f"ðŸŽ Kamu mendapat {amt} umpan dari @{uname}"
                )
            except Exception as e:
                logger.error(f"Gagal notif penerima {rid}: {e}")

            # Info ke GROUP (delay 2 detik)
            try:
                await asyncio.sleep(2)
                await client.send_message(
                    TARGET_GROUP,
                    f"```\nðŸ“¢ Transfer Umpan!\nðŸ‘¤ @{uname} memberi {amt} umpan ke {rname}```\n"
                )
            except Exception as e:
                logger.error(f"Gagal notif group: {e}")

        except Exception as e:
            await message.reply(f"âŒ Error: {e}")

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
                return await message.reply(f"âŒ Point tidak cukup ({pts} pts, butuh {jumlah * 100} pts).")
            TUKAR_POINT_STATE[uid]["jumlah_umpan"] = jumlah
            TUKAR_POINT_STATE[uid]["step"] = 2
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("âœ… YA", callback_data="TUKAR_CONFIRM")],
                [InlineKeyboardButton("âŒ Batal", callback_data="D3A")]
            ])
            await message.reply(f"ðŸ“Š Yakin ingin menukar {jumlah} umpan COMMON ðŸ›?\n(100 chat points = 1 umpan)", reply_markup=kb)
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
                await message.reply("âŒ Jumlah coin harus lebih dari 0.")
                return

            total_coin = fizz_coin.get_coin(uid)
            if jumlah_coin > total_coin:
                await message.reply(f"âŒ Coin kamu tidak cukup. Kamu hanya punya {total_coin} fizz coin.")
                return

            # Set parameter berdasarkan jenis
            if jenis == "A":
                min_coin, konversi, nama, emoji = 5, 5, "COMMON (Type A)", "ðŸ›"
            elif jenis == "B":
                min_coin, konversi, nama, emoji = 50, 50, "RARE (Type B)", "ðŸª±"
            else:
                await message.reply("âŒ Tipe tukar tidak valid.")
                return

            if jumlah_coin < min_coin:
                await message.reply(f"âŒ Minimal {min_coin} coin untuk tukar 1 umpan {nama}.")
                return

            # Hitung jumlah umpan yang bisa didapat
            umpan_didapat = jumlah_coin // konversi
            biaya = umpan_didapat * konversi
            sisa_coin = jumlah_coin - biaya  # coin yang tidak habis dibagi tetap tersisa di user

            if umpan_didapat == 0:
                await message.reply(f"âŒ Coin tidak cukup untuk ditukar menjadi umpan {nama}.")
                return

            # Kurangi coin & tambahkan umpan
            fizz_coin.add_coin(uid, -biaya)
            umpan.add_umpan(uid, jenis, umpan_didapat)

            await message.reply(
                f"âœ… Tukar berhasil!\n\n"
                f"ðŸ’° -{biaya} fizz coin\n"
                f"{emoji} +{umpan_didapat} Umpan {nama}\n\n"
                f"Sisa coin: {fizz_coin.get_coin(uid)}",
                reply_markup=make_keyboard("D2C_MENU", uid)
            )

        except ValueError:
            await message.reply("âŒ Format salah. Masukkan angka jumlah coin yang ingin ditukar.")
        finally:
            TUKAR_COIN_STATE.pop(uid, None)
        return

# ---------------- SHOW LEADERBOARD ---------------- #
async def show_leaderboard(cq: CallbackQuery, uid: int, page: int = 0):
    pts = yapping.load_points()
    sorted_pts = sorted(pts.items(), key=lambda x: x[1]["points"], reverse=True)
    total_pages = max((len(sorted_pts) - 1) // 10, 0) if len(sorted_pts) > 0 else 0
    start, end = page * 10, page * 10 + 10
    text = f"ðŸ† Leaderboard Yapping (Page {page+1}/{total_pages+1}) ðŸ†\n\n"
    for i, (u, pdata) in enumerate(sorted_pts[start:end], start=start + 1):
        text += f"{i}. {pdata.get('username','Unknown')} - {pdata.get('points',0)} pts | Level {pdata.get('level',0)} {yapping.get_badge(pdata.get('level',0))}\n"
    await cq.message.edit_text(text, reply_markup=make_keyboard("BBB", uid, page))

# ---------------- SHOW LEADERBOARD ---------------- #
async def show_leaderboard(cq: CallbackQuery, uid: int, page: int = 0):
    pts = yapping.load_points()
    sorted_pts = sorted(pts.items(), key=lambda x: x[1]["points"], reverse=True)
    total_pages = max((len(sorted_pts) - 1) // 10, 0) if len(sorted_pts) > 0 else 0
    start, end = page * 10, page * 10 + 10
    text = f"ðŸ† Leaderboard Yapping (Page {page+1}/{total_pages+1}) ðŸ†\n\n"
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
    await message.reply("ðŸ“‹ Menu Utama:", reply_markup=make_keyboard("main", uid))

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







