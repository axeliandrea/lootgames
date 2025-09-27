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
    # Old drops (rounded, scaled)
    "🤧 Zonk": 56.00,
    "𓆝 Small Fish": 9.68,
    "🐌 Snail": 4.44,
    "🐙 Octopus": 3.23,
    "🐡 Pufferfish": 0.81,
    "Lost cip": 4.03,
    "ଳ Jelly Fish": 1.61,
    "📿 Lucky Jewel": 0.81,
    "🐋 Orca": 0.04,
    "🐉 Baby Dragon": 0.0001,
    "🐉 Skull Dragon": 0.0001,
    "🐉 Blue Dragon": 0.0001,
    "🐸 Frog": 4.00,
    "🐟 Clownfish": 4.00,
    "🐟 Doryfish": 4.00,
    "🐟 Bannerfish": 4.00,
    "🐟 Anglerfish": 4.00,
    "🦪 Giant Clam": 4.00
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
