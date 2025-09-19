# lootgames/modules/menu_utama.py
import logging
import asyncio
from pyrogram import Client, filters, handlers
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# import database
from lootgames.modules import database as db

logger = logging.getLogger(__name__)

OWNER_ID = 6395738130

# ---------------- STATE TRANSFER ---------------- #
TRANSFER_STATE = {}  # user_id: True jika menunggu input transfer

# ---------------- MAIN MENU ---------------- #
MENU_STRUCTURE = {
    "main": {
        "title": "📋 [Menu Utama]",
        "buttons": [
            ("UMPAN", "A"),
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
    "buttons": [
        ("TRANSFER UMPAN", "AAA"),
        ("⬅️ Kembali", "A")
    ]
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
    
    MENU_STRUCTURE[key1] = {
        "title": f"📋 Menu {key1}",
        "buttons": [
            (f"Menu {key2}", key2),
            ("⬅️ Kembali", "main")
        ]
    }
    
    MENU_STRUCTURE[key2] = {
        "title": f"📋 Menu {key2}",
        "buttons": [
            (f"Menu {key3}", key3),
            ("⬅️ Kembali", key1)
        ]
    }
    
    MENU_STRUCTURE[key3] = {
        "title": f"📋 Menu {key3} (Tampilan Terakhir)",
        "buttons": [
            ("⬅️ Kembali", key2)
        ]
    }

# ---------------- KEYBOARD BUILDER ---------------- #
def make_keyboard(menu_key: str, user_id=None) -> InlineKeyboardMarkup:
    buttons = []
    for text, callback in MENU_STRUCTURE[menu_key]["buttons"]:
        # Tampilkan jumlah total umpan di tombol TRANSFER UMPAN
        if menu_key == "AA" and user_id is not None and text == "TRANSFER UMPAN":
            user_data = db.get_user(user_id)
            total_umpan = sum(user_data["umpan"].values())
            display_text = f"{text} ({total_umpan})"
        else:
            display_text = text
        buttons.append([InlineKeyboardButton(display_text, callback_data=callback)])
    return InlineKeyboardMarkup(buttons)

# ---------------- MENU HANDLERS ---------------- #
async def open_menu(client: Client, message: Message):
    await message.reply_text(
        MENU_STRUCTURE["main"]["title"],
        reply_markup=make_keyboard("main", message.from_user.id)
    )

async def callback_handler(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id

    await callback_query.answer()  # jawaban awal supaya tombol tidak loading

    # Delay 2 detik untuk mencegah flood
    await asyncio.sleep(2)

    if data == "TRANSFER_OK":
        # Aktifkan mode input transfer untuk user
        TRANSFER_STATE[user_id] = True
        await callback_query.message.edit_text(
            "📥 Masukkan transfer dalam format:\n@username jumlah_umpan\nContoh: @axeliandrea 1",
            reply_markup=None
        )
        return

    elif data in MENU_STRUCTURE:
        await callback_query.message.edit_text(
            MENU_STRUCTURE[data]["title"],
            reply_markup=make_keyboard(data, user_id)
        )
    else:
        await callback_query.answer("Menu tidak tersedia.", show_alert=True)
        logger.error(f"❌ Callback {data} tidak dikenal!")

# ---------------- HANDLE TRANSFER MESSAGE ---------------- #
async def handle_transfer_message(client: Client, message: Message):
    user_id = message.from_user.id
    if not TRANSFER_STATE.get(user_id):
        return

    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            await message.reply("Format salah. Contoh: @axeliandrea 1")
            return

        username, amount = parts
        if not username.startswith("@"):
            await message.reply("Username harus diawali '@'. Contoh: @axeliandrea")
            return

        amount = int(amount)
        if amount <= 0:
            await message.reply("Jumlah harus lebih dari 0.")
            return

        # Ambil data penerima
        recipient_user = await client.get_users(username)
        recipient_id = recipient_user.id

        sender_data = db.get_user(user_id)
        total_umpan = sum(sender_data["umpan"].values())

        if total_umpan < amount:
            await message.reply("❌ Umpan tidak cukup!")
        else:
            # Kurangi umpan A/B/C dari pengirim secara berurutan
            remaining = amount
            for jenis in ["A", "B", "C"]:
                if sender_data["umpan"][jenis] >= remaining:
                    db.remove_umpan(user_id, jenis, remaining)
                    remaining = 0
                    break
                else:
                    sub = sender_data["umpan"][jenis]
                    db.remove_umpan(user_id, jenis, sub)
                    remaining -= sub

            # Tambah umpan ke penerima (default A)
            db.add_umpan(recipient_id, "A", amount)
            await message.reply(f"✅ Transfer berhasil! Anda transfer {amount} umpan ke {username}")

        TRANSFER_STATE[user_id] = False

    except Exception as e:
        await message.reply(f"❌ Error: {e}")
        TRANSFER_STATE[user_id] = False

# ---------------- REGISTER ---------------- #
def register(app: Client):
    app.add_handler(handlers.MessageHandler(open_menu, filters.command("menufish", prefixes=".")))
    app.add_handler(handlers.CallbackQueryHandler(callback_handler))
    app.add_handler(handlers.MessageHandler(handle_transfer_message))
