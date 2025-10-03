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
    # Common
    "🤧 Zonk": 25.00,
    "𓆝 Small Fish": 32.45,
    "🐚 Hermit Crab": 14.81,
    "🐸 Frog": 14.26,
    "🐙 Octopus": 3.36,

    # Rare
    "🐡 Pufferfish": 0.78,
    "ଳ Jelly Fish": 0.78,
    "📿 Lucky Jewel": 0.78,
    "🐟 Goldfish": 0.78,
    "🐟 Stingrays Fish": 0.78,
    "🐟 Seahorse": 0.78,
    "🐟 Clownfish": 0.78,
    "🐟 Doryfish": 0.78,
    "🐟 Bannerfish": 0.78,
    "🐟 Anglerfish": 0.78,
    "🦪 Giant Clam": 0.78,
    "🐟 Shark": 0.16,
    "🐊 Crocodile": 0.16,
    "🦦 Seal": 0.16,
    "🐢 Turtle": 0.16,
    "🦞 Lobster": 0.16,
    "🐹⚡ Pikachu": 0.16,
    "🐋⚡ Kyogre": 0.16,
    "🐋 Orca": 0.16,
    "🐋 Dolphin": 0.16,
    "Lost cip": 0.16,

    # Mythic
    "🐉 Baby Dragon": 0.01,
    "🐉 Baby Spirit Dragon": 0.01,
    "🐉 Skull Dragon": 0.01,
    "🐉 Blue Dragon": 0.01,
    "🐉 Black Dragon": 0.01,
    "🐉 Yellow Dragon": 0.01,
    "🧜‍♀️ Mermaid Boy": 0.01,
    "🧜‍♀️ Mermaid Girl": 0.01,
    "🐉 Cupid Dragon": 0.001,
}

# Buff rate berdasarkan umpan
BUFF_RATE = {
    "COMMON": 0.0,
    "RARE": 3.00,
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
    Rare tidak akan menghasilkan Zonk, Small Fish, atau Hermit Crab.
    """
    items = []
    chances =
