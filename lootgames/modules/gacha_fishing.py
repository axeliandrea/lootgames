# lootgames/modules/gacha_fishing.py
import random
import asyncio
import logging
from pyrogram import Client
from lootgames.modules import aquarium

logger = logging.getLogger(__name__)

# ---------------- LOOT TABLE ---------------- #
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
async def fishing_loot(
    client: Client,
    target_chat: int | None,
    username: str,
    user_id: int,
    umpan_type: str = "COMMON",
    *,
    return_loot: bool = False
):
    """
    Menentukan loot fishing dan menyimpan ke database aquarium.py
    Jika return_loot=True, hanya mengembalikan loot, tidak kirim ke chat.
    """
    buff = BUFF_RATE.get(umpan_type, 0)
    loot_item = roll_loot(buff)
    
    logger.info(f"[FISHING] {username} ({user_id}) memancing dengan {umpan_type}, mendapatkan: {loot_item}")
    
    # Simpan ke database aquarium
    aquarium.add_fish(user_id, loot_item, 1)

    # Kirim ke chat jika target_chat diberikan
    if target_chat is not None:
        try:
            await asyncio.sleep(2)  # delay animasi
            await client.send_message(target_chat, f"🎣 @{username} mendapatkan {loot_item}!")
        except Exception as e:
            logger.error(f"Error kirim loot ke chat {target_chat}: {e}")
    
    if return_loot:
        return loot_item

# ---------------- HELPERS ---------------- #
def roll_loot(buff: int) -> str:
    """
    Roll loot berdasarkan persentase dan buff.
    Chance dihitung: jika roll <= chance + buff, item keluar
    """
    items = list(FISH_LOOT.items())
    random.shuffle(items)  # acak urutan
    for item, chance in items:
        roll = random.randint(1, 100)
        if roll <= chance + buff:
            return item
    return "🤧 Zonk"
