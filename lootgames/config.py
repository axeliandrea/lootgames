import os
import logging
from dotenv import load_dotenv

# Load .env
load_dotenv()

def get_env_int(key, default=None):
    value = os.getenv(key)
    if value is None:
        if default is not None:
            return default
        raise ValueError(f"Environment variable {key} tidak ditemukan!")
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Environment variable {key} harus angka, tapi '{value}' ditemukan.")

def get_env_str(key, default=None):
    value = os.getenv(key)
    if value is None:
        if default is not None:
            return default
        raise ValueError(f"Environment variable {key} tidak ditemukan!")
    return value

# ================== Telegram Bot Configuration ================== #
API_ID = get_env_int("API_ID")
API_HASH = get_env_str("API_HASH")
BOT_TOKEN = get_env_str("BOT_TOKEN")

# ================== Bot Settings ================== #
OWNER_ID = get_env_int("OWNER_ID")
ALLOWED_GROUP_ID = get_env_int("ALLOWED_GROUP_ID")

# ================== Logging Configuration ================== #
LOG_LEVEL = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper())
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# ================== Yapping System Configuration ================== #
POINTS_PER_CHARS = get_env_int("POINTS_PER_CHARS", 5)  # default 5
USER_DATA_FILE = get_env_str("USER_DATA_FILE", "lootgames/data/users.json")
