# lootgames/modules/fishing_loot.py
import random
import asyncio
import logging
from pyrogram import Client
from lootgames.modules.fishing_helper import send_single_emoji, FISHING_EMOJI
from lootgames.modules import aquarium, umpan

logger = logging.getLogger(__name__)

# ============================================================
# 🎣 LOOT TABLE (TOTAL ≈1000.00%, urut harga)
# ============================================================
FISH_LOOT = {
    # ---------------- COMMON (harga 0–4) ---------------- #
    "🤧 Zonk": 50.00,                  # 5.00%
    "𓆝 Small Fish": 168.00,          # 16.80%
    "🐌 Snail": 143.00,                # 14.30%
    "🐚 Hermit Crab": 143.00,          # 14.30%
    "🦀 Crab": 133.00,                 # 13.30%
    "🐸 Frog": 133.00,                 # 13.30%
    "🐍 Snake": 135.00,                # 13.50%
    "🐙 Octopus": 105.00,              # 10.50%
    "ଳ Jelly Fish": 70.00,             # 7.00%
    "🦪 Giant Clam": 70.00,            # 7.00%
    "🐟 Goldfish": 70.00,              # 7.00%
    "🐟 Stingrays Fish": 70.00,        # 7.00%
    "🐟 Clownfish": 70.00,             # 7.00%
    "🐟 Doryfish": 70.00,              # 7.00%
    "🐟 Bannerfish": 70.00,            # 7.00%
    "🐟 Moorish Idol": 70.00,          # 7.00%
    "🐟 Axolotl": 70.00,               # 7.00%
    "🐟 Beta Fish": 70.00,             # 7.00%
    "🐟 Anglerfish": 70.00,            # 7.00%
    "🦆 Duck": 70.00,                  # 7.00%

    # ---------------- ULTRA RARE (harga 5–10) ---------------- #
    "🐡 Pufferfish": 50.00,            # 5.00%
    "📿 Lucky Jewel": 50.00,           # 5.00%
    "🐱 Red Hammer Cat": 10.00,        # 1.00%
    "🐱 Purple Fist Cat": 10.00,       # 1.00%
    "🐱 Green Dino Cat": 10.00,        # 1.00%
    "🐱 White Winter Cat": 10.00,      # 1.00%
    "🐟 Shark": 30.00,                 # 3.00%
    "🐟 Seahorse": 30.00,              # 3.00%
    "🐊 Crocodile": 30.00,             # 3.00%
    "🦦 Seal": 30.00,                  # 3.00%
    "🐢 Turtle": 30.00,                # 3.00%
    "🦞 Lobster": 30.00,               # 3.00%

    # ---------------- LEGENDARY (harga 15–30) ---------------- #
    "🐋 Orca": 30.00,                   # 3.00%
    "🐬 Dolphin": 30.00,                # 3.00%
    "🐒 Monkey": 30.00,                 # 3.00%
    "🦍 Gorilla": 30.00,                # 3.00%
    "🐼 Panda": 30.00,                   # 3.00%
    "🐶 Dog": 30.00,                     # 3.00%
    "🐹⚡ Pikachu": 5.00,               # 0.50%
    "🐸🍀 Bulbasaur": 5.00,             # 0.50%
    "🐢💧 Squirtle": 5.00,              # 0.50%
    "🐉🔥 Charmander": 5.00,            # 0.50%
    "🐋⚡ Kyogre": 5.00,                 # 0.50%

    # ---------------- MYTHIC (harga 0,09–0,1) ---------------- #
    "🐉 Baby Dragon": 0.10,             # 0.01%
    "🐉 Baby Spirit Dragon": 0.10,      # 0.01%
    "🐉 Baby Magma Dragon": 0.10,       # 0.01%
    "🐉 Skull Dragon": 0.09,            # 0.009%
    "🐉 Blue Dragon": 0.09,             # 0.009%
    "🐉 Black Dragon": 0.09,            # 0.009%
    "🐉 Yellow Dragon": 0.09,           # 0.009%
    "🧜‍♀️ Mermaid Boy": 0.09,           # 0.009%
    "🧜‍♀️ Mermaid Girl": 0.09,          # 0.009%
    "🐉 Cupid Dragon": 0.01,            # 0.001%
    "🐺 Werewolf": 0.001,               # 0.0001%
    "🐱 Rainbow Angel Cat": 0.001,      # 0.0001%
    "👹 Dark Lord Demon": 0.001,        # 0.0001%
    "🦊 Princess of Nine Tail": 0.001   # 0.0001%
}

# ============================================================
# 🎯 BUFF RATE PER JENIS UMPAN
# ============================================================
BUFF_RATE = {
    "COMMON": 0.0,
    "RARE": 5.50,
    "LEGEND": 7.00,
    "MYTHIC": 10.00
}

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
# 🎲 PROSES RANDOM LOOT
# ============================================================
def roll_loot(buff: float, umpan_type: str = "COMMON") -> str:
    items = []
    chances = []

    if umpan_type == "COMMON":
        allowed = list(FISH_LOOT.keys())  # COMMON bisa dapat semua termasuk MYTHIC
    elif umpan_type == "RARE":
        allowed = list(FISH_LOOT.keys())[20:]  # mulai ULTRA RARE
    elif umpan_type == "LEGEND":
        allowed = list(FISH_LOOT.keys())[32:]  # mulai LEGEND
    elif umpan_type == "MYTHIC":
        allowed = list(FISH_LOOT.keys())[-14:]  # hanya MYTHIC
    else:
        allowed = list(FISH_LOOT.keys())

    mythic_items = [
        "🐉 Baby Dragon", "🐉 Baby Spirit Dragon", "🐉 Baby Magma Dragon",
        "🐉 Skull Dragon", "🐉 Blue Dragon", "🐉 Black Dragon",
        "🐉 Yellow Dragon", "🧜‍♀️ Mermaid Boy", "🧜‍♀️ Mermaid Girl",
        "🐉 Cupid Dragon"
    ]
    ultra_mythic_items = ["👹 Dark Lord Demon", "🦊 Princess of Nine Tail", "🐱 Rainbow Angel Cat"]

    for item, base_chance in FISH_LOOT.items():
        if item not in allowed:
            continue

        bonus = 0.0
        if umpan_type == "RARE":
            if item in mythic_items:
                bonus = 5.0
            elif item in ultra_mythic_items:
                bonus = 0.5
            else:
                bonus = buff
        elif umpan_type == "LEGEND":
            if item in mythic_items:
                bonus = 4.0
            elif item in ultra_mythic_items:
                bonus = 7.0
            else:
                bonus = buff
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
# 🧠 BACKGROUND WORKER
# ============================================================
async def fishing_worker(app: Client):
    logger.info("[FISHING WORKER] Worker siap berjalan...")
    while True:
        logger.debug("[FISHING WORKER] Tick... tidak ada aksi saat ini")
        await asyncio.sleep(60)
