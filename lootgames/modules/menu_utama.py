# lootgames/modules/menu_utama.py
import logging
from pyrogram import Client, filters, handlers
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

logger = logging.getLogger(__name__)

OWNER_ID = 6395738130

# Simulasi database
USER_DB = {
    6395738130: {"umpan": 10},
}

# ---------------- MAIN MENU ---------------- #
MENU_STRUCTURE = {
    "main": {
        "title": "📋 [Menu Utama]",
        "buttons": [
            ("UMPAN", "A"),  # Menu A diganti UMPAN
            ("Menu B", "B"), ("Menu C", "C"), ("Menu D", "D"),
            ("Menu E", "E"), ("Menu F", "F"), ("Menu G", "G"),
            ("Menu H", "H"), ("Menu I", "I"), ("Menu J", "J"),
            ("Menu K", "K"), ("Menu L", "L"),
        ],
    }
}

# ---------------- CUSTOM MENU A → AA → AAA ---------------- #
MENU_STRUCTURE["A"] = {
    "title": "📋 Menu UMPAN",
    "buttons": [("Jumlah UMPAN", "AA"), ("⬅️ Kembali", "main")]
}

MENU_STRUCTURE["AA"] = {
    "title": "📋 Jumlah UMPAN",
    "buttons": [("TRANSFER UMPAN", "AAA"), ("⬅️ Kembali", "A")]
}

MENU_STRUCTURE["AAA"] = {
    "title": "📋 TRANSFER UMPAN KE",
    "buttons": [("Klik OK untuk transfer", "TRANSFER_OK"), ("⬅️ Kembali", "AA")]
}

# ---------------- GENERATOR MENU B–L ---------------- #
for letter in "BCDEFGHIJKL":
    key1 = letter
    key2 = f"{letter}{letter}"
    key3 = f"{letter}{letter}{letter}"
    MENU_STRUCTURE[key1] = {"title": f"📋 Menu {key1}", "buttons": [(f"Menu {key2}", key2), ("⬅️ Kembali", "main")]}
    MENU_STRUCTURE[key2] = {"title": f"📋 Menu {key2}", "buttons": [(f"Menu {key3}", key3), ("⬅️ Kembali", key1)]}
    MENU_STRUCTURE[key3] = {"title": f"📋 Menu {key3} (Tampilan Terakhir)", "buttons": [("⬅️ Kembali", key2)]}

# ---------------- KEYBOARD BUILDER ---------------- #
def make_keyboard(menu_key: str, user_id=None) -> InlineKeyboardMarkup:
    buttons = []
    for text, callback in MENU_STRUCTURE[menu_key]["buttons"]:
        if menu_key == "AA" and user_id is not None:
            u = USER_DB.get(user_id, {}).get("umpan", 0)
            text = f"Jumlah UMPAN: {u}"
        buttons.append([InlineKeyboardButton(text, callback_data=callback)])
    return InlineKeyboardMarkup(buttons)

# ---------------- MENU HANDLERS ---------------- #
async def open_menu(client: Client, message: Message):
    await message.reply_text(MENU_STRUCTURE["main"]["title"], reply_markup=make_keyboard("main", message.from_user.id))

async def callback_handler(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id

    if data == "TRANSFER_OK":
        sender = USER_DB.get(user_id, {"umpan": 0})
        recipient_id = 123456789  # contoh, bisa diganti input user
        amount = 1

        if sender["umpan"] >= amount:
            sender["umpan"] -= amount
            USER_DB.setdefault(recipient_id, {"umpan": 0})
            USER_DB[recipient_id]["umpan"] += amount
            text = f"✅ Transfer berhasil! Anda transfer {amount} umpan ke {recipient_id}"
        else:
            text = "❌ Umpan tidak cukup!"
        await callback_query.message.edit_text(text, reply_markup=make_keyboard("AA", user_id))
        await callback_query.answer()

    elif data in MENU_STRUCTURE:
        await callback_query.message.edit_text(
            MENU_STRUCTURE[data]["title"],
            reply_markup=make_keyboard(data, user_id)
        )
        await callback_query.answer()
    else:
        await callback_query.answer("Menu tidak tersedia.", show_alert=True)
        logger.error(f"❌ Callback {data} tidak dikenal!")

# ---------------- REGISTER ---------------- #
def register(app: Client):
    app.add_handler(handlers.MessageHandler(open_menu, filters.command("menufish", prefixes=".")))
    app.add_handler(handlers.CallbackQueryHandler(callback_handler))
