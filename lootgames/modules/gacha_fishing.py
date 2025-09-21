# lootgames/modules/gacha_fishing.py
import random
import asyncio
import logging
from pyrogram import Client
from lootgames.modules.menu_utama import send_single_emoji, FISHING_EMOJI
from lootgames.modules import aquarium

logger = logging.getLogger(__name__)

# ---------------- LOOT TABLE SEDERHANA ---------------- #
FISH_LOOT = {
    "🧺 Ember Pecah": 65,
    "🥾 Sepatu Butut": 75,
    "🧻 Roll Tisue Bekas": 85,
    "🤧 Zonk": 90,
    "𓆝 Small Fish": 35,
    "🦀 Crab": 10,
    "🐡 Pufferfish": 3
}

# Buff rate berdasarkan umpan
BUFF_RATE = {
    "COMMON": 0,
    "RARE": 5,
    "LEGEND": 10,
    "MYTHIC": 15
}

# ---------------- FISHING FUNCTION ---------------- #
async def fishing_loot(client: Client, target_chat: int, username: str, user_id: int, umpan_type: str = "COMMON"):
    """
    Menentukan loot fishing dan menyimpan ke database aquarium.py
    """
    buff = BUFF_RATE.get(umpan_type, 0)
    loot_item = roll_loot(buff)
    
    try:
        await asyncio.sleep(2)  # delay animasi
        await send_single_emoji(client, target_chat, FISHING_EMOJI, f" @{username} mendapatkan {loot_item}!")
        aquarium.add_fish(user_id, loot_item, 1)
    except Exception as e:
        logger.error(f"Error fishing loot untuk {username}: {e}")

# ---------------- HELPERS ---------------- #
def roll_loot(buff: int) -> str:
    """
    Roll loot berdasarkan persentase dan buff.
    Chance dihitung: jika roll < chance - buff, item keluar
    """
    items = list(FISH_LOOT.items())
    random.shuffle(items)  # acak urutan
    for item, chance in items:
        roll = random.randint(1, 100)
        if roll <= max(0, chance - buff):
            return item
    return "🤧 Zonk"
