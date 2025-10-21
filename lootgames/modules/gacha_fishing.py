import random
import asyncio
import logging
from pyrogram import Client
from lootgames.modules import aquarium

logger = logging.getLogger(__name__)

# ============================================================
# 🎣 LOOT TABLES
# ============================================================

# ---------------- COMMON ---------------- #
FISH_LOOT_COMMON = {
    # monster besar (sudah dikurangi proporsional)
    "🤧 Zonk": 43.18,
    "𓆝 Small Fish": 61.75,
    "🐌 Snail": 48.10,
    "🐚 Hermit Crab": 50.90,
    "🦀 Crab": 46.71,
    "🐸 Frog": 46.71,
    "🐍 Snake": 46.65,
    "🐙 Octopus": 29.77,

    # item kecil — lebih besar dari element
    "ଳ Jelly Fish": 40.00,
    "🦪 Giant Clam": 40.00,
    "🐟 Goldfish": 40.00,
    "🐟 Stingrays Fish": 40.00,
    "🐟 Clownfish": 40.00,
    "🐟 Doryfish": 40.00,
    "🐟 Bannerfish": 40.00,
    "🐟 Moorish Idol": 40.00,
    "🐟 Axolotl": 40.00,
    "🐟 Beta Fish": 40.00,
    "🐟 Anglerfish": 40.00,
    "🦆 Duck": 40.00,

    # kecil tetap
    "🧬 Mysterious DNA": 15.00,

    # ✨ ELEMENT MONSTERS ✨
    "✨ Thunder Element": 30.00,
    "✨ Fire Element": 30.00,
    "✨ Water Element": 30.00,
    "✨ Wind Element": 30.00,
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
# 🔧 SCALE KE TOTAL 2000.00%
# ============================================================
def scale_loot_table(table: dict, target: float = 2000.0) -> dict:
    total = sum(table.values())
    if total == 0:
        return table
    scale_factor = target / total
    scaled = {k: round(v * scale_factor, 3) for k, v in table.items()}
    logger.info(f"[SCALE] {len(table)} items di-scale → {sum(scaled.values()):.2f}% total (factor={scale_factor:.3f})")
    return scaled

FISH_LOOT_COMMON = scale_loot_table(FISH_LOOT_COMMON)
FISH_LOOT_RARE = scale_loot_table(FISH_LOOT_RARE)

# ============================================================
# 🎯 BUFF RATE PER TIER
# ============================================================
BUFF_RATE = {
    "ULTRA_RARE": 10.0,
    "LEGEND": 20.0,
    "MYTHIC": 5.1,
    "ULTRA_MYTHIC": 1.05,
    "COMMON": 0.0,
}

# ============================================================
# 🎲 RANDOM LOOT
# ============================================================
def roll_loot(umpan_type: str = "COMMON") -> str:
    """Random loot sesuai jenis umpan."""
    if umpan_type == "RARE":
        loot_table = FISH_LOOT_RARE
        weighted = []

        for item, base in loot_table.items():
            if item in ["🐡 Pufferfish","📿 Lucky Jewel","🐱 Red Hammer Cat","🐱 Purple Fist Cat","🐱 Green Dino Cat",
                        "🐱 White Winter Cat","🐟 Shark","🐟 Seahorse","🐊 Crocodile","🦦 Seal","🐢 Turtle","🦞 Lobster"]:
                tier = "ULTRA_RARE"
            elif item in ["🐋 Orca","🐬 Dolphin","🐒 Monkey","🦍 Gorilla","🐼 Panda","🐶 Dog","🦇 bat",
                          "🐹⚡ Pikachu","🐸🍀 Bulbasaur","🐢💧 Squirtle","🐉🔥 Charmander","🐋⚡ Kyogre"]:
                tier = "LEGEND"
            elif item in ["🐉 Baby Dragon","🐉 Baby Spirit Dragon","🐉 Baby Magma Dragon","🐉 Skull Dragon",
                          "🐉 Blue Dragon","🐉 Black Dragon","🐉 Yellow Dragon","🧜‍♀️ Mermaid Boy","🧜‍♀️ Mermaid Girl"]:
                tier = "MYTHIC"
            elif item in ["🐉 Cupid Dragon","🐉 Dark Knight Dragon","🐯 White Tiger","🐺 Werewolf","🐱 Rainbow Angel Cat",
                          "👹 Dark Lord Demon","🦊 Princess of Nine Tail","🐦‍🔥 Fire Phoenix","🐦❄️ Frost Phoenix","🐦🌌 Dark Phoenix"]:
                tier = "ULTRA_MYTHIC"
            else:
                tier = "COMMON"

            weighted.append(base + BUFF_RATE[tier])

        return random.choices(list(loot_table.keys()), weights=weighted, k=1)[0]

    # COMMON
    items = list(FISH_LOOT_COMMON.keys())
    weights = list(FISH_LOOT_COMMON.values())
    return random.choices(items, weights=weights, k=1)[0]

# ============================================================
# 🎣 MEMANCING
# ============================================================
async def fishing_loot(client: Client, target_chat: int, username: str, user_id: int, umpan_type: str = "COMMON") -> str:
    loot = roll_loot(umpan_type)
    logger.info(f"[FISHING] @{username} ({user_id}) pakai {umpan_type} → {loot}")

    try:
        await asyncio.sleep(2)
        if target_chat:
            await client.send_message(target_chat, f"🎣 @{username} mendapatkan {loot}!")
        aquarium.add_fish(user_id, loot, 1)
    except Exception as e:
        logger.error(f"[FISHING ERROR] {e}")

    return loot

# ============================================================
# 🧠 BACKGROUND WORKER
# ============================================================
async def fishing_worker(app: Client):
    logger.info("[FISHING WORKER] Worker aktif ✅")
    while True:
        logger.debug("[FISHING WORKER] Tick... idle.")
        await asyncio.sleep(60)
