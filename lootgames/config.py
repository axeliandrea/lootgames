import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram Bot Configuration
API_ID = int(os.getenv("API_ID", "29580121"))
API_HASH = os.getenv("API_HASH", "fff375a88f6546f0da2df781ca7725df")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7660904765:AAFQuSU8ShpXAzqYqAhBojjGLf7U03ityck")

# Bot Settings
OWNER_ID = int(os.getenv("OWNER_ID", "6395738130"))
ALLOWED_GROUP_ID = int(os.getenv("ALLOWED_GROUP_ID", "-1002904817520"))

# Logging Configuration
LOG_LEVEL = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper())
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Yapping System Configuration
POINTS_PER_CHARS = int(os.getenv("POINTS_PER_CHARS", "5"))  # 5 characters = 1 point
USER_DATA_FILE = os.getenv("USER_DATA_FILE", "lootgames/data/users.json")
