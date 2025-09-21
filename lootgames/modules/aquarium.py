# lootgames/modules/aquarium.py
import json
import os
import logging

logger = logging.getLogger(__name__)

DB_FILE = "storage/aquarium_data.json"

# ---------------- LOAD & SAVE ---------------- #
def load_data():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Gagal load aquarium_data.json: {e}")
        return {}

def save_data(data):
    try:
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Gagal save aquarium_data.json: {e}")

# ---------------- USER DATA HANDLER ---------------- #
def add_fish(user_id: int, fish_name: str, jumlah: int = 1):
    data = load_data()
    str_uid = str(user_id)
    if str_uid not in data:
        data[str_uid] = {}
    data[str_uid][fish_name] = data[str_uid].get(fish_name, 0) + jumlah
    save_data(data)

def get_user_fish(user_id: int):
    data = load_data()
    return data.get(str(user_id), {})

def reset_user(user_id: int):
    data = load_data()
    data.pop(str(user_id), None)
    save_data(data)

def reset_all():
    save_data({})
