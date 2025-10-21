# lootgames/modules/aquarium.py
import json
import os
import logging

logger = logging.getLogger(__name__)

DB_FILE = "storage/aquarium_data.json"

# ---------------- LOAD & SAVE ---------------- #
def load_data() -> dict:
    """Load semua data aquarium dari file JSON"""
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Gagal load aquarium_data.json: {e}")
        return {}

def save_data(data: dict):
    """Simpan data aquarium ke file JSON"""
    try:
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Gagal save aquarium_data.json: {e}")

# ---------------- USER DATA HANDLER ---------------- #
def add_fish(user_id: int, fish_name: str, jumlah: int = 1):
    """Tambahkan ikan ke inventory user"""
    data = load_data()
    str_uid = str(user_id)
    if str_uid not in data:
        data[str_uid] = {}
    data[str_uid][fish_name] = data[str_uid].get(fish_name, 0) + jumlah
    save_data(data)
    logger.info(f"[AQUARIUM] User {user_id} mendapatkan {jumlah}x {fish_name} (background only)")

def get_user_fish(user_id: int) -> dict:
    """Ambil seluruh inventory ikan user"""
    data = load_data()
    return data.get(str(user_id), {})

def reset_user(user_id: int):
    """Reset inventory user tertentu"""
    data = load_data()
    data.pop(str(user_id), None)
    save_data(data)
    logger.info(f"[AQUARIUM] Inventory user {user_id} direset")

def reset_all():
    """Reset semua inventory user"""
    save_data({})
    logger.info("[AQUARIUM] Semua inventory direset")

# ---------------- UTILITY ---------------- #
def get_total_fish(user_id: int) -> int:
    """Hitung total jumlah semua ikan user"""
    inventory = get_user_fish(user_id)
    return sum(inventory.values())

def list_inventory(user_id: int) -> str:
    """
    Buat string daftar inventory user untuk ditampilkan di menu.
    - Semua monster ditampilkan, termasuk yang 0
    - Urut dari jumlah terbanyak ke paling sedikit
    - Tambahkan Total All di bagian bawah
    """
    inventory = get_user_fish(user_id) or {}

    # master list semua monster (sesuaikan dengan game)
    master_monsters = [
        "🧜‍♀️ Mermaid Girl", "🐟 Axolotl", "🐟 Doryfish", "🧬 Mysterious DNA", "🐊 Crocodile",
        "🐟 Seahorse", "🐡 Pufferfish", "🐟 Shark", "📿 Lucky Jewel", "🐱 White Winter Cat",
        "🦦 Seal", "🐢 Turtle", "🐬 Dolphin", "🐙 Octopus", "🐢💧 Squirtle", "🐱 Green Dino Cat",
        "🐱 Red Hammer Cat", "🐶 Dog", "🦍 Gorilla", "🦞 Lobster", "🐉 Baby Magma Dragon",
        "🐉 Baby Spirit Dragon", "🐉 Dark Knight Dragon", "🐌 Snail", "🐒 Monkey",
        "🐦‍🔥 Fire Phoenix", "🐦🌌 Dark Phoenix", "🐯 White Tiger", "🐱 Purple Fist Cat",
        "🐹⚡ Pikachu", "🐼 Panda", "🦇 bat", "🦪 Giant Clam", "ଳ Jelly Fish", "𓆝 Small Fish",
        "🐉 Baby Dragon", "🐉 Black Dragon", "🐉 Blue Dragon", "🐉 Cupid Dragon", "🐉 Skull Dragon",
        "🐉 Snail Dragon", "🐉 Yellow Dragon", "🐉🔥 Charmander", "🐋 Orca", "🐋⚡ Kyogre",
        "🐍 Snake", "🐔 Chicken", "🐚 Hermit Crab", "🐟 Anglerfish", "🐟 Bannerfish", "🐟 Beta Fish",
        "🐟 Clownfish", "🐟 Goldfish", "🐟 Moorish Idol", "🐟 Stingrays Fish", "🐦❄️ Frost Phoenix",
        "🐱 Rainbow Angel Cat", "🐸 Frog", "🐸🍀 Bulbasaur", "🐺 Werewolf", "🐻 Bear",
        "👑 Queen Of Hermit", "👑 Queen Of Medusa 🐍", "👑🧜‍♀️ Princess Mermaid", "👹 Dark Fish Warrior",
        "👹 Dark Lord Demon", "🤖 Mecha Frog", "🤧 Zonk", "🦀 Crab", "🦁🐍 Chimera",
        "🦆 Duck", "🦊 Princess of Nine Tail", "🧜‍♀️ Mermaid Boy", "✨ Thunder Element", "✨ Fire Element",
        "✨ Water Element", "✨ Wind Element", "🧚 Sea Fairy"
    ]

    # buat dict lengkap semua monster, default 0 jika belum ada
    full_inventory = {m: inventory.get(m, 0) for m in master_monsters}

    # urut dari jumlah terbanyak ke paling sedikit
    sorted_inventory = dict(sorted(full_inventory.items(), key=lambda x: x[1], reverse=True))

    # buat list baris
    lines = [f"{fish} : {qty}" for fish, qty in sorted_inventory.items()]

    # total all termasuk yang 0
    total_monster = sum(sorted_inventory.values())
    lines.append(f"Total All : {total_monster}")

    return "\n".join(lines)
