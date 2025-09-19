# lootgames/modules/menu_utama.py
import logging
import asyncio
from pyrogram import Client, handlers
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# import database & yapping
from lootgames.modules import database as db
from lootgames.modules import yapping as yp

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
            ("YAPPING", "B"),
            ("Menu C", "C"), ("Menu D", "D"),
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

# ---------------- CUSTOM MENU B → BB → BBB ---------------- #
MENU_STRUCTURE["B"] = {
    "title": "📋 YAPPING",
    "buttons": [("Total Point Chat", "BB"), ("⬅️ Kembali", "main")]
}

MENU_STRUCTURE["BB"] = {
    "title": "📋 Total Point Chat",
    "buttons": [
        ("➡️ Next", "BBB"),
        ("⬅️ Kembali", "B")
    ]
}

MENU_STRUCTURE["BBB"] = {
    "title": "📋 Leaderboard Yapping",
    "buttons": [("⬅️ Kembali", "BB")]
}

# ---------------- GENERATOR MENU C → L ---------------- #
for letter in "CDEFGHIJKL":
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

    await callback_query.answer()
    await asyncio.sleep(1)

    # ---------------- TRANSFER ---------------- #
    if data == "TRANSFER_OK":
        TRANSFER_STATE[user_id] = True
        await callback_query.message.edit_text(
            "📥 Masukkan transfer dalam format:\n@username jumlah_umpan\nContoh: @axeliandrea 1",
            reply_markup=None
        )
        return

    # ---------------- YAPPING MENU ---------------- #
    if data == "BB":
        points = yp.load_points()
        text = "📊 Total Chat Points:\n\n"
        for uid, pdata in points.items():
            text += f"- {pdata['username']}: {pdata['points']} pts\n"
        await callback_query.message.edit_text(text, reply_markup=make_keyboard("BB", user_id))
        return

    elif data == "BBB":
        points = yp.load_points()
        text = yp.generate_leaderboard_page(points, 0)
        max_page = max(0, (len(points)-1)//10)
        keyboard = yp.leaderboard_keyboard(0, max_page)
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        return

    elif data.startswith("leaderboard_"):
        page = int(data.split("_")[1])
        points = yp.load_points()
        text = yp.generate_leaderboard_page(points, page)
        max_page = max(0, (len(points)-1)//10)
        keyboard = yp.leaderboard_keyboard(page, max_page)
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        return

    # ---------------- DEFAULT NAVIGATION ---------------- #
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

        recipient_user = await client.get_users(username)
        recipient_id = recipient_user.id

        sender_data = db.get_user(user_id)
        total_umpan = sum(sender_data["umpan"].values())

        if total_umpan < amount:
            await message.reply("❌ Umpan tidak cukup!")
        else:
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
