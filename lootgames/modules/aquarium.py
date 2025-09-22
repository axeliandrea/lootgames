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
    """
    Tambahkan ikan ke inventory user
    Tetap masuk database tanpa mengirim chat ke group
    """
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
    """Buat string daftar inventory user untuk ditampilkan di menu"""
    inventory = get_user_fish(user_id)
    if not inventory:
        return "🎣 Kamu belum menangkap ikan apapun."
    lines = []
    for fish, qty in inventory.items():
        lines.append(f"{fish}: {qty} pcs")
    return "\n".join(lines)

# ---------------- COLLECTION HANDLER ---------------- #
def show_collection(user_id: int) -> str:
    """Menampilkan semua koleksi tangkapan hasil memancing"""
    inventory = get_user_fish(user_id)
    if not inventory:
        return "🎣 Kamu belum menangkap apapun."
    
    lines = []
    for item, qty in inventory.items():
        lines.append(f"☘️ {item}: {qty} pcs")
    
    return "\n".join(lines)
