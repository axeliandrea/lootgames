# lootgames/modules/gacha_fishing.py
import random
import asyncio
import logging
from pyrogram import Client
from lootgames.modules.fishing_helper import send_single_emoji, FISHING_EMOJI
from lootgames.modules import aquarium, umpan

logger = logging.getLogger(__name__)

# ---------------- LOOT TABLE ---------------- #
# Persentase bisa desimal, misal 0.5%
FISH_LOOT = {
    "🤧 Zonk": 53.60,
    "𓆝 Small Fish": 20.52,
    "🐌 Snail": 4.50,
    "🐚 Hermit Crab": 3.00,
    "🐙 Octopus": 3.25,
    "Lost cip": 3.00, 
    "🐡 Pufferfish": 0.90, 
    "ଳ Jelly Fish": 1.00, 
    "📿 Lucky Jewel": 0.80,
    "🐟 Seahorse": 0.80, 
    "🐸 Frog": 1.00,
    "🐟 Clownfish": 1.20,  
    "🐟 Doryfish": 1.20,  
    "🐟 Bannerfish": 1.20,  
    "🐟 Anglerfish": 1.20,  
    "🦪 Giant Clam": 1.20,
    "🐟 Shark": 0.25, 
    "🐊 Crocodile": 0.25, 
    "🐋 Orca": 0.5,
    "🐋 Dolphin": 0.5,
    "🐉 Baby Dragon": 0.02,
    "🐉 Skull Dragon": 0.02,
    "🐉 Blue Dragon": 0.02,
    "🐉 Black Dragon": 0.02,
    "🧜‍♀️ Mermaid Boy": 0.02,
    "🧜‍♀️ Mermaid Girl": 0.02,
    "🐉 Cupid Dragon": 0.01,
}

# Buff rate berdasarkan umpan
BUFF_RATE = {
    "COMMON": 0.0,
    "RARE": 25.0,
    "LEGEND": 50.0,
    "MYTHIC": 75.0
}

# ---------------- FISHING FUNCTION ---------------- #
async def fishing_loot(client: Client, target_chat: int, username: str, user_id: int, umpan_type: str = "COMMON") -> str:
    """
    Menentukan loot fishing dan menyimpan ke database aquarium.py
    Mengembalikan loot item agar bisa dikirim ke group
    """
    buff = BUFF_RATE.get(umpan_type, 0.0)
    loot_item = roll_loot(buff)
    
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
def roll_loot(buff: float) -> str:
    items = list(FISH_LOOT.keys())
    chances = []
    for item, base_chance in FISH_LOOT.items():
        if item == "🤧 Zonk":
            chances.append(base_chance)  # Zonk tidak kena buff
        else:
            # Tambahkan buff hanya ke non-Zonk
            chances.append(base_chance + buff)

    loot_item = random.choices(items, weights=chances, k=1)[0]
    return loot_item
