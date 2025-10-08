import random
import asyncio
import logging
from pyrogram import Client
from lootgames.modules.fishing_helper import send_single_emoji, FISHING_EMOJI
from lootgames.modules import aquarium, umpan

logger = logging.getLogger(__name__)

# ============================================================
# 🎣 LOOT TABLE (URUT HARGA)
# ============================================================
FISH_LOOT = {
    # ---------------- COMMON ---------------- #
    "🤧 Zonk": 170.00,
    "𓆝 Small Fish": 288.00,
    "🐌 Snail": 171.00,
    "🐚 Hermit Crab": 171.00,
    "🦀 Crab": 161.00,
    "🐸 Frog": 161.00,
    "🐍 Snake": 163.00,
    "🐙 Octopus": 105.00,
    "ଳ Jelly Fish": 50.00,
    "🦪 Giant Clam": 50.00,
    "🐟 Goldfish": 50.00,
    "🐟 Stingrays Fish": 50.00,
    "🐟 Clownfish": 50.00,
    "🐟 Doryfish": 50.00,
    "🐟 Bannerfish": 50.00,
    "🐟 Moorish Idol": 50.00,
    "🐟 Axolotl": 50.00,
    "🐟 Beta Fish": 50.00,
    "🐟 Anglerfish": 50.00,
    "🦆 Duck": 50.00,

    # ---------------- ULTRA RARE ---------------- #
    "🐡 Pufferfish": 40.00,
    "📿 Lucky Jewel": 40.00,
    "🐱 Red Hammer Cat": 10.00,
    "🐱 Purple Fist Cat": 10.00,
    "🐱 Green Dino Cat": 10.00,
    "🐱 White Winter Cat": 10.00,
    "🐟 Shark": 40.00,
    "🐟 Seahorse": 40.00,
    "🐊 Crocodile": 40.00,
    "🦦 Seal": 40.00,
    "🐢 Turtle": 40.00,
    "🦞 Lobster": 40.00,

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
    "🐉 Baby Dragon": 0.10,
    "🐉 Baby Spirit Dragon": 0.10,
    "🐉 Baby Magma Dragon": 0.10,
    "🐉 Skull Dragon": 0.09,
    "🐉 Blue Dragon": 0.09,
    "🐉 Black Dragon": 0.09,
    "🐉 Yellow Dragon": 0.09,
    "🧜‍♀️ Mermaid Boy": 0.09,
    "🧜‍♀️ Mermaid Girl": 0.09,

    # ---------------- ULTRA MYTHIC ---------------- #
    "🐉 Cupid Dragon": 0.01,
    "🐺 Werewolf": 0.001,
    "🐱 Rainbow Angel Cat": 0.001,
    "👹 Dark Lord Demon": 0.001,
    "🦊 Princess of Nine Tail": 0.001,
    "🐦‍🔥 Fire Phoenix": 0.001,
    "🐦❄️ Frost Phoenix": 0.001,
    "🐦🌌 Dark Phoenix": 0.001
}

# ============================================================
# 🔧 AUTO SCALE KE TOTAL 2000%
# ============================================================
TOTAL_TARGET = 2000.0
current_total = sum(FISH_LOOT.values())
scale_factor = TOTAL_TARGET / current_total
for k in FISH_LOOT:
    FISH_LOOT[k] = round(FISH_LOOT[k] * scale_factor, 3)

logger.info(f"[FISH_LOOT] Total bobot otomatis di-scale ke {TOTAL_TARGET}%")

# ============================================================
# 🎯 BUFF RATE PER JENIS UMPAN
# ============================================================
BUFF_RATE = {
    "COMMON": 0.0,
    "RARE": 1.50,
    "LEGEND": 7.00,
    "MYTHIC": 10.00
}

# ============================================================
# 🎲 LIST ITEM MYTHIC & ULTRA MYTHIC
# ============================================================
mythic_items = [
    "🐉 Baby Dragon", "🐉 Baby Spirit Dragon", "🐉 Baby Magma Dragon",
    "🐉 Skull Dragon", "🐉 Blue Dragon", "🐉 Black Dragon",
    "🐉 Yellow Dragon", "🧜‍♀️ Mermaid Boy", "🧜‍♀️ Mermaid Girl",
    "🐉 Cupid Dragon"
]

ultra_mythic_items = [
    "👹 Dark Lord Demon", "🦊 Princess of Nine Tail", "🐱 Rainbow Angel Cat",
    "🐦‍🔥 Fire Phoenix", "🐦❄️ Frost Phoenix", "🐦🌌 Dark Phoenix"
]

# ============================================================
# 🎲 PROSES RANDOM LOOT
# ============================================================
def roll_loot(buff: float, umpan_type: str = "COMMON") -> str:
    items, chances = [], []

    for item, base_chance in FISH_LOOT.items():
        bonus = 0.0

        # ==================== LOGIKA RARE ====================
        if umpan_type == "RARE":
            # COMMON items tidak boleh masuk
            if item not in mythic_items and item not in ultra_mythic_items and base_chance > 50.0:
                continue
            if item in mythic_items:
                bonus = 1.50
            elif item in ultra_mythic_items:
                bonus = 0.10
            else:
                bonus = buff

        # ==================== LEGEND ====================
        elif umpan_type == "LEGEND":
            if item in mythic_items:
                bonus = 4.0
            elif item in ultra_mythic_items:
                bonus = 1.5
            else:
                bonus = buff

        # ==================== COMMON ====================
        elif umpan_type == "COMMON":
            if item in mythic_items:
                bonus = 0.09
            elif item in ultra_mythic_items:
                bonus = 0.01
            else:
                bonus = buff
        else:
            bonus = buff

        items.append(item)
        chances.append(base_chance + bonus)

    loot_item = random.choices(items, weights=chances, k=1)[0]
    return loot_item

# ============================================================
# 🎣 FUNGSI MEMANCING
# ============================================================
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

# ============================================================
# 🧠 BACKGROUND WORKER
# ============================================================
async def fishing_worker(app: Client):
    logger.info("[FISHING WORKER] Worker siap berjalan...")
    while True:
        logger.debug("[FISHING WORKER] Tick... tidak ada aksi saat ini")
        await asyncio.sleep(60)
