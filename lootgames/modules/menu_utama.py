# lootgames/modules/menu_utama.py
import logging
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from lootgames.config import Config

OWNER_ID = Config.OWNER_ID
TARGET_GROUP = Config.TARGET_GROUP  # tidak dipaksa; hanya info

logger = logging.getLogger(__name__)

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
for letter in list("ABCDEFGHIJKL"):
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
    for text, callback in MENU_STRUCTURE[menu_key]["buttons"]:
        buttons.append([InlineKeyboardButton(text, callback_data=callback)])
    return InlineKeyboardMarkup(buttons)

# ---------------- Handlers ---------------- #
async def open_menu(client, message: Message):
    if not message.from_user:
        logger.warning("⚠️ Pesan tidak punya from_user, dilewati.")
        return

    logger.info(f"📥 Command .menufish diterima dari {message.from_user.id} di chat {message.chat.id}")

    # batasi hanya owner
    if message.from_user.id != OWNER_ID:
        logger.warning(f"⛔ User {message.from_user.id} mencoba akses menu tanpa izin.")
        return

    logger.info("✅ Owner valid, menampilkan Menu Utama...")
    await message.reply_text(
        MENU_STRUCTURE["main"]["title"],
        reply_markup=make_keyboard("main")
    )

async def callback_handler(client, callback_query: CallbackQuery):
    data = callback_query.data
    logger.info(f"🔘 Callback ditekan: {data} oleh {callback_query.from_user.id}")

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
def register(app):
    logger.info("📝 Mendaftarkan handler menu_utama...")
    app.add_handler(MessageHandler(open_menu, filters.command("menufish", prefixes=".")))
    app.add_handler(CallbackQueryHandler(callback_handler))
    logger.info("✅ Handler menu_utama berhasil terdaftar.")
