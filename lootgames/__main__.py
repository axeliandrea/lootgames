import asyncio
import logging
from pyrogram import Client
from lootgames.modules import yapping

API_ID = 123456      # ganti dengan API_ID kamu
API_HASH = "xxxxxx"  # ganti dengan API_HASH kamu
BOT_TOKEN = "xxxxxx" # ganti dengan token botmu
OWNER_ID = 6395738130
ALLOWED_GROUP_ID = -1002904817520
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

app = Client("lootgames", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Register yapping manually
yapping.register(app)

async def main():
    await app.start()
    logger.info("🚀 Bot started!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
