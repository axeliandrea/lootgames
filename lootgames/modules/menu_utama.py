# lootgames/modules/menu_utama.py
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

from lootgames.config import Config

OWNER_ID = Config.OWNER_ID
TARGET_GROUP = Config.TARGET_GROUP  # hanya info

# ---------------- Logging ---------------- #
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------- Struktur menu ---------------- #
MENU_STRUCTURE = {
    "main": {
        "title": "📋 [Menu Utama]",
        "buttons": [
            ("Menu A", "A"), ("Menu B", "B"), ("Menu C", "C"),
            ("Menu D", "D"), ("Menu E", "E"), ("Menu F", "F"),
            ("Menu G", "G"), ("Menu H", "H"), ("Menu I", "I"),
            ("Menu J", "J"), ("Menu K", "K"), ("Menu L", "L"),
        ],
    }
}

# buat menu A..L -> AA..AAA pattern
for letter in "ABCDEFGHIJKL":
    key1 = letter
    key2 = f"{letter}{letter}"
    key3 = f"{letter}{letter}{letter}"

    MENU_STRUCTURE[key1] = {
        "title": f"📋 Menu {key1}",
        "buttons": [(f"Menu {key2}", key2), ("⬅️ Kembali", "main")]
    }
    MENU_STRUCTURE[key2] = {
        "title": f"📋 Menu {key2}",
        "buttons": [(f"Menu {key3}", key3), ("⬅️ Kembali", key1)]
    }
    MENU_STRUCTURE[key3] = {
        "title": f"📋 Menu {key3} (Tampilan Terakhir)",
        "buttons": [("⬅️ Kembali", key2)]
    }

# ---------------- Keyboard builder ---------------- #
def make_keyboard(menu_key: str) -> InlineKeyboardMarkup:
    logger.debug(f"🔧 Membuat keyboard untuk menu: {menu_key}")
    buttons = []
    row = []
    for i, (text, callback) in enumerate(MENU_STRUCTURE[menu_key]["buttons"], start=1):
        row.append(InlineKeyboardButton(text, callback_data=callback))
        if i % 3 == 0:  # 3 tombol per row
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

# ---------------- Handlers ---------------- #
async def open_menu(client: Client, message: Message):
    logger.debug(f"open_menu triggered by {message.from_user.id if message.from_user else 'unknown'} in chat {message.chat.id}")
    if not message.from_user:
        logger.warning("⚠️ Pesan tidak punya from_user, dilewati.")
        return

    # Batasi hanya owner
    if message.from_user.id != OWNER_ID:
        logger.warning(f"⛔ User {message.from_user.id} mencoba akses menu tanpa izin.")
        await message.reply_text("⚠️ Kamu tidak punya akses ke menu ini.")
        return

    logger.info(f"✅ Owner valid, menampilkan Menu Utama ke {message.from_user.id}")
    await message.reply_text(
        MENU_STRUCTURE["main"]["title"],
        reply_markup=make_keyboard("main")
    )

async def callback_handler(client: Client, callback_query: CallbackQuery):
    logger.debug(f"Callback received: {callback_query.data} from {callback_query.from_user.id}")

    data = callback_query.data
    if data in MENU_STRUCTURE:
        await callback_query.message.edit_text(
            MENU_STRUCTURE[data]["title"],
            reply_markup=make_keyboard(data)
        )
        await callback_query.answer()
        logger.info(f"✅ Menu {data} berhasil ditampilkan.")
    else:
        await callback_query.answer("Menu tidak tersedia.", show_alert=True)
        logger.error(f"❌ Callback {data} tidak dikenal!")

# ---------------- Register function ---------------- #
def register(app: Client):
    logger.info("📝 Mendaftarkan handler menu_utama...")

    # handler command .menufish
    @app.on_message(filters.command("menufish", prefixes="."))
    async def _open_menu(client, message):
        await open_menu(client, message)

    # handler callback query
    @app.on_callback_query()
    async def _callback(client, callback_query):
        await callback_handler(client, callback_query)

    logger.info("✅ Handler menu_utama berhasil terdaftar.")
