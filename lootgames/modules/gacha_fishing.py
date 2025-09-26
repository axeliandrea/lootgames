# lootgames/modules/gacha_fishing.py tester 1
import random
import asyncio
import logging
from pyrogram import Client
from lootgames.modules.fishing_helper import send_single_emoji, FISHING_EMOJI
from lootgames.modules import aquarium, umpan

logger = logging.getLogger(__name__)

# ---------------- LOOT TABLE ---------------- #
FISH_LOOT = {
    "🤧 Zonk": 78,
    "𓆝 Small Fish": 10,
    "🐌 snail": 4,
    "🐙 octopus": 2,   
    "🐡 Pufferfish": 1,
    "lost cip": 5
}

# Buff rate berdasarkan umpan
BUFF_RATE = {
    "COMMON": 0,
    "RARE": 5,
    "LEGEND": 15,
    "MYTHIC": 25
}

# ---------------- FISHING FUNCTION ---------------- #
async def fishing_loot(client: Client, target_chat: int, username: str, user_id: int, umpan_type: str = "COMMON") -> str:
    """
    Menentukan loot fishing dan menyimpan ke database aquarium.py
    Mengembalikan loot item agar bisa dikirim ke group
    """
    buff = BUFF_RATE.get(umpan_type, 0)
    loot_item = roll_loot(buff)
    
    logger.info(f"[FISHING] {username} ({user_id}) memancing dengan {umpan_type}, mendapatkan: {loot_item}")
    
    # Simulasi animasi dan kirim pesan ke group
    try:
        await asyncio.sleep(2)  # delay animasi awal
        if target_chat:
            # Kirim pesan langsung ke group, menggantikan pesan ⬛ lama
            await client.send_message(target_chat, f"@{username} mendapatkan {loot_item}!")
        # Simpan loot ke database aquarium
        aquarium.add_fish(user_id, loot_item, 1)
    except Exception as e:
        logger.error(f"Error fishing loot untuk {username}: {e}")
    
    return loot_item

# ---------------- HELPERS ---------------- #
def roll_loot(buff: int) -> str:
    """
    Roll loot berdasarkan persentase dan buff.
    Chance dihitung: jika roll <= chance + buff, item keluar
    """
    items = list(FISH_LOOT.items())
    random.shuffle(items)
    for item, chance in items:
        roll = random.randint(1, 100)
        if roll <= chance + buff:
            return item
    return "🤧 Zonk"
