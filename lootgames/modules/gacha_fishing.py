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
    # Common
    "🤧 Zonk": 20.18,
    "𓆝 Small Fish": 26.19,
    "🐚 Hermit Crab": 11.96,
    "🐸 Frog": 11.51,
    "🐙 Octopus": 2.71,
    
    # Rare
    "🐡 Pufferfish": 0.63,
    "ଳ Jelly Fish": 0.63,
    "📿 Lucky Jewel": 0.63,
    "🐟 Goldfish": 0.63,
    "🐟 Stingrays Fish": 0.63,
    "🐟 Seahorse": 0.63,
    "🐟 Clownfish": 0.63,
    "🐟 Doryfish": 0.63,
    "🐟 Bannerfish": 0.63,
    "🐟 Anglerfish": 0.63,
    "🦪 Giant Clam": 0.63,
    "🐟 Shark": 0.13,
    "🐊 Crocodile": 0.13,
    "🦦 Seal": 0.13,
    "🐢 Turtle": 0.13,
    "🦞 Lobster": 0.13,
    "🐹⚡ Pikachu": 0.13,
    "🐋⚡ Kyogre": 0.13,
    "🐋 Orca": 0.13,
    "🐋 Dolphin": 0.13,
    "Lost cip": 0.13,
    
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
    "RARE": 0.50,
    "LEGEND": 25.0,
    "MYTHIC": 35.0
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
