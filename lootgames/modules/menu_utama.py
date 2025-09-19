# lootgames/modules/menu_utama.py
import logging
from pyrogram import Client, filters, handlers
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# ---------------- CONFIG ---------------- #
OWNER_ID = 123456789  # ganti dengan ID owner asli
TARGET_GROUP = -1001234567890  # opsional

# ---------------- LOGGING ---------------- #
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- STRUKTUR MENU ---------------- #
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

# ---------------- KEYBOARD BUILDER ---------------- #
def make_keyboard(menu_key: str) -> InlineKeyboardMarkup:
    logger.debug(f"[DEBUG] Membuat keyboard untuk menu: {menu_key}")
    buttons = []
    row = []
    for i, (text, callback) in enumerate(MENU_STRUCTURE[menu_key]["buttons"], start=1):
        row.append(InlineKeyboardButton(text, callback_data=callback))
        if i % 3 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

# ---------------- HANDLER COMMAND ---------------- #
async def open_menu(client: Client, message: Message):
    logger.info(f"[DEBUG] Command .menufish diterima dari {message.from_user.id}")

    # untuk testing, cek owner sementara di-comment
    # if message.from_user.id != OWNER_ID:
    #     await message.reply_text("⚠️ Kamu tidak punya akses ke menu ini.")
    #     return

    await message.reply_text(
        MENU_STRUCTURE["main"]["title"],
        reply_markup=make_keyboard("main")
    )

# ---------------- HANDLER CALLBACK ---------------- #
async def callback_handler(client: Client, callback_query: CallbackQuery):
    logger.info(f"[DEBUG] Callback diterima: {callback_query.data} dari {callback_query.from_user.id}")

    data = callback_query.data
    if data in MENU_STRUCTURE:
        await callback_query.message.edit_text(
            MENU_STRUCTURE[data]["title"],
            reply_markup=make_keyboard(data)
        )
        await callback_query.answer()
    else:
        await callback_query.answer("Menu tidak tersedia.", show_alert=True)
        logger.error(f"❌ Callback {data} tidak dikenal!")

# ---------------- REGISTER FUNCTION ---------------- #
def register(app: Client):
    logger.info("[INFO] Mendaftarkan handler menu_utama...")

    # MessageHandler
    app.add_handler(
        handlers.MessageHandler(open_menu, filters.command("menufish", prefixes="."))
    )

    # CallbackQueryHandler
    app.add_handler(
        handlers.CallbackQueryHandler(callback_handler)
    )

    logger.info("[INFO] Handler menu_utama berhasil terdaftar.")
