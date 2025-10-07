# lootgames/modules/fishing_loot.py
import random
import asyncio
import logging
from pyrogram import Client
from lootgames.modules.fishing_helper import send_single_emoji, FISHING_EMOJI
from lootgames.modules import aquarium, umpan

logger = logging.getLogger(__name__)

# ============================================================
# 🎣 LOOT TABLE (TOTAL = 1000.00%)
# ============================================================
FISH_LOOT = {
    # COMMON
    "🤧 Zonk": 47.0, "𓆝 Small Fish": 82.0, "🐌 Snail": 33.0, "🐚 Hermit Crab": 33.0,
    "🦀 Crab": 33.0, "🐸 Frog": 33.0, "🐍 Snake": 33.0, "🐙 Octopus": 20.0,
    "ଳ Jelly Fish": 25.0, "🦪 Giant Clam": 25.0, "🐟 Goldfish": 25.0, "🐟 Stingrays Fish": 25.0,
    "🐟 Clownfish": 25.0, "🐟 Doryfish": 25.0, "🐟 Bannerfish": 25.0, "🐟 Moorish Idol": 25.0,
    "🐟 Axolotl": 25.0, "🐟 Beta Fish": 25.0, "🐟 Anglerfish": 25.0, "🦆 Duck": 25.0,

    # RARE & LEGENDARY
    "🐡 Pufferfish": 20.0, "📿 Lucky Jewel": 20.0, "🐱 Red Hammer Cat": 20.0,
    "🐱 Purple Fist Cat": 20.0, "🐱 Green Dino Cat": 20.0, "🐱 White Winter Cat": 20.0,
    "🐟 Shark": 20.0, "🐟 Seahorse": 20.0, "🐊 Crocodile": 20.0, "🦦 Seal": 20.0,
    "🐢 Turtle": 20.0, "🦞 Lobster": 20.0, "🐋 Orca": 13.0, "🐬 Dolphin": 13.0,
    "🐒 Monkey": 13.0, "🦍 Gorilla": 13.0, "🐼 Panda": 13.0, "🐶 Dog": 13.0,
    "🐹⚡ Pikachu": 13.0, "🐸🍀 Bulbasaur": 13.0, "🐢💧 Squirtle": 13.0,
    "🐉🔥 Charmander": 13.0, "🐋⚡ Kyogre": 13.0,

    # MYTHIC
    "🐉 Baby Dragon": 1.0, "🐉 Baby Spirit Dragon": 1.0, "🐉 Baby Magma Dragon": 1.0,
    "🐉 Skull Dragon": 0.5, "🐉 Blue Dragon": 0.5, "🐉 Black Dragon": 0.5,
    "🐉 Yellow Dragon": 0.5, "🧜‍♀️ Mermaid Boy": 0.42, "🧜‍♀️ Mermaid Girl": 0.42,

    # ULTRA MYTHIC
    "🐉 Cupid Dragon": 0.05, "🐺 Werewolf": 0.02, "🐱 Rainbow Angel Cat": 0.03,
    "👹 Dark Lord Demon": 0.02, "🦊 Princess of Nine Tail": 0.02,
    "🐦‍🔥 Fire Phoenix": 0.02, "🐦❄️ Frost Phoenix": 0.02, "🐦🌌 Dark Phoenix": 0.02,
}

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
# 🎣 LIST ITEM PER KATEGORI
# ============================================================
ultra_mythic_items = [
    "🐺 Werewolf", "🐱 Rainbow Angel Cat", "👹 Dark Lord Demon",
    "🦊 Princess of Nine Tail", "🐦‍🔥 Fire Phoenix", "🐦❄️ Frost Phoenix", "🐦🌌 Dark Phoenix"
]

mythic_items = [
    "🐉 Baby Dragon", "🐉 Baby Spirit Dragon", "🐉 Baby Magma Dragon",
    "🐉 Skull Dragon", "🐉 Blue Dragon", "🐉 Black Dragon",
    "🐉 Yellow Dragon", "🧜‍♀️ Mermaid Boy", "🧜‍♀️ Mermaid Girl", "🐉 Cupid Dragon"
]

common_items = [
    item for item in FISH_LOOT
    if FISH_LOOT[item] >= 20 and item not in mythic_items + ultra_mythic_items
]

rare_items = [
    item for item in FISH_LOOT
    if item not in common_items + mythic_items + ultra_mythic_items
]

# ============================================================
# 🎣 FUNGSI MEMANCING
# ============================================================
async def fishing_loot(client: Client, target_chat: int, username: str, user_id: int, umpan_type: str = "COMMON") -> str:
    buff = BUFF_RATE.get(umpan_type, 0.0)
    loot_item = roll_loot(buff)
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
# 🎲 RANDOM LOOT PROCESS
# ============================================================
def roll_loot(buff: float = 0.0) -> str:
    roll = random.uniform(0, 100)
    # Check Ultra Mythic
    for item in ultra_mythic_items:
        if roll <= FISH_LOOT[item] + buff:
            return item
    # Check Mythic
    for item in mythic_items:
        if roll <= FISH_LOOT[item] + buff:
            return item
    # Check Rare
    for item in rare_items:
        if roll <= FISH_LOOT[item] + buff:
            return item
    # Check Common
    for item in common_items:
        if roll <= FISH_LOOT[item] + buff:
            return item
    # fallback
    return random.choice(common_items)
