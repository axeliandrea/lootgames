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
    # Drop fish
    "🤧 Zonk": 54.11,  
    "𓆝 Small Fish": 30.52,
    "🐌 Snail": 4.50,
    "🐚 Hermit Crab": 3.00,
    "🐙 Octopus": 3.25,
    "Lost cip": 3.00, 
    "🐡 Pufferfish": 0.080,
    "ଳ Jelly Fish": 0.060, 
    "🐟 Seahorse": 1.00,
    "📿 Lucky Jewel": 0.080, 
    "🐸 Frog": 0.050, 
    "🐟 Clownfish": 0.050, 
    "🐟 Doryfish": 0.050, 
    "🐟 Bannerfish": 0.050, 
    "🐟 Anglerfish": 0.050, 
    "🦪 Giant Clam": 0.050, 
    "🐟 Shark": 0.025, 
    "🐊 Crocodile": 0.025, 
    "🐋 Orca": 0.05,
    "🐋 Dolphin": 0.05,
    "🐉 Baby Dragon": 0.0001,
    "🐉 Skull Dragon": 0.0001,
    "🐉 Blue Dragon": 0.0001,
    "🐉 Black Dragon": 0.0001,
    "🧜‍♀️ Mermaid Boy": 0.0001,
    "🧜‍♀️ Mermaid Girl": 0.0001,
    "🐉 Cupid Dragon": 0.00001,
}

# Buff rate berdasarkan umpan
BUFF_RATE = {
    "COMMON": 0.0,
    "RARE": 5.0,
    "LEGEND": 15.0,
    "MYTHIC": 25.0
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
    """
    Roll loot berdasarkan persentase dan buff.
    Chance dihitung: chance + buff, bisa desimal.
    Menggunakan random.choices agar probabilitas akurat.
    """
    items = list(FISH_LOOT.keys())
    chances = [chance + buff for chance in FISH_LOOT.values()]
    
    # random.choices mendukung weight float
    loot_item = random.choices(items, weights=chances, k=1)[0]
    return loot_item
