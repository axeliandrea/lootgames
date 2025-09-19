import importlib
import pkgutil
import logging
import asyncio
from pyrogram import Client
import lootgames.modules  # pastikan __init__.py ada
from lootgames.config import Config

# ---------------- Logging ---------------- #
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ---------------- Client ---------------- #
app = Client(
    "lootgames",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN if Config.BOT_TOKEN else None,
)

# ---------------- Loader ---------------- #
def load_modules():
    """Auto load semua modul dari lootgames/modules dan daftarkan handler."""
    for _, module_name, _ in pkgutil.iter_modules(lootgames.modules.__path__):
        mod = importlib.import_module(f"lootgames.modules.{module_name}")
        logging.info(f"✅ Loaded module: {module_name}")
        if hasattr(mod, "register"):
            try:
                mod.register(app)
                logging.info(f"🔌 Registered handlers for module: {module_name}")
            except Exception as e:
                logging.error(f"❌ Gagal register handler {module_name}: {e}")

# ---------------- Main ---------------- #
async def main():
    load_modules()
    await app.start()
    logging.info("🚀 LootGames Bot Started...")

    # Kirim notifikasi ke OWNER
    try:
        await app.send_message(
            Config.OWNER_ID,
            "🤖 LootGames Bot sudah aktif dan siap dipakai!"
        )
        logging.info("📢 Notifikasi start terkirim ke OWNER.")
    except Exception as e:
        logging.error(f"Gagal kirim notifikasi start: {e}")

    # biar bot tetap jalan
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
