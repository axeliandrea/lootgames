# lootgames/modules/fishing_loot.py
import random
import asyncio
import logging
from pyrogram import Client
from lootgames.modules.fishing_helper import send_single_emoji, FISHING_EMOJI
from lootgames.modules import aquarium, umpan

logger = logging.getLogger(__name__)

# ---------------- LOOT TABLE (TOTAL ≈1000.00%) ---------------- #
FISH_LOOT = {
    # ---------------- TERMURAH → TERMAHAL ---------------- #
    # Common
    "🤧 Zonk": 50.00,                 # harga 0
    "𓆝 Small Fish": 128.00,          # harga 1
    "🐌 Snail": 128.00,               # harga 2
    "🐚 Hermit Crab": 128.00,         # harga 2
    "🦀 Crab": 128.00,                # harga 2
    "🐸 Frog": 128.00,                # harga 2
    "🐍 Snake": 128.00,               # harga 2
    "🐙 Octopus": 100.00,             # harga 3

    # Rare
    "ଳ Jelly Fish": 80.00,            # harga 4
    "🦪 Giant Clam": 80.00,           # harga 4
    "🐟 Goldfish": 80.00,             # harga 4
    "🐟 Stingrays Fish": 80.00,       # harga 4
    "🐟 Clownfish": 80.00,            # harga 4
    "🐟 Doryfish": 80.00,             # harga 4
    "🐟 Bannerfish": 80.00,           # harga 4
    "🐟 Moorish Idol": 80.00,         # harga 4
    "🐟 Axolotl": 80.00,              # harga 4
    "🐟 Beta Fish": 80.00,            # harga 4
    "🐟 Anglerfish": 80.00,           # harga 4
    "🦆 Duck": 80.00,                 # harga 4

    # Ultra Rare
    "🐡 Pufferfish": 70.00,           # harga 5
    "📿 Lucky Jewel": 60.00,          # harga 7
    "🐱 Red Hammer Cat": 10.00,       # harga 8
    "🐱 Purple Fist Cat": 10.00,      # harga 8
    "🐱 Green Dino Cat": 10.00,       # harga 8
    "🐱 White Winter Cat": 10.00,     # harga 8
    "🐟 Shark": 40.00,                # harga 10
    "🐟 Seahorse": 40.00,             # harga 10
    "🐊 Crocodile": 40.00,            # harga 10
    "🦦 Seal": 40.00,                 # harga 10
    "🐢 Turtle": 40.00,               # harga 10
    "🦞 Lobster": 40.00,              # harga 10

    # Legendary
    "🐋 Orca": 30.00,                 # harga 15
    "🐬 Dolphin": 30.00,              # harga 15
    "🐹⚡ Pikachu": 5.00,             # harga 30
    "🐸🍀 Bulbasaur": 5.00,           # harga 30
    "🐢💧 Squirtle": 5.00,            # harga 30
    "🐉🔥 Charmander": 5.00,          # harga 30
    "🐋⚡ Kyogre": 5.00,              # harga 30

    # Mythic
    "🐉 Baby Dragon": 0.10,           
    "🐉 Baby Spirit Dragon": 0.10,    
    "🐉 Baby Magma Dragon": 0.10,     
    "🐉 Skull Dragon": 0.09,          
    "🐉 Blue Dragon": 0.09,           
    "🐉 Black Dragon": 0.09,          
    "🐉 Yellow Dragon": 0.09,         
    "🧜‍♀️ Mermaid Boy": 0.09,         
    "🧜‍♀️ Mermaid Girl": 0.09,        
    "🐉 Cupid Dragon": 0.01,          
    "🐺 Werewolf": 0.001,  
    "🐱 Rainbow Angel Cat": 0.001, 
    "👹 Dark Lord Demon": 0.001,      
    "🦊 Princess of Nine Tail": 0.001,    
}

# ---------------- BUFF RATE ---------------- #
BUFF_RATE = {
    "COMMON": 0.0,
    "RARE": 50.50,
    "LEGEND": 7.00,
    "MYTHIC": 10.00
}

# ---------------- FISHING FUNCTION ---------------- #
async def fishing_loot(client: Client, target_chat: int, username: str, user_id: int, umpan_type: str = "COMMON") -> str:
    buff = BUFF_RATE.get(umpan_type, 0.0)
    loot_item = roll_loot(buff, umpan_type)

    logger.info(f"[FISHING] {username} ({user_id}) memancing dengan {umpan_type}, mendapatkan: {loot_item}")

    try:
        await asyncio.sleep(2)
        if target_chat:
            await client.send_message(target_chat, f"@{username} mendapatkan {loot_item}!")
        aquarium.add_fish(user_id, loot_item, 1)
    except Exception as e:
        logger.error(f"[FISHING] Error untuk {username}: {e}")

    return loot_item

# ---------------- HELPERS ---------------- #
def roll_loot(buff: float, umpan_type: str = "COMMON") -> str:
    items = []
    chances = []

    # Batasan jenis ikan per jenis umpan
    if umpan_type == "COMMON":
        allowed = list(FISH_LOOT.keys())[:48]   # Common → awal Mythic
    elif umpan_type == "RARE":
        allowed = list(FISH_LOOT.keys())[8:55]  # Rare → Mythic menengah
    elif umpan_type == "LEGEND":
        allowed = list(FISH_LOOT.keys())[20:]   # Ultra Rare → Mythic
    elif umpan_type == "MYTHIC":
        allowed = list(FISH_LOOT.keys())[-14:]  # Khusus Mythic
    else:
        allowed = list(FISH_LOOT.keys())

    # Daftar Mythic & Ultra Mythic untuk pengecualian umpan RARE
    mythic_items = [
        "🐉 Yellow Dragon", "🧜‍♀️ Mermaid Boy", "🧜‍♀️ Mermaid Girl",
        "🐉 Cupid Dragon"
    ]
    ultra_mythic_items = ["👹 Dark Lord Demon", "🦊 Princess of Nine Tail", "🐱 Rainbow Angel Cat"]

    for item, base_chance in FISH_LOOT.items():
        if item not in allowed:
            continue

        bonus = 0.0

        # === Pengecualian buff untuk umpan RARE === #
        if umpan_type == "RARE":
            if item in mythic_items:
                bonus = 50.0
            elif item in ultra_mythic_items:
                bonus = 10.5
            elif item != "🤧 Zonk":
                bonus = buff
        elif umpan_type == "LEGEND":
            if item in mythic_items:
                bonus = 4.0      # bonus Mythic saat LEGEND
            elif item in ultra_mythic_items:
                bonus = 7.0      # bonus Ultra Mythic saat LEGEND
            elif item != "🤧 Zonk":
                bonus = buff     # buff default LEGEND 7%
        else:
            bonus = buff if item != "🤧 Zonk" else 0

        items.append(item)
        chances.append(base_chance + bonus)

        # Debug optional (aktifkan jika mau analisis drop rate)
        # logger.debug(f"[BUFF] {item}: base={base_chance} + bonus={bonus} → total={base_chance + bonus}")

    loot_item = random.choices(items, weights=chances, k=1)[0]
    return loot_item

# ---------------- WORKER ---------------- #
async def fishing_worker(app: Client):
    logger.info("[FISHING WORKER] Worker siap berjalan...")
    while True:
        logger.debug("[FISHING WORKER] Tick... tidak ada aksi saat ini")
        await asyncio.sleep(60)
