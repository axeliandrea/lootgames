# lootgames/modules/utils.py
import os
import json
from datetime import datetime

# -------------------------------
# FILE PATHS
# -------------------------------
POINT_FILE = "storage/chat_points.json"
DAILY_POINT_FILE = "storage/daily_points.json"
DAILY_RESET_FILE = "storage/daily_reset.json"
TOPUP_HISTORY_FILE = "storage/topup_history.json"

# -------------------------------
# UTILS UMUM
# -------------------------------
def load_json(file_path):
    """Load data JSON dari file, aman terhadap error."""
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print(f"[DEBUG] JSONDecodeError: {file_path} rusak, membuat ulang")
                return {}
    return {}

def save_json(file_path, data):
    """Simpan data ke file JSON, buat folder jika belum ada."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[DEBUG] Data disimpan ke {file_path}")

# -------------------------------
# CHAT POINTS & DAILY POINTS
# -------------------------------
def load_points():
    return load_json(POINT_FILE)

def save_points(data):
    save_json(POINT_FILE, data)

def load_daily_points():
    daily_points = load_json(DAILY_POINT_FILE)
    auto_reset_daily_points(daily_points)
    return daily_points

def save_daily_points(data):
    save_json(DAILY_POINT_FILE, data)

def add_user_if_not_exist(points, user_id, username):
    user_id = str(user_id)
    if user_id not in points:
        points[user_id] = {"username": username, "points": 0, "level": 0}
        print(f"[DEBUG] User baru ditambahkan: {username} ({user_id})")
    else:
        points[user_id]["username"] = username
        if "level" not in points[user_id]:
            points[user_id]["level"] = 0

def add_points(user_id, username, amount=1):
    user_id = str(user_id)
    points = load_points()
    daily_points = load_daily_points()

    add_user_if_not_exist(points, user_id, username)
    add_user_if_not_exist(daily_points, user_id, username)

    points[user_id]["points"] += amount
    daily_points[user_id]["points"] += amount

    print(f"[DEBUG] {username} ({user_id}) mendapat +{amount} poin")
    print(f"[DEBUG] Total points sekarang: {points[user_id]['points']}")
    print(f"[DEBUG] Daily points sekarang: {daily_points[user_id]['points']}")

    save_points(points)
    save_daily_points(daily_points)

def reset_daily_points():
    save_daily_points({})
    save_json(DAILY_RESET_FILE, {"last_reset": datetime.now().strftime("%Y-%m-%d")})
    print("[DEBUG] Daily points direset manual")

def auto_reset_daily_points(daily_points):
    """Reset daily points otomatis jika tanggal sudah berganti."""
    reset_info = load_json(DAILY_RESET_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    last_reset = reset_info.get("last_reset", "")

    if last_reset != today:
        daily_points.clear()
        save_daily_points(daily_points)
        save_json(DAILY_RESET_FILE, {"last_reset": today})
        print(f"[DEBUG] Daily points direset otomatis: {today}")

# -------------------------------
# TOPUP HISTORY & UMPAN
# -------------------------------
def load_topup_history():
    return load_json(TOPUP_HISTORY_FILE)

def save_topup_history(user_id, username, amount, bonus, umpan_type):
    data = load_json(TOPUP_HISTORY_FILE)
    user_id_str = str(user_id)
    data.setdefault(user_id_str, [])
    next_id = len(data[user_id_str]) + 1
    data[user_id_str].append({
        "id": next_id,
        "username": username,
        "amount": amount,
        "bonus": bonus,
        "type": umpan_type,
        "timestamp": datetime.utcnow().timestamp()
    })
    save_json(TOPUP_HISTORY_FILE, data)
    print(f"[DEBUG] History top-up disimpan untuk user {user_id}")

def calculate_umpan(amount, tipe):
    """
    Hitung jumlah umpan berdasarkan tipe dan nominal top-up.
    Umpan A: 1 pcs = 50
    Umpan B: 1 pcs = 500
    """
    if tipe == "A":
        return int(amount // 50)
    elif tipe == "B":
        return int(amount // 500)
    return 0
