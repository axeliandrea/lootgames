# lootgames/config.py

import os
from dotenv import load_dotenv

# Load variabel dari file .env
load_dotenv()

class Config:
    # Wajib isi di .env
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")  # kalau pakai bot
    SESSION_STRING = os.getenv("SESSION_STRING")  # kalau pakai Ubot (userbot)

    # Owner & Target Group
    OWNER_ID = int(os.getenv("OWNER_ID"))
    TARGET_GROUP = int(os.getenv("TARGET_GROUP"))
