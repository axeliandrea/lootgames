# lootgames/modules/fishing_loot.py
import random
import asyncio
import logging
from pyrogram import Client
from lootgames.modules.fishing_helper import send_single_emoji, FISHING_EMOJI
from lootgames.modules import aquarium, umpan

logger = logging.getLogger(__name__)

# ============================================================
# 🎣 LOOT TABLE (TOTAL ≈1000.00%)
# ============================================================
FISH_LOOT = {
    # ---------------- COMMON (Monster 1–19) ---------------- #
    "🤧 Zonk": 50.00,                 # harga 0
    "𓆝 Small Fish": 168.00,          # harga 1 — Monster 1
    "🐌 Snail": 148.00,               # harga 2 — Monster 2
    "🐚 Hermit Crab": 148.00,         # harga 2 — Monster 3
    "🦀 Crab": 138.00,                # harga 2 — Monster 4
    "🐸 Frog": 138.00,                # harga 2 — Monster 5
    "🐍 Snake": 138.00,               # harga 2 — Monster 6
    "🐙 Octopus": 110.00,             # harga 3 — Monster 7
    "ଳ Jelly Fish": 70.00,            # harga 4 — Monster 8
    "🦪 Giant Clam": 70.00,           # harga 4 — Monster 9
    "🐟 Goldfish": 70.00,             # harga 4 — Monster 10
    "🐟 Stingrays Fish": 70.00,       # harga 4 — Monster 11
    "🐟 Clownfish": 70.00,            # harga 4 — Monster 12
    "🐟 Doryfish": 70.00,             # harga 4 — Monster 13
    "🐟 Bannerfish": 70.00,           # harga 4 — Monster 14
    "🐟 Moorish Idol": 70.00,         # harga 4 — Monster 15
    "🐟 Axolotl": 70.00,              # harga 4 — Monster 16
    "🐟 Beta Fish": 70.00,            # harga 4 — Monster 17
    "🐟 Anglerfish": 70.00,           # harga 4 — Monster 18
    "🦆 Duck": 70.00,                 # harga 4 — Monster 19

    # ---------------- ULTRA RARE (Monster 20–32) ---------------- #
    "🐡 Pufferfish": 50.00,           # harga 5 — Monster 20
    "📿 Lucky Jewel": 50.00,          # harga 7 — Monster 21
    "🐱 Red Hammer Cat": 10.00,       # harga 8 — Monster 22
    "🐱 Purple Fist Cat": 10.00,      # harga 8 — Monster 23
    "🐱 Green Dino Cat": 10.00,       # harga 8 — Monster 24
    "🐱 White Winter Cat": 10.00,     # harga 8 — Monster 25
    "🐟 Shark": 30.00,                # harga 10 — Monster 26
    "🐟 Seahorse": 30.00,             # harga 10 — Monster 27
    "🐊 Crocodile": 30.00,            # harga 10 — Monster 28
    "🦦 Seal": 30.00,                 # harga 10 — Monster 29
    "🐢 Turtle": 30.00,               # harga 10 — Monster 30
    "🦞 Lobster": 30.00,              # harga 10 — Monster 31

    # ---------------- LEGENDARY (Monster 32–41) ---------------- #
    "🐋 Orca": 30.00,                 # harga 15 — Monster 32
    "🐬 Dolphin": 30.00,              # harga 15 — Monster 33
    "🐒 Monkey": 30.00,               # harga 15 — Monster 34
    "🦍 Gorilla": 30.00,              # harga 15 — Monster 35
    "🐼 Panda" : 30.00,                # harga 15 — Monster 36
    "🐹⚡ Pikachu": 5.00,             # harga 30 — Monster 37
    "🐸🍀 Bulbasaur": 5.00,           # harga 30 — Monster 38
    "🐢💧 Squirtle": 5.00,            # harga 30 — Monster 39
    "🐉🔥 Charmander": 5.00,          # harga 30 — Monster 40
    "🐋⚡ Kyogre": 5.00,              # harga 30 — Monster 41

    # ---------------- MYTHIC (Monster 41–54) ---------------- #
    "🐉 Baby Dragon": 0.10,           # harga 50 — Monster 42
    "🐉 Baby Spirit Dragon": 0.10,    # harga 50 — Monster 43
    "🐉 Baby Magma Dragon": 0.10,     # harga 50 — Monster 44
    "🐉 Skull Dragon": 0.09,          # harga 55 — Monster 45
    "🐉 Blue Dragon": 0.09,           # harga 55 — Monster 46
    "🐉 Black Dragon": 0.09,          # harga 55 — Monster 47
    "🐉 Yellow Dragon": 0.09,         # harga 55 — Monster 48
    "🧜‍♀️ Mermaid Boy": 0.09,         # harga 60 — Monster 49
    "🧜‍♀️ Mermaid Girl": 0.09,        # harga 60 — Monster 50
    "🐉 Cupid Dragon": 0.01,          # harga 70 — Monster 51
    "🐺 Werewolf": 0.001,             # harga 100 — Monster 52
    "🐱 Rainbow Angel Cat": 0.001,    # harga 120 — Monster 53
    "👹 Dark Lord Demon": 0.001,      # harga 150 — Monster 54
    "🦊 Princess of Nine Tail": 0.001 # harga 200 — Monster 55
}

# ============================================================
# 🎯 BUFF RATE PER JENIS UMPAN
# ============================================================
BUFF_RATE = {
    "COMMON": 0.0,
    "RARE": 30.50,
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

    # Batasi jenis ikan per tipe umpan
    if umpan_type == "COMMON":
        allowed = list(FISH_LOOT.keys())[:19]  # Monster 1–19
    elif umpan_type == "RARE":
        allowed = list(FISH_LOOT.keys())[19:]  # Monster 20 ke atas
    elif umpan_type == "LEGEND":
        allowed = list(FISH_LOOT.keys())[31:]  # Monster 32 ke atas
    elif umpan_type == "MYTHIC":
        allowed = list(FISH_LOOT.keys())[-14:]  # Khusus Mythic
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
                bonus = 30.0
            elif item in ultra_mythic_items:
                bonus = 1.5
            else:
                bonus = buff
        elif umpan_type == "LEGEND":
            if item in mythic_items:
                bonus = 4.0
            elif item in ultra_mythic_items:
                bonus = 7.0
            else:
                bonus = buff
        else:
            bonus = buff if item != "🤧 Zonk" else 0

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
