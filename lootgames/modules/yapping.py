import json
import logging
import os
from pyrogram import Client, filters
from pyrogram.types import Message
from ..config import ALLOWED_GROUP_ID, POINTS_PER_CHARS, USER_DATA_FILE

logger = logging.getLogger(__name__)

class YappingSystem:
    def __init__(self):
        self.data_file = USER_DATA_FILE
        self.ensure_data_file()
    
    def ensure_data_file(self):
        """Pastikan file data users.json ada"""
        if not os.path.exists(self.data_file):
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, 'w') as f:
                json.dump({}, f)
    
    def load_users(self):
        """Load data user dari JSON file"""
        try:
            with open(self.data_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            logger.error("Error decoding users.json, creating new file")
            return {}
    
    def save_users(self, users_data):
        """Simpan data user ke JSON file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(users_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving users data: {e}")
    
    def add_points(self, user_id, username, points):
        """Tambah points ke user"""
        users = self.load_users()
        user_key = str(user_id)
        
        if user_key not in users:
            users[user_key] = {
                "username": username,
                "points": 0,
                "total_messages": 0,
                "total_chars": 0
            }
        
        users[user_key]["points"] += points
        users[user_key]["total_messages"] += 1
        users[user_key]["total_chars"] += points * POINTS_PER_CHARS
        if username:  # Update username jika ada
            users[user_key]["username"] = username
        
        self.save_users(users)
        return users[user_key]["points"]
    
    def get_user_points(self, user_id):
        """Dapatkan points user"""
        users = self.load_users()
        user_key = str(user_id)
        return users.get(user_key, {}).get("points", 0)
    
    def get_leaderboard(self, limit=10):
        """Dapatkan leaderboard user"""
        users = self.load_users()
        sorted_users = sorted(
            users.items(), 
            key=lambda x: x[1]["points"], 
            reverse=True
        )
        return sorted_users[:limit]

# Initialize yapping system
yapping = YappingSystem()

# Filter untuk group yang diizinkan
def allowed_group_filter():
    def func(_, __, message: Message):
        return message.chat.id == ALLOWED_GROUP_ID
    return filters.create(func)

async def handle_yapping_message(client: Client, message: Message):
    """Handler untuk menghitung points dari chat"""
    if message.from_user is None:
        return
    
    # Hitung karakter dalam pesan
    text = message.text or message.caption or ""
    char_count = len(text)
    
    if char_count < POINTS_PER_CHARS:
        return  # Tidak cukup karakter untuk mendapat point
    
    # Hitung points (1 point per 5 karakter)
    points_earned = char_count // POINTS_PER_CHARS
    
    if points_earned > 0:
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name
        
        total_points = yapping.add_points(user_id, username, points_earned)
        
        logger.info(f"User {username} ({user_id}) earned {points_earned} points from {char_count} chars. Total: {total_points}")

async def handle_points_command(client: Client, message: Message):
    """Handler untuk command /points"""
    user_id = message.from_user.id
    points = yapping.get_user_points(user_id)
    username = message.from_user.username or message.from_user.first_name
    
    await message.reply_text(
        f"🎯 **Yapping Points**\
\
"
        f"👤 **User:** {username}\
"
        f"⭐ **Total Points:** {points:,}\
\
"
        f"💬 Dapatkan 1 point setiap {POINTS_PER_CHARS} karakter yang kamu chat!"
    )

async def handle_leaderboard_command(client: Client, message: Message):
    """Handler untuk command /leaderboard"""
    leaderboard = yapping.get_leaderboard(10)
    
    if not leaderboard:
        await message.reply_text("📊 **Yapping Leaderboard**\
\
Belum ada data user.")
        return
    
    text = "🏆 **Top 10 Yapping Leaderboard**\
\
"
    
    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, data) in enumerate(leaderboard):
        medal = medals[i] if i < 3 else f"{i+1}."
        username = data.get("username", f"User {user_id}")
        points = data.get("points", 0)
        text += f"{medal} **{username}** - {points:,} points\
"
    
    text += f"\
💬 Chat terus untuk naik ranking! ({POINTS_PER_CHARS} chars = 1 point)"
    
    await message.reply_text(text)

def register(app: Client):
    """Register handlers untuk yapping module"""
    
    # Handler untuk semua pesan di group yang diizinkan
    @app.on_message(allowed_group_filter() & ~filters.bot)
    async def yapping_handler(client: Client, message: Message):
        await handle_yapping_message(client, message)
    
    # Command untuk cek points
    @app.on_message(filters.command("points") & allowed_group_filter())
    async def points_command(client: Client, message: Message):
        await handle_points_command(client, message)
    
    # Command untuk leaderboard
    @app.on_message(filters.command(["leaderboard", "lb"]) & allowed_group_filter())
    async def leaderboard_command(client: Client, message: Message):
        await handle_leaderboard_command(client, message)
    
    logger.info("🎯 Yapping module handlers registered successfully!")
