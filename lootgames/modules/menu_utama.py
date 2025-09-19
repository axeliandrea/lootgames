# lootgames/modules/menu_utama.py
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from lootgames.config import Config

OWNER_ID = Config.OWNER_ID
TARGET_GROUP = Config.TARGET_GROUP  # tidak dipaksa; hanya info

# ---------------- Struktur menu (A -> AA -> AAA ... sampai L) ---------------- #
MENU_STRUCTURE = {
    "main": {
        "title": "📋 [Menu Utama]",
        "buttons": [
            ("Menu A", "A"), ("Menu B", "B"), ("Menu C", "C"), ("Menu D", "D"),
            ("Menu E", "E"), ("Menu F", "F"), ("Menu G", "G"), ("Menu H", "H"),
            ("Menu I", "I"), ("Menu J", "J"), ("Menu K", "K"), ("Menu L", "L"),
        ],
    }
}

# helper to generate levels programmatically for A..L with AA..AAA pattern
import string
for idx, letter in enumerate(list("ABCDEFGHIJKL")):
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
    buttons = []
    for text, callback in MENU_STRUCTURE[menu_key]["buttons"]:
        buttons.append([InlineKeyboardButton(text, callback_data=callback)])
    return InlineKeyboardMarkup(buttons)

# ---------------- Handlers ---------------- #
async def open_menu(client, message: Message):
    """Command handler untuk .menufish
       - Hanya OWNER dapat memanggil menu ini (aman)
       - Boleh dipanggil di mana saja (group/private) oleh OWNER
    """
    # pastikan dari user
    if not message.from_user:
        return

    # batasi hanya owner
    if message.from_user.id != OWNER_ID:
        return

    # optional: jika mau batasi ke TARGET_GROUP uncomment
    # if TARGET_GROUP and message.chat.id != TARGET_GROUP:
    #     await message.reply_text("Perintah hanya dapat digunakan di grup target.")
    #     return

    await message.reply_text(
        MENU_STRUCTURE["main"]["title"],
        reply_markup=make_keyboard("main")
    )

async def callback_handler(client, callback_query: CallbackQuery):
    data = callback_query.data
    if data in MENU_STRUCTURE:
        await callback_query.message.edit_text(
            MENU_STRUCTURE[data]["title"],
            reply_markup=make_keyboard(data)
        )
        await callback_query.answer()
    else:
        await callback_query.answer("Menu tidak tersedia.", show_alert=True)

# ---------------- Register function ---------------- #
def register(app):
    """
    Dipanggil oleh loader di __main__.py setelah import modul.
    Mendaftarkan MessageHandler dan CallbackQueryHandler ke client/app.
    """
    # Message handler: .menufish
    app.add_handler(
        MessageHandler(open_menu, filters.command("menufish", prefixes="."))
    )
    # CallbackQuery handler: inline buttons
    app.add_handler(
        CallbackQueryHandler(callback_handler)
    )
