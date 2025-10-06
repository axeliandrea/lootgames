# lootgames/modules/fishing_loot.py TESTER COBAIN LOOT DROP 1000%
import random
import asyncio
import logging
from pyrogram import Client
from lootgames.modules.fishing_helper import send_single_emoji, FISHING_EMOJI
from lootgames.modules import aquarium, umpan

logger = logging.getLogger(__name__)

# ---------------- LOOT TABLE (TOTAL ≈1000.00%) ---------------- #
FISH_LOOT = {
    "🤧 Zonk": 50.00,               
    "𓆝 Small Fish": 128.00,       
    "🐌 Snail": 120.00,             
    "🐚 Hermit Crab": 120.00,       
    "🦀 Crab": 120.00,              
    "🐸 Frog": 120.00,              
    "🐍 Snake": 120.00,             
    "🐙 Octopus": 100.00,           
    "ଳ Jelly Fish": 80.00,          
    "🦪 Giant Clam": 80.00,         
    "🐟 Goldfish": 80.00,           
    "🐟 Stingrays Fish": 80.00,     
    "🐟 Clownfish": 80.00,          
    "🐟 Doryfish": 80.00,           
    "🐟 Bannerfish": 80.00,         
    "🐟 Moorish Idol": 80.00,       
    "🐟 Axolotl": 80.00,            
    "🐟 Beta Fish": 80.00,          
    "🐟 Anglerfish": 80.00,         
    "🦆 Duck": 80.00,               
    "🐔 Chicken": 80.00,            
    "🐡 Pufferfish": 70.00,         
    "📿 Lucky Jewel": 60.00,        
    "🐱 Red Hammer Cat": 10.00,     
    "🐱 Purple Fist Cat": 10.00,    
    "🐱 Green Dino Cat": 10.00,     
    "🐱 White Winter Cat": 10.00,   
    "🐟 Shark": 40.00,              
    "🐟 Seahorse": 40.00,           
    "🐊 Crocodile": 40.00,          
    "🦦 Seal": 40.00,               
    "🐢 Turtle": 40.00,             
    "🦞 Lobster": 40.00,            
    "🐋 Orca": 30.00,               
    "🐬 Dolphin": 30.00,            
    "🐹⚡ Pikachu": 5.00,           
    "🐸🍀 Bulbasaur": 5.00,         
    "🐢💧 Squirtle": 5.00,          
    "🐉🔥 Charmander": 5.00,        
    "🐋⚡ Kyogre": 5.00,             
    "🐉 Baby Dragon": 0.10,         
    "🐉 Baby Spirit Dragon": 0.10,  
    "🐉 Baby Magma Dragon": 0.10,   
    "🐉 Skull Dragon": 0.09,        
    "🐉 Blue Dragon": 0.09,         
    "🐉 Black Dragon": 0.09,        
    "🐉 Yellow Dragon": 0.09,       
    "🧜‍♀️ Mermaid Boy": 0.09,       
    "🧜‍♀️ Mermaid Girl": 0.09,      
    "🐉 Cupid Dragon": 0.01,        
    "🐺 Werewolf": 0.009,           
    "👹 Dark Lord Demon": 0.001,    
    "🦊 Princess of Nine Tail": 0.001
}

# Hitung total drop rate
_total = sum(FISH_LOOT.values())
logger.info(f"[INIT] Total drop rate: {_total:.2f}% (Target: ~1000%)")

# ---------------- BUFF RATE ---------------- #
BUFF_RATE = {
    "COMMON": 0.0,
    "RARE": 1.50,
    "LEGEND": 5.00,
    "MYTHIC": 10.00
}

# ---------------- FISHING FUNCTION ---------------- #
async def fishing_loot(client: Client, target_chat: int, username: str, user_id: int, umpan_type: str = "COMMON") -> str:
    buff = BUFF_RATE.get(umpan_type, 0.0)
    loot_item = roll_loot(buff, umpan_type)
    
    logger.info(f"[FISHING] {username} ({user_id}) memancing dengan {umpan_type}, mendapatkan: {loot_item}")
    
    try:
        await asyncio.sleep(2)  # delay animasi
        if target_chat:
            await client.send_message(target_chat, f"@{username} mendapatkan {loot_item}!")
        aquarium.add_fish(user_id, loot_item, 1)
    except Exception as e:
        logger.error(f"[FISHING] Error untuk {username}: {e}")
    
    return loot_item

# ---------------- HELPERS ---------------- #
def roll_loot(buff: float, umpan_type: str = "COMMON") -> str:
    items = []
    chances = []

    # Filter item sesuai level umpan
    exclude_for_rare = ["🤧 Zonk", "𓆝 Small Fish", "🐚 Hermit Crab"]
    exclude_for_legend = exclude_for_rare + ["🐸 Frog", "🐙 Octopus", "🐍 Snake"]
    exclude_for_mythic = exclude_for_legend + [
        "🐡 Pufferfish", "ଳ Jelly Fish", "📿 Lucky Jewel", "🐟 Goldfish",
        "🐟 Stingrays Fish", "🐟 Seahorse", "🐟 Clownfish", "🐟 Doryfish",
        "🐟 Bannerfish", "🐟 Anglerfish", "🦪 Giant Clam"
    ]

    for item, base_chance in FISH_LOOT.items():
        if umpan_type == "RARE" and item in exclude_for_rare:
            continue
        elif umpan_type == "LEGEND" and item in exclude_for_legend:
            continue
        elif umpan_type == "MYTHIC" and item in exclude_for_mythic:
            continue

        items.append(item)
        if item == "🤧 Zonk":
            chances.append(base_chance)
        else:
            chances.append(base_chance + buff)

    loot_item = random.choices(items, weights=chances, k=1)[0]
    return loot_item

# ---------------- WORKER ---------------- #
async def fishing_worker(app: Client):
    logger.info("[FISHING WORKER] Worker siap berjalan...")
    while True:
        logger.debug("[FISHING WORKER] Tick... tidak ada aksi saat ini")
        await asyncio.sleep(60)
