# lootgames/lootgames/modules/menu_utama.py
import logging
from pyrogram import Client, filters, handlers
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

logger = logging.getLogger(__name__)

OWNER_ID = 6395738130  # ganti sesuai owner
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

# Generate submenus A..L -> AA..AAA
for letter in "ABCDEFGHIJKL":
    key1 = letter
    key2 = f"{letter}{letter}"
    key3 = f"{letter}{letter}{letter}"
    MENU_STRUCTURE[key1] = {"title": f"📋 Menu {key1}", "buttons": [(f"Menu {key2}", key2), ("⬅️ Kembali", "main")]}
    MENU_STRUCTURE[key2] = {"title": f"📋 Menu {key2}", "buttons": [(f"Menu {key3}", key3), ("⬅️ Kembali", key1)]}
    MENU_STRUCTURE[key3] = {"title": f"📋 Menu {key3} (Tampilan Terakhir)", "buttons": [("⬅️ Kembali", key2)]}

def make_keyboard(menu_key: str) -> InlineKeyboardMarkup:
    buttons, row = [], []
    for i, (text, callback) in enumerate(MENU_STRUCTURE[menu_key]["buttons"], start=1):
        row.append(InlineKeyboardButton(text, callback_data=callback))
        if i % 3 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

async def open_menu(client: Client, message: Message):
    logger.info(f"[DEBUG] Command .menufish diterima dari {message.from_user.id}")
    await message.reply_text(MENU_STRUCTURE["main"]["title"], reply_markup=make_keyboard("main"))

async def callback_handler(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    if data in MENU_STRUCTURE:
        await callback_query.message.edit_text(MENU_STRUCTURE[data]["title"], reply_markup=make_keyboard(data))
        await callback_query.answer()
    else:
        await callback_query.answer("Menu tidak tersedia.", show_alert=True)
        logger.error(f"❌ Callback {data} tidak dikenal!")

def register(app: Client):
    logger.info("[INFO] Mendaftarkan handler menu_utama...")
    app.add_handler(handlers.MessageHandler(open_menu, filters.command("menufish", prefixes=".")))
    app.add_handler(handlers.CallbackQueryHandler(callback_handler))
    logger.info("[INFO] Handler menu_utama berhasil terdaftar.")
