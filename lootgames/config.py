import os
import logging
from dotenv import load_dotenv

# Load environment variables dari file .env
load_dotenv()

# ================== Telegram Bot Configuration ================== #
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ================== Bot Settings ================== #
OWNER_ID = int(os.getenv("OWNER_ID"))
ALLOWED_GROUP_ID = int(os.getenv("ALLOWED_GROUP_ID"))

# ================== Logging Configuration ================== #
LOG_LEVEL = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper())
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# ================== Yapping System Configuration ================== #
POINTS_PER_CHARS = int(os.getenv("POINTS_PER_CHARS", "5"))  # default 5 kalau tidak diisi
USER_DATA_FILE = os.getenv("USER_DATA_FILE", "lootgames/data/users.json")
