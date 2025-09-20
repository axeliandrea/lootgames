import asyncio, importlib, pkgutil, logging
from pyrogram import Client
from .config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID, ALLOWED_GROUP_ID
import lootgames.modules

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Client("lootgames", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def load_modules():
    for _, module_name, _ in pkgutil.iter_modules(lootgames.modules.__path__):
        mod = importlib.import_module(f"lootgames.modules.{module_name}")
        logger.info(f"Loaded module: {module_name}")
        if hasattr(mod, "register"):
            try:
                mod.register(app)
                logger.info(f"Handlers registered for: {module_name}")
            except Exception as e:
                logger.error(f"Gagal register handler {module_name}: {e}")

async def main():
    logger.info("Starting LootGames bot...")
    load_modules()
    await app.start()
    logger.info(f"Bot started. Monitoring group: {ALLOWED_GROUP_ID}")
    await asyncio.Event().wait()  # keep running

if __name__=="__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
