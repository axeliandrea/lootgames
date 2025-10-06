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
    # Common
    "🤧 Zonk": 100.00,  # 10%
    "𓆝 Small Fish": 207.87,
    "🐚 Hermit Crab": 141.48,
    "🐸 Frog": 137.35,
    "🐍 Snake": 135.60,
    "🐙 Octopus": 47.70,

    # Rare (total +100 point dibagi rata)
    "🐡 Pufferfish": 19.09,
    "ଳ Jelly Fish": 19.09,
    "📿 Lucky Jewel": 12.09,
    "🐟 Goldfish": 12.09,
    "🐟 Stingrays Fish": 12.09,
    "🐟 Seahorse": 12.09,
    "🐟 Clownfish": 12.09,
    "🐟 Doryfish": 12.09,
    "🐟 Bannerfish": 12.09,
    "🐟 Anglerfish": 12.09,
    "🦪 Giant Clam": 12.09,

    # Ultra Rare (total 120 dibagi rata 18 item ≈ 6.66%)
    "🐟 Beta Fish": 6.66,
    "🐟 Moorish Idol": 6.66,
    "🐟 Axolotl": 6.66,
    "🦆 Duck": 6.66,
    "🦀 Crab": 6.66,
    "🐟 Shark": 6.66,
    "🐊 Crocodile": 6.66,
    "🦦 Seal": 6.66,
    "🐢 Turtle": 6.66,
    "🦞 Lobster": 6.66,
    "🐹⚡ Pikachu": 6.66,
    "🐸🍀 Bulbasaur": 6.66,
    "🐢💧 Squirtle": 6.66,
    "🐉🔥 Charmander": 6.66,
    "🐋⚡ Kyogre": 6.66,
    "🐋 Orca": 6.66,
    "🐋 Dolphin": 6.66,
    "Lost cip": 6.66,

    # Mythic
    "🐉 Baby Dragon": 0.10,
    "🐉 Baby Spirit Dragon": 0.10,
    "🐉 Baby Magma Dragon": 0.10,
    "🐉 Skull Dragon": 0.01,
    "🐉 Blue Dragon": 0.01,
    "🐉 Black Dragon": 0.01,
    "🐉 Yellow Dragon": 0.01,
    "🧜‍♀️ Mermaid Boy": 0.01,
    "🧜‍♀️ Mermaid Girl": 0.01,
    "🐉 Cupid Dragon": 0.01,
    "🐺 Werewolf": 0.001,
}

# Hitung total drop rate
_total = sum(FISH_LOOT.values())
logger.info(f"[INIT] Total drop rate: {_total:.2f}% (Target: ~1000%)")

# ---------------- BUFF RATE ---------------- #
BUFF_RATE = {
    "COMMON": 0.0,
    "RARE": 2.50,
    "LEGEND": 2.00,
    "MYTHIC": 5.00
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
