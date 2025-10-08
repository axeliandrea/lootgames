import random
import asyncio
import logging
from pyrogram import Client
from lootgames.modules.fishing_helper import send_single_emoji, FISHING_EMOJI
from lootgames.modules import aquarium, umpan

logger = logging.getLogger(__name__)

# ============================================================
# 🎣 LOOT TABLE: Umpan Common Type A (Buff 0%)
# ============================================================
FISH_LOOT_COMMON = {
    # ---------------- COMMON ---------------- #
    "🤧 Zonk": 77.91,
    "𓆝 Small Fish": 131.52,
    "🐌 Snail": 78.27,
    "🐚 Hermit Crab": 78.27,
    "🦀 Crab": 73.78,
    "🐸 Frog": 73.78,
    "🐍 Snake": 74.68,
    "🐙 Octopus": 48.12,
    "ଳ Jelly Fish": 22.91,
    "🦪 Giant Clam": 22.91,
    "🐟 Goldfish": 22.91,
    "🐟 Stingrays Fish": 22.91,
    "🐟 Clownfish": 22.91,
    "🐟 Doryfish": 22.91,
    "🐟 Bannerfish": 22.91,
    "🐟 Moorish Idol": 22.91,
    "🐟 Axolotl": 22.91,
    "🐟 Beta Fish": 22.91,
    "🐟 Anglerfish": 22.91,
    "🦆 Duck": 22.91,

    # ---------------- MYTHIC ---------------- #
    "🐉 Baby Dragon": 0.5,
    "🐉 Baby Spirit Dragon": 0.5,
    "🐉 Baby Magma Dragon": 0.5,
    "🐉 Skull Dragon": 0.5,
    "🐉 Blue Dragon": 0.5,
    "🐉 Black Dragon": 0.5,
    "🐉 Yellow Dragon": 0.5,
    "🧜‍♀️ Mermaid Boy": 0.5,
    "🧜‍♀️ Mermaid Girl": 0.5,

    # ---------------- ULTRA MYTHIC ---------------- #
    "🐉 Cupid Dragon": 0.1,
    "🐺 Werewolf": 0.1,
    "🐱 Rainbow Angel Cat": 0.1,
    "👹 Dark Lord Demon": 0.1,
    "🦊 Princess of Nine Tail": 0.1,
    "🐦‍🔥 Fire Phoenix": 0.1,
    "🐦❄️ Frost Phoenix": 0.1,
    "🐦🌌 Dark Phoenix": 0.1,
}

# ============================================================
# 🎣 LOOT TABLE: Umpan Rare Type B (Drop Rate Lebih Bagus)
# ============================================================
FISH_LOOT_RARE = {
    # ---------------- ULTRA RARE ---------------- #
    "🐡 Pufferfish": 62.75,
    "📿 Lucky Jewel": 62.75,
    "🐱 Red Hammer Cat": 62.75,
    "🐱 Purple Fist Cat": 62.75,
    "🐱 Green Dino Cat": 62.75,
    "🐱 White Winter Cat": 62.75,
    "🐟 Shark": 62.75,
    "🐟 Seahorse": 62.75,
    "🐊 Crocodile": 62.75,
    "🦦 Seal": 62.75,
    "🐢 Turtle": 62.75,
    "🦞 Lobster": 62.75,

    # ---------------- LEGENDARY ---------------- #
    "🐋 Orca": 20.00,
    "🐬 Dolphin": 20.00,
    "🐒 Monkey": 20.00,
    "🦍 Gorilla": 20.00,
    "🐼 Panda": 20.00,
    "🐶 Dog": 20.00,
    "🐹⚡ Pikachu": 5.00,
    "🐸🍀 Bulbasaur": 5.00,
    "🐢💧 Squirtle": 5.00,
    "🐉🔥 Charmander": 5.00,
    "🐋⚡ Kyogre": 5.00,

    # ---------------- MYTHIC ---------------- #
    "🐉 Baby Dragon": 2.10,
    "🐉 Baby Spirit Dragon": 2.10,
    "🐉 Baby Magma Dragon": 2.10,
    "🐉 Skull Dragon": 2.10,
    "🐉 Blue Dragon": 2.10,
    "🐉 Black Dragon": 2.10,
    "🐉 Yellow Dragon": 2.10,
    "🧜‍♀️ Mermaid Boy": 2.10,
    "🧜‍♀️ Mermaid Girl": 2.10,

    # ---------------- ULTRA MYTHIC ---------------- #
    "🐉 Cupid Dragon": 1.01,
    "🐺 Werewolf": 1.01,
    "🐱 Rainbow Angel Cat": 1.01,
    "👹 Dark Lord Demon": 1.01,
    "🦊 Princess of Nine Tail": 1.01,
    "🐦‍🔥 Fire Phoenix": 1.01,
    "🐦❄️ Frost Phoenix": 1.01,
    "🐦🌌 Dark Phoenix": 1.01,
}

# ============================================================
# 🔧 SCALE MASING-MASING TABEL KE TOTAL 2000%
# ============================================================
def scale_loot_table(table: dict, target: float = 2000.0) -> dict:
    total = sum(table.values())
    scale_factor = target / total
    return {k: round(v * scale_factor, 3) for k, v in table.items()}

FISH_LOOT_COMMON = scale_loot_table(FISH_LOOT_COMMON)
FISH_LOOT_RARE = scale_loot_table(FISH_LOOT_RARE)

logger.info(f"[FISH_LOOT] Common & Rare di-scale otomatis ke total 2000%")

# ============================================================
# 🎯 BUFF RATE PER JENIS UMPAN
# ============================================================
BUFF_RATE = {
    "COMMON": 0.0,
    "RARE": 1.50,
    "LEGEND": 7.00,
    "MYTHIC": 10.00,
}

# ============================================================
# 🎲 LIST ITEM MYTHIC & ULTRA MYTHIC
# ============================================================
mythic_items = [
    "🐉 Baby Dragon", "🐉 Baby Spirit Dragon", "🐉 Baby Magma Dragon",
    "🐉 Skull Dragon", "🐉 Blue Dragon", "🐉 Black Dragon",
    "🐉 Yellow Dragon", "🧜‍♀️ Mermaid Boy", "🧜‍♀️ Mermaid Girl",
]
ultra_mythic_items = [
    "🐉 Cupid Dragon", "👹 Dark Lord Demon", "🦊 Princess of Nine Tail",
    "🐱 Rainbow Angel Cat", "🐦‍🔥 Fire Phoenix",
    "🐦❄️ Frost Phoenix", "🐦🌌 Dark Phoenix",
]

# ============================================================
# 🎲 PROSES RANDOM LOOT (Beda Table per Umpan)
# ============================================================
def roll_loot(buff: float, umpan_type: str = "COMMON") -> str:
    if umpan_type == "RARE":
        loot_table = FISH_LOOT_RARE
    else:
        loot_table = FISH_LOOT_COMMON

    items = list(loot_table.keys())
    chances = [v + buff for v in loot_table.values()]
    return random.choices(items, weights=chances, k=1)[0]

# ============================================================
# 🎣 FUNGSI MEMANCING
# ============================================================
async def fishing_loot(client: Client, target_chat: int, username: str, user_id: int, umpan_type: str = "COMMON") -> str:
    buff = BUFF_RATE.get(umpan_type, 0.0)
    loot_item = roll_loot(buff, umpan_type)

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
