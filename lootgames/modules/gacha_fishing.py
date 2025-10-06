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
    "🤧 Zonk": 50.00,               # dummy common, harga 0
    "𓆝 Small Fish": 128.00,       # harga 1
    "🐌 Snail": 120.00,             # harga 2
    "🐚 Hermit Crab": 120.00,       # harga 2
    "🦀 Crab": 120.00,              # harga 2
    "🐸 Frog": 120.00,              # harga 2
    "🐍 Snake": 120.00,             # harga 2
    "🐙 Octopus": 100.00,           # harga 3
    "ଳ Jelly Fish": 80.00,          # harga 4
    "🦪 Giant Clam": 80.00,         # harga 4
    "🐟 Goldfish": 80.00,           # harga 4
    "🐟 Stingrays Fish": 80.00,     # harga 4
    "🐟 Clownfish": 80.00,          # harga 4
    "🐟 Doryfish": 80.00,           # harga 4
    "🐟 Bannerfish": 80.00,         # harga 4
    "🐟 Moorish Idol": 80.00,       # harga 4
    "🐟 Axolotl": 80.00,            # harga 4
    "🐟 Beta Fish": 80.00,          # harga 4
    "🐟 Anglerfish": 80.00,         # harga 4
    "🦆 Duck": 80.00,               # harga 4
    "🐡 Pufferfish": 70.00,         # harga 5
    "📿 Lucky Jewel": 60.00,        # harga 7
    "🐱 Red Hammer Cat": 10.00,     # harga 8
    "🐱 Purple Fist Cat": 10.00,    # harga 8
    "🐱 Green Dino Cat": 10.00,     # harga 8
    "🐱 White Winter Cat": 10.00,   # harga 8
    "🐟 Shark": 40.00,              # harga 10
    "🐟 Seahorse": 40.00,           # harga 10
    "🐊 Crocodile": 40.00,          # harga 10
    "🦦 Seal": 40.00,               # harga 10
    "🐢 Turtle": 40.00,             # harga 10
    "🦞 Lobster": 40.00,            # harga 10
    "🐋 Orca": 30.00,               # harga 15
    "🐬 Dolphin": 30.00,            # harga 15
    "🐹⚡ Pikachu": 5.00,           # harga 30
    "🐸🍀 Bulbasaur": 5.00,         # harga 30
    "🐢💧 Squirtle": 5.00,          # harga 30
    "🐉🔥 Charmander": 5.00,        # harga 30
    "🐋⚡ Kyogre": 5.00,             # harga 30
    "🐉 Baby Dragon": 0.10,         # harga 100
    "🐉 Baby Spirit Dragon": 0.10,  # harga 100
    "🐉 Baby Magma Dragon": 0.10,   # harga 100
    "🐉 Skull Dragon": 0.09,        # harga 200
    "🐉 Blue Dragon": 0.09,         # harga 200
    "🐉 Black Dragon": 0.09,        # harga 200
    "🐉 Yellow Dragon": 0.09,       # harga 200
    "🧜‍♀️ Mermaid Boy": 0.09,       # harga 200
    "🧜‍♀️ Mermaid Girl": 0.09,      # harga 200
    "🐉 Cupid Dragon": 0.01,        # harga 300
    "🐺 Werewolf": 0.009,           # harga 300
    "👹 Dark Lord Demon": 0.001     # harga 500
}

# Hitung total drop rate
_total = sum(FISH_LOOT.values())
logger.info(f"[INIT] Total drop rate: {_total:.2f}% (Target: ~1000%)")

# ---------------- BUFF RATE ---------------- #
BUFF_RATE = {
    "COMMON": 0.0,
    "RARE": 1.50,
    "LEGEND": 5.00,
    "MYTHIC": 10.00
}

# ---------------- FISHING FUNCTION ---------------- #
async def fishing_loot(client: Client, target_chat: int, username: str, user_id: int, umpan_type: str = "COMMON") -> str:
    buff = BUFF_RATE.get(umpan_type, 0.0)
    loot_item = roll_loot(buff, umpan_type)
    
    logger.info(f"[FISHING] {username} ({user_id}) memancing dengan {umpan_type}, mendapatkan: {loot_item}")
    
    try:
        await asyncio.sleep(2)  # delay animasi
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

    # Filter item sesuai level umpan
    exclude_for_rare = ["🤧 Zonk", "𓆝 Small Fish", "🐚 Hermit Crab"]
    exclude_for_legend = exclude_for_rare + ["🐸 Frog", "🐙 Octopus", "🐍 Snake"]
    exclude_for_mythic = exclude_for_legend + [
        "🐡 Pufferfish", "ଳ Jelly Fish", "📿 Lucky Jewel", "🐟 Goldfish",
        "🐟 Stingrays Fish", "🐟 Seahorse", "🐟 Clownfish", "🐟 Doryfish",
        "🐟 Bannerfish", "🐟 Anglerfish", "🦪 Giant Clam"
    ]

    for item, base_chance in FISH_LOOT.items():
        if umpan_type == "RARE" and item in exclude_for_rare:
            continue
        elif umpan_type == "LEGEND" and item in exclude_for_legend:
            continue
        elif umpan_type == "MYTHIC" and item in exclude_for_mythic:
            continue

        items.append(item)
        if item == "🤧 Zonk":
            chances.append(base_chance)
        else:
            chances.append(base_chance + buff)

    loot_item = random.choices(items, weights=chances, k=1)[0]
    return loot_item

# ---------------- WORKER ---------------- #
async def fishing_worker(app: Client):
    logger.info("[FISHING WORKER] Worker siap berjalan...")
    while True:
        logger.debug("[FISHING WORKER] Tick... tidak ada aksi saat ini")
        await asyncio.sleep(60)
