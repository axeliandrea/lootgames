# lootgames/modules/fishing_loot.py
import random
import asyncio
import logging
from pyrogram import Client
from lootgames.modules.fishing_helper import send_single_emoji, FISHING_EMOJI
from lootgames.modules import aquarium, umpan

logger = logging.getLogger(__name__)

# ============================================================
# 🎣 LOOT TABLE (TOTAL = 1000.00%, urut harga)
# ============================================================
FISH_LOOT = {
    # ---------------- COMMON (total ≈600) ---------------- #
    "🤧 Zonk": 40.0,
    "𓆝 Small Fish": 80.0,
    "🐌 Snail": 33.0,
    "🐚 Hermit Crab": 33.0,
    "🦀 Crab": 33.0,
    "🐸 Frog": 33.0,
    "🐍 Snake": 33.0,
    "🐙 Octopus": 20.0,

    "ଳ Jelly Fish": 25.0,
    "🦪 Giant Clam": 25.0,
    "🐟 Goldfish": 25.0,
    "🐟 Stingrays Fish": 25.0,
    "🐟 Clownfish": 25.0,
    "🐟 Doryfish": 25.0,
    "🐟 Bannerfish": 25.0,
    "🐟 Moorish Idol": 25.0,
    "🐟 Axolotl": 25.0,
    "🐟 Beta Fish": 25.0,
    "🐟 Anglerfish": 25.0,
    "🦆 Duck": 25.0,

    # ---------------- RARE & LEGENDARY (total ≈399.99) ---------------- #
    "🐡 Pufferfish": 20.0,
    "📿 Lucky Jewel": 20.0,
    "🐱 Red Hammer Cat": 20.0,
    "🐱 Purple Fist Cat": 20.0,
    "🐱 Green Dino Cat": 20.0,
    "🐱 White Winter Cat": 20.0,
    "🐟 Shark": 20.0,
    "🐟 Seahorse": 20.0,
    "🐊 Crocodile": 20.0,
    "🦦 Seal": 20.0,
    "🐢 Turtle": 20.0,
    "🦞 Lobster": 20.0,

    "🐋 Orca": 13.0,
    "🐬 Dolphin": 13.0,
    "🐒 Monkey": 13.0,
    "🦍 Gorilla": 13.0,
    "🐼 Panda": 13.0,
    "🐶 Dog": 13.0,
    "🐹⚡ Pikachu": 13.0,
    "🐸🍀 Bulbasaur": 13.0,
    "🐢💧 Squirtle": 13.0,
    "🐉🔥 Charmander": 13.0,
    "🐋⚡ Kyogre": 13.0,

    # ---------------- MYTHIC (total ≈0.84) ---------------- #
    "🐉 Baby Dragon": 0.1,
    "🐉 Baby Spirit Dragon": 0.1,
    "🐉 Baby Magma Dragon": 0.1,
    "🐉 Skull Dragon": 0.09,
    "🐉 Blue Dragon": 0.09,
    "🐉 Black Dragon": 0.09,
    "🐉 Yellow Dragon": 0.09,
    "🧜‍♀️ Mermaid Boy": 0.09,
    "🧜‍♀️ Mermaid Girl": 0.09,

    # ---------------- ULTRA MYTHIC (total ≈0.016) ---------------- #
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
common_items = [
    "🤧 Zonk", "𓆝 Small Fish", "🐌 Snail", "🐚 Hermit Crab", "🦀 Crab",
    "🐸 Frog", "🐍 Snake", "🐙 Octopus", "ଳ Jelly Fish", "🦪 Giant Clam",
    "🐟 Goldfish", "🐟 Stingrays Fish", "🐟 Clownfish", "🐟 Doryfish",
    "🐟 Bannerfish", "🐟 Moorish Idol", "🐟 Axolotl", "🐟 Beta Fish",
    "🐟 Anglerfish", "🦆 Duck"
]

rare_items = [
    "🐡 Pufferfish", "📿 Lucky Jewel", "🐱 Red Hammer Cat", "🐱 Purple Fist Cat",
    "🐱 Green Dino Cat", "🐱 White Winter Cat", "🐟 Shark", "🐟 Seahorse",
    "🐊 Crocodile", "🦦 Seal", "🐢 Turtle", "🦞 Lobster",
    "🐋 Orca", "🐬 Dolphin", "🐒 Monkey", "🦍 Gorilla",
    "🐼 Panda", "🐶 Dog", "🐹⚡ Pikachu", "🐸🍀 Bulbasaur",
    "🐢💧 Squirtle", "🐉🔥 Charmander", "🐋⚡ Kyogre"
]

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
# 🎲 PROSES RANDOM LOOT
# ============================================================
def roll_loot(buff: float = 0.0) -> str:
    roll = random.uniform(0, 100)

    # Cek Ultra Mythic
    for item in ultra_mythic_items:
        chance = FISH_LOOT[item] + buff
        if roll <= chance:
            return item

    # Cek Mythic
    for item in mythic_items:
        chance = FISH_LOOT[item] + buff
        if roll <= chance:
            return item

    # Cek Rare / Legendary
    for item in rare_items:
        chance = FISH_LOOT[item] + buff
        if roll <= chance:
            return item

    # Cek Common
    for item in common_items:
        chance = FISH_LOOT[item] + buff
        if roll <= chance:
            return item

    # fallback
    return random.choice(common_items)
