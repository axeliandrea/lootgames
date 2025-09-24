# lootgames/modules/yapping.py
import os
import json
import logging
from pyrogram import filters
from pyrogram.types import Message

# ================= CONFIG ================= #
TARGET_GROUP = -1002946278772  # Group tempat chat dihitung point
YAPPINGPOINT_DB = "storage/chat_points.json"
DEBUG = True

# ================= LOGGER ================= #
logger = logging.getLogger(__name__)
if DEBUG:
    logger.setLevel(logging.DEBUG)

# ================= HELPER FUNCTIONS ================= #
def load_points():
    """Muat data point dari file storage"""
    if not os.path.exists(YAPPINGPOINT_DB):
        return {}
    try:
        with open(YAPPINGPOINT_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Gagal load point DB: {e}")
        return {}

def save_points(data):
    """Simpan data point ke file storage"""
    try:
        with open(YAPPINGPOINT_DB, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Gagal simpan point DB: {e}")

def add_point(user_id: int, username: str, chars: int):
    """Tambah point user berdasarkan jumlah karakter chat"""
    points = load_points()
    user_key = str(user_id)
    # hitung 5 karakter = 1 point
    point_gain = chars // 5
    if point_gain <= 0:
        return 0

    if user_key not in points:
        points[user_key] = {"username": username, "point": 0}

    points[user_key]["username"] = username  # update username jika berubah
    points[user_key]["point"] += point_gain
    save_points(points)
    return point_gain

# ================= HANDLER REGISTRATION ================= #
def register(app):
    """Register handler Pyrogram"""
    @app.on_message(filters.group & filters.chat(TARGET_GROUP))
    async def handle_group_message(client, message: Message):
        user_id = message.from_user.id
        username = message.from_user.username or f"user{user_id}"
        text = message.text or ""

        # Debug seluruh chat
        if DEBUG:
            logger.debug(f"[CHAT DEBUG] {username} ({user_id}): {text}")

        # Hitung jumlah karakter dan tambahkan point
        char_count = len(text)
        gained = add_point(user_id, username, char_count)
        if gained > 0:
            if DEBUG:
                logger.debug(f"[POINT DEBUG] {username} (+{gained} point) Total: {load_points().get(str(user_id), {}).get('point', 0)}")
