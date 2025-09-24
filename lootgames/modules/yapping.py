# lootgames/modules/yapping.py
import os
import json
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= CONFIG ================= #
OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772  # <-- pastikan ini sama dengan group ID sebenarnya
YAPPINGPOINT_DB = "storage/chat_points.json"
DEBUG = True
IGNORED_USERS = ["694690", "some_bot_username"]  # tambahkan user yang ingin di-ignore

# ================= HELPERS ================= #
def load_points():
    if not os.path.exists(YAPPINGPOINT_DB):
        return {}
    with open(YAPPINGPOINT_DB, "r") as f:
        return json.load(f)

def save_points(data):
    with open(YAPPINGPOINT_DB, "w") as f:
        json.dump(data, f, indent=2)

def add_point(user_id, username, point=1):
    data = load_points()
    user_id_str = str(user_id)
    if user_id_str not in data:
        data[user_id_str] = {"username": username, "point": 0}
    data[user_id_str]["point"] += point
    save_points(data)
    if DEBUG:
        print(f"[DEBUG POINT] {username} ({user_id}) +{point} → {data[user_id_str]['point']} total")

# ================= HANDLER ================= #
async def handle_all_messages(client: Client, message: Message):
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id if user else None
    username = user.username if user else "Unknown"

    text = message.text or ""
    char_count = len(text)

    # PRINT RAW DEBUG SEMUA PESAN
    print(f"[RAW DEBUG] chat_id={chat_id} from_user={user_id} username={username} text='{text}'")

    # FILTER IGNORE
    if user_id in IGNORED_USERS or username in IGNORED_USERS:
        if DEBUG:
            print(f"[DEBUG] IGNORE user {username} ({user_id})")
        return

    # FILTER GROUP TARGET
    if chat_id != TARGET_GROUP:
        if DEBUG:
            print(f"[DEBUG] SKIP chat_id {chat_id} != TARGET_GROUP")
        return

    # HITUNG POINT HANYA UNTUK TEXT VALID
    if char_count > 0:
        add_point(user_id, username, point=1)

# ================= REGISTER ================= #
def register(app: Client):
    # handler untuk semua pesan di group, tanpa filter supaya bisa debug
    app.add_handler(
        app.on_message()(handle_all_messages)
    )
    if DEBUG:
        print("[DEBUG] Yapping handler registered")
