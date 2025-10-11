import random
import asyncio
import logging
from pyrogram import Client
from lootgames.modules.fishing_helper import send_single_emoji, FISHING_EMOJI
from lootgames.modules import aquarium, umpan

logger = logging.getLogger(__name__)

# ============================================================
# 🎣 LOOT TABLES
# ============================================================

# ---------------- COMMON ---------------- #
FISH_LOOT_COMMON = {
    "🤧 Zonk": 94.91,
    "𓆝 Small Fish": 128.04,
    "🐌 Snail": 82.27,
    "🐚 Hermit Crab": 87.27,
    "🦀 Crab": 79.78,
    "🐸 Frog": 79.78,
    "🐍 Snake": 79.68,
    "🐙 Octopus": 53.12,
    "ଳ Jelly Fish": 24.91,
    "🦪 Giant Clam": 24.91,
    "🐟 Goldfish": 24.91,
    "🐟 Stingrays Fish": 24.91,
    "🐟 Clownfish": 24.91,
    "🐟 Doryfish": 24.91,
    "🐟 Bannerfish": 24.91,
    "🐟 Moorish Idol": 24.91,
    "🐟 Axolotl": 24.91,
    "🐟 Beta Fish": 24.91,
    "🐟 Anglerfish": 24.91,
    "🦆 Duck": 24.91,
    "🧬 Mysterious DNA": 5.00,
}

# ---------------- RARE ---------------- #
FISH_LOOT_RARE = {
    # Ultra Rare
    "🐡 Pufferfish": 67.62,
    "📿 Lucky Jewel": 63.66,
    "🐱 Red Hammer Cat": 63.66,
    "🐱 Purple Fist Cat": 63.66,
    "🐱 Green Dino Cat": 63.66,
    "🐱 White Winter Cat": 63.66,
    "🐟 Shark": 61.66,
    "🐟 Seahorse": 61.66,
    "🐊 Crocodile": 61.66,
    "🦦 Seal": 61.66,
    "🐢 Turtle": 65.66,
    "🦞 Lobster": 61.66,

    # Legendary
    "🐋 Orca": 20.39,
    "🐬 Dolphin": 20.39,
    "🐒 Monkey": 20.39,
    "🦍 Gorilla": 20.39,
    "🐼 Panda": 20.39,
    "🐶 Dog": 20.39,
    "🦇 bat": 20.39,
    "🧬 Mysterious DNA": 15.30,
    "🐹⚡ Pikachu": 5.10,
    "🐸🍀 Bulbasaur": 5.10,
    "🐢💧 Squirtle": 5.10,
    "🐉🔥 Charmander": 5.10,
    "🐋⚡ Kyogre": 5.10,

    # Mythic
    "🐉 Baby Dragon": 0.10,
    "🐉 Baby Spirit Dragon": 0.10,
    "🐉 Baby Magma Dragon": 0.10,
    "🐉 Skull Dragon": 0.10,
    "🐉 Blue Dragon": 0.10,
    "🐉 Black Dragon": 0.10,
    "🐉 Yellow Dragon": 0.10,
    "🧜‍♀️ Mermaid Boy": 0.10,
    "🧜‍♀️ Mermaid Girl": 0.10,

    # Ultra Mythic
    "🐉 Cupid Dragon": 0.01,
    "🐉 Dark Knight Dragon": 0.01,
    "🐯 White Tiger": 0.01,
    "🐺 Werewolf": 0.01,
    "🐱 Rainbow Angel Cat": 0.01,
    "👹 Dark Lord Demon": 0.01,
    "🦊 Princess of Nine Tail": 0.01,
    "🐦‍🔥 Fire Phoenix": 0.01,
    "🐦❄️ Frost Phoenix": 0.01,
    "🐦🌌 Dark Phoenix": 0.01,
}

# ============================================================
# 🔧 SCALE KE TOTAL 2000%
# ============================================================
def scale_loot_table(table: dict, target: float = 2000.0) -> dict:
    total = sum(table.values())
    scale_factor = target / total
    return {k: round(v * scale_factor, 3) for k, v in table.items()}

