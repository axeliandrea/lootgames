#test
import random
import asyncio
import logging
from pyrogram import Client
from lootgames.modules.fishing_helper import send_single_emoji, FISHING_EMOJI
from lootgames.modules import aquarium, umpan

logger = logging.getLogger(__name__)

# ---------------- LOOT TABLE ---------------- #
FISH_LOOT = {
    "🤧 Zonk": 25.00,
    "𓆝 Small Fish": 25.67,  # agar total 100.00%
    "🐚 Hermit Crab": 14.81,
    "🐸 Frog": 14.26,
    "🐙 Octopus": 6.36,

    # Rare
    "🐡 Pufferfish": 1.50,
    "ଳ Jelly Fish": 1.50,
    "📿 Lucky Jewel": 0.50,
    "🐟 Goldfish": 0.50,
    "🐟 Stingrays Fish": 0.50,
    "🐟 Seahorse": 0.50,
    "🐟 Clownfish": 0.50,
    "🐟 Doryfish": 0.50,
    "🐟 Bannerfish": 0.50,
    "🐟 Anglerfish": 0.50,
    "🦪 Giant Clam": 0.50,

    # Ultra rare
    "🐟 Beta Fish": 0.10,
    "🐟 Moorish Idol": 0.10,
    "🐟 Axolotl": 0.10,
    "🦆 Duck": 0.10,
    "🦀 Crab": 0.10,
    "🐟 Shark": 0.10,
    "🐊 Crocodile": 0.10,
    "🦦 Seal": 0.10,
    "🐢 Turtle": 0.10,
    "🦞 Lobster": 0.10,
    "🐹⚡ Pikachu": 0.10,
    "🐸🍀 Bulbasaur": 0.10,
    "🐢💧 Squirtle": 0.10,
    "🐉🔥 Charmander": 0.10,
    "🐋⚡ Kyogre": 0.10,
    "🐋 Orca": 0.10,
    "🐋 Dolphin": 0.10,
    "Lost cip": 0.10,

    # Mythic
    "🐉 Baby Dragon": 0.01,
    "🐉 Baby Spirit Dragon": 0.01,
    "🐉 Baby Magma Dragon": 0.01,
    "🐉 Skull Dragon": 0.01,
    "🐉 Blue Dragon": 0.01,
    "🐉 Black Dragon": 0.01,
    "🐉 Yellow Dragon": 0.01,
    "🧜‍♀️ Mermaid Boy": 0.01,
    "🧜‍♀️ Mermaid Girl": 0.01,
    "🐉 Cupid Dragon": 0.01,
}

# Buff rate berdasarkan umpan
BUFF_RATE = {
    "COMMON": 0.0,
    "RARE": 0.05,
    "LEGEND": 25.00,
    "MYTHIC": 35.00
}

# ---------------- FISHING FUNCTION ---------------- #
async def fishing_loot(client: Client, target_chat: int, username: str, user_id: int, umpan_type: str = "COMMON") -> str:
    """
    Menentukan loot fishing dan menyimpan ke database aquarium.py
    Mengembalikan loot item agar bisa dikirim ke group
    """
    buff = BUFF_RATE.get(umpan_type, 0.0)
    loot_item = roll_loot(buff, umpan_type)
    
    logger.info(f"[FISHING] {username} ({user_id}) memancing dengan {umpan_type}, mendapatkan: {loot_item}")
    
    try:
        await asyncio.sleep(2)  # delay animasi awal
        if target_chat:
            await client.send_message(target_chat, f"@{username} mendapatkan {loot_item}!")
        aquarium.add_fish(user_id, loot_item, 1)
    except Exception as e:
        logger.error(f"Error fishing loot untuk {username}: {e}")
    
    return loot_item

# ---------------- HELPERS ---------------- #
def roll_loot(buff: float, umpan_type: str = "COMMON") -> str:
    """
    Menentukan loot berdasarkan buff dan tipe umpan.
    Rare hanya bisa mendapatkan Rare + Legendary.
    """
    items = []
    chances = []

    # List item kategori
    common_items = ["🤧 Zonk", "𓆝 Small Fish", "🐚 Hermit Crab", "🐸 Frog", "🐙 Octopus"]
    rare_items = [
        "🐡 Pufferfish", "ଳ Jelly Fish", "📿 Lucky Jewel", "🐟 Goldfish",
        "🐟 Stingrays Fish", "🐟 Seahorse", "🐟 Clownfish", "🐟 Doryfish",
        "🐟 Bannerfish", "🐟 Anglerfish", "🦪 Giant Clam", "🐟 Shark",
        "🐊 Crocodile", "🦦 Seal", "🐢 Turtle", "🦞 Lobster", "🐹⚡ Pikachu",
        "🐋⚡ Kyogre", "🐋 Orca", "🐋 Dolphin", "Lost cip"
    ]
    legendary_items = [
        "🐉 Baby Dragon", "🐉 Baby Spirit Dragon", "🐉 Skull Dragon",
        "🐉 Blue Dragon", "🧜‍♀️ Mermaid Boy"
    ]
    mythic_items = ["🐉 Cupid Dragon"]

    for item, base_chance in FISH_LOOT.items():
        if umpan_type == "RARE":
            # Rare hanya boleh rare + legendary
            if item in common_items or item in mythic_items:
                continue

        items.append(item)
        # Zonk tidak kena buff
        if item == "🤧 Zonk":
            chances.append(base_chance)
        else:
            chances.append(base_chance + buff)

    loot_item = random.choices(items, weights=chances, k=1)[0]
    return loot_item

# ---------------- WORKER ---------------- #
async def fishing_worker(app: Client):
    """
    Worker background untuk proses fishing periodic.
    Saat ini hanya loop dummy tiap 60 detik.
    """
    logger.info("[FISHING WORKER] Worker siap berjalan...")
    while True:
        logger.debug("[FISHING WORKER] Tick... tidak ada aksi saat ini")
        await asyncio.sleep(60)
