import json
import os
from threading import Lock

DB_FILE = "storage/database.json"
lock = Lock()  # untuk mencegah race condition

# ==================== LOAD DATABASE ==================== #
if not os.path.exists("storage"):
    os.makedirs("storage")

if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        try:
            DATABASE = json.load(f)
        except json.JSONDecodeError:
            DATABASE = {}
else:
    DATABASE = {}

# ==================== FUNCTION HELPERS ==================== #
def save_db():
    """Simpan DATABASE ke file"""
    with lock:
        with open(DB_FILE, "w") as f:
            json.dump(DATABASE, f, indent=4)

def create_user(user_id: int):
    """Buat data default untuk user baru"""
    if str(user_id) not in DATABASE:
        DATABASE[str(user_id)] = {
            "umpan": {"A": 0, "B": 0, "C": 0},
            "koleksi_ikan": [],
            "axelcoin": 0
        }
        save_db()

def get_user(user_id: int):
    """Ambil data user, buat default jika belum ada"""
    create_user(user_id)
    return DATABASE[str(user_id)]

def update_user(user_id: int, key: str, value):
    """Update field tertentu user, key bisa 'axelcoin' atau 'koleksi_ikan' atau 'umpan'"""
    create_user(user_id)
    if key == "umpan":
        for k in value:  # update per jenis umpan
            DATABASE[str(user_id)]["umpan"][k] = value[k]
    else:
        DATABASE[str(user_id)][key] = value
    save_db()

def add_umpan(user_id: int, jenis: str, jumlah: int):
    """Tambah jumlah umpan tertentu"""
    create_user(user_id)
    DATABASE[str(user_id)]["umpan"][jenis] += jumlah
    save_db()

def add_axelcoin(user_id: int, jumlah: int):
    """Tambah Axelcoin user"""
    create_user(user_id)
    DATABASE[str(user_id)]["axelcoin"] += jumlah
    save_db()

def add_ikan(user_id: int, ikan: str):
    """Tambah ikan ke koleksi user"""
    create_user(user_id)
    if ikan not in DATABASE[str(user_id)]["koleksi_ikan"]:
        DATABASE[str(user_id)]["koleksi_ikan"].append(ikan)
        save_db()

def remove_umpan(user_id: int, jenis: str, jumlah: int):
    """Kurangi umpan tertentu, tidak boleh negatif"""
    create_user(user_id)
    DATABASE[str(user_id)]["umpan"][jenis] = max(0, DATABASE[str(user_id)]["umpan"][jenis] - jumlah)
    save_db()

def remove_axelcoin(user_id: int, jumlah: int):
    """Kurangi Axelcoin, tidak boleh negatif"""
    create_user(user_id)
    DATABASE[str(user_id)]["axelcoin"] = max(0, DATABASE[str(user_id)]["axelcoin"] - jumlah)
    save_db()
