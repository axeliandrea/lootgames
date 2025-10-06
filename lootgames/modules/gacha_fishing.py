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
    "🤧 Zonk": 15.00,
    "𓆝 Small Fish": 27.67,  # agar total 100.00%
    "🐚 Hermit Crab": 18.81,
    "🐸 Frog": 18.26,
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
    "🐉 Skull Dragon": 0.001,
    "🐉 Blue Dragon": 0.001,
    "🐉 Black Dragon": 0.001,
    "🐉 Yellow Dragon": 0.001,
    "🧜‍♀️ Mermaid Boy": 0.001,
    "🧜‍♀️ Mermaid Girl": 0.001,
    "🐉 Cupid Dragon": 0.001,
}

# ---------------- BUFF RATE ---------------- #
BUFF_RATE = {
    "COMMON": 0.0,
    "RARE": 0.20,
    "LEGEND": 1.00,
    "MYTHIC": 5.00
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
    Menentukan loot berdasarkan buff dan tipe umpan:
      - COMMON: bisa dapat semua
      - RARE: hanya bisa dapat mulai dari Frog ke atas
      - LEGEND: hanya bisa dapat Rare dan ke atas
      - MYTHIC: hanya bisa dapat Ultra Rare dan Mythic
    """
    items = []
    chances = []

    # Kategori pembatas
    exclude_for_rare = ["🤧 Zonk", "𓆝 Small Fish", "🐚 Hermit Crab"]
    exclude_for_legend = exclude_for_rare + ["🐸 Frog", "🐙 Octopus"]
    exclude_for_mythic = exclude_for_legend + [
        "🐡 Pufferfish", "ଳ Jelly Fish", "📿 Lucky Jewel", "🐟 Goldfish",
        "🐟 Stingrays Fish", "🐟 Seahorse", "🐟 Clownfish", "🐟 Doryfish",
        "🐟 Bannerfish", "🐟 Anglerfish", "🦪 Giant Clam"
    ]

    for item, base_chance in FISH_LOOT.items():
        # Filter berdasarkan umpan
        if umpan_type == "RARE" and item in exclude_for_rare:
            continue
        elif umpan_type == "LEGEND" and item in exclude_for_legend:
            continue
        elif umpan_type == "MYTHIC" and item in exclude_for_mythic:
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
