# lootgames/modules/menu_utama.py

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# ---------------- CONFIG ---------------- #
OWNER_ID = 6395738130
TARGET_GROUP = -1002904817520

# Struktur Menu (bertahap)
MENU_STRUCTURE = {
    "main": {
        "title": "📋 [Menu Utama]",
        "buttons": [
            ("Menu A", "A"),
            ("Menu B", "B"),
            ("Menu C", "C"),
            ("Menu D", "D"),
            ("Menu E", "E"),
            ("Menu F", "F"),
            ("Menu G", "G"),
            ("Menu H", "H"),
            ("Menu I", "I"),
            ("Menu J", "J"),
            ("Menu K", "K"),
            ("Menu L", "L"),
        ]
    },
    # Submenu A → AA
    "A": {
        "title": "📋 Menu A",
        "buttons": [("Menu AA", "AA"), ("⬅️ Kembali", "main")]
    },
    "AA": {
        "title": "📋 Menu AA",
        "buttons": [("Menu AAA", "AAA"), ("⬅️ Kembali", "A")]
    },
    "AAA": {
        "title": "📋 Menu AAA (Tampilan Terakhir)",
        "buttons": [("⬅️ Kembali", "AA")]
    },

    # Submenu B → BB
    "B": {
        "title": "📋 Menu B",
        "buttons": [("Menu BB", "BB"), ("⬅️ Kembali", "main")]
    },
    "BB": {
        "title": "📋 Menu BB",
        "buttons": [("Menu BBB", "BBB"), ("⬅️ Kembali", "B")]
    },
    "BBB": {
        "title": "📋 Menu BBB (Tampilan Terakhir)",
        "buttons": [("⬅️ Kembali", "BB")]
    },

    # Dan seterusnya untuk C → CC → CCC sampai L → LL → LLL
    "C": {
        "title": "📋 Menu C",
        "buttons": [("Menu CC", "CC"), ("⬅️ Kembali", "main")]
    },
    "CC": {
        "title": "📋 Menu CC",
        "buttons": [("Menu CCC", "CCC"), ("⬅️ Kembali", "C")]
    },
    "CCC": {
        "title": "📋 Menu CCC (Tampilan Terakhir)",
        "buttons": [("⬅️ Kembali", "CC")]
    },
    # ... kamu tinggal lanjutkan pola ini sampai "L" → "LL" → "LLL"
}


# Fungsi bikin keyboard
def make_keyboard(menu_key: str):
    buttons = []
    for text, callback in MENU_STRUCTURE[menu_key]["buttons"]:
        buttons.append([InlineKeyboardButton(text, callback_data=callback)])
    return InlineKeyboardMarkup(buttons)


# Command untuk buka menu
@Client.on_message(filters.command("menufish", prefixes="."))
async def open_menu(client: Client, message: Message):
    print(f"[DEBUG] Command diterima dari chat_id={message.chat.id}, user={message.from_user.id}")
    if message.chat.id != TARGET_GROUP:
        print(f"[DEBUG] Chat bukan target: {message.chat.id}")
        return
    if message.from_user and message.from_user.id != OWNER_ID:
        print(f"[DEBUG] Bukan owner: {message.from_user.id}")
        return

    await message.reply_text(
        MENU_STRUCTURE["main"]["title"],
        reply_markup=make_keyboard("main")
    )

# Callback handler
@Client.on_callback_query()
async def menu_handler(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    if data in MENU_STRUCTURE:
        await callback_query.message.edit_text(
            MENU_STRUCTURE[data]["title"],
            reply_markup=make_keyboard(data)
        )
        await callback_query.answer()
    else:
        await callback_query.answer("Menu tidak tersedia.", show_alert=True)