FISH_LOOT_COMMON = scale_loot_table(FISH_LOOT_COMMON)
FISH_LOOT_RARE = scale_loot_table(FISH_LOOT_RARE)

logger.info(f"[FISH_LOOT] Common & Rare di-scale otomatis ke total 2000%")

# ============================================================
# 🎯 BUFF RATE PER TIER (Hanya untuk Umpan RARE)
# ============================================================
BUFF_RATE = {
    "ULTRA_RARE": 10.0,
    "LEGEND": 20.0,
    "MYTHIC": 5.10,
    "ULTRA_MYTHIC": 1.05,
    "COMMON": 0.0,  # Tidak berlaku di rare table
}

# ============================================================
# 🎲 RANDOM LOOT
# ============================================================
def roll_loot(umpan_type: str = "COMMON") -> str:
    """Random loot sesuai umpan, COMMON atau RARE dengan buff tier"""
    if umpan_type == "RARE":
        loot_table = FISH_LOOT_RARE
        weighted_items = []
        for item, chance in loot_table.items():
            # Tentukan tier untuk buff
            if item in ["🐡 Pufferfish","📿 Lucky Jewel","🐱 Red Hammer Cat","🐱 Purple Fist Cat","🐱 Green Dino Cat",
                        "🐱 White Winter Cat","🐟 Shark","🐟 Seahorse","🐊 Crocodile","🦦 Seal","🐢 Turtle","🦞 Lobster"]:
                tier = "ULTRA_RARE"
            elif item in ["🐋 Orca","🐬 Dolphin","🐒 Monkey","🦍 Gorilla","🐼 Panda","🐶 Dog","🦇 bat","🐹⚡ Pikachu",
                          "🐸🍀 Bulbasaur","🐢💧 Squirtle","🐉🔥 Charmander","🐋⚡ Kyogre"]:
                tier = "LEGEND"
            elif item in ["🐉 Baby Dragon","🐉 Baby Spirit Dragon","🐉 Baby Magma Dragon","🐉 Skull Dragon","🐉 Blue Dragon",
                          "🐉 Black Dragon","🐉 Yellow Dragon","🧜‍♀️ Mermaid Boy","🧜‍♀️ Mermaid Girl"]:
                tier = "MYTHIC"
            elif item in ["🐉 Cupid Dragon","🐉 Dark Knight Dragon","🐯 White Tiger","🐺 Werewolf","🐱 Rainbow Angel Cat",
                          "👹 Dark Lord Demon","🦊 Princess of Nine Tail","🐦‍🔥 Fire Phoenix","🐦❄️ Frost Phoenix","🐦🌌 Dark Phoenix"]:
                tier = "ULTRA_MYTHIC"
            else:
                tier = "COMMON"  # Mysterious DNA

            weighted_items.append(chance + BUFF_RATE.get(tier,0))

        items = list(loot_table.keys())
        return random.choices(items, weights=weighted_items, k=1)[0]

    else:
        # COMMON tabel biasa
        items = list(FISH_LOOT_COMMON.keys())
        chances = list(FISH_LOOT_COMMON.values())
        return random.choices(items, weights=chances, k=1)[0]

# ============================================================
# 🎣 MEMANCING
# ============================================================
async def fishing_loot(client: Client, target_chat: int, username: str, user_id: int, umpan_type: str = "COMMON") -> str:
    loot_item = roll_loot(umpan_type)

    logger.info(f"[FISHING] @{username} ({user_id}) menggunakan {umpan_type}, hasil: {loot_item}")

    try:
        await asyncio.sleep(2)
        if target_chat:
            await client.send_message(target_chat, f"🎣 @{username} mendapatkan {loot_item}!")
        aquarium.add_fish(user_id, loot_item, 1)
    except Exception as e:
        logger.error(f"[FISHING] Error: {e}")

    return loot_item

# ============================================================
# 🧠 BACKGROUND WORKER
# ============================================================
async def fishing_worker(app: Client):
    logger.info("[FISHING WORKER] Worker aktif...")
    while True:
        logger.debug("[FISHING WORKER] Tick... idle.")
        await asyncio.sleep(60)
