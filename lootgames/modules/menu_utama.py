# lootgames/modules/menu_utama.py
import logging
import asyncio
from pyrogram import Client, filters, handlers
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

from lootgames.modules import database as db
from lootgames.modules import yapping

logger = logging.getLogger(__name__)
OWNER_ID = 6395738130

# ---------------- STATE ---------------- #
TRANSFER_STATE = {}  # user_id: True jika menunggu input transfer
LEADER_PAGE = {}    # user_id: page terakhir di leaderboard

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

# ---------------- GENERATOR MENU C–L ---------------- #
for letter in "CDEFGHIJKL":
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

# ---------------- CUSTOM MENU B → BB → BBB ---------------- #
MENU_STRUCTURE["B"] = {
    "title": "📋 YAPPING",
    "buttons": [("Total Point Chat", "BB"), ("⬅️ Kembali", "main")]
}

MENU_STRUCTURE["BB"] = {
    "title": "📋 Total Point Chat",
    "buttons": [("➡️ Next", "BBB"), ("⬅️ Kembali", "B")]
}

MENU_STRUCTURE["BBB"] = {
    "title": "📋 Leaderboard Yapping",
    "buttons": [("⬅️ Kembali", "BB")]
}

# ---------------- KEYBOARD BUILDER ---------------- #
def make_keyboard(menu_key: str, user_id=None, page: int = 0) -> InlineKeyboardMarkup:
    buttons = []

    if menu_key == "BBB" and user_id is not None:
        points = yapping.load_points()
        sorted_points = sorted(points.items(), key=lambda x: x[1]["points"], reverse=True)
        total_pages = (len(sorted_points) - 1) // 10

        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"BBB_PAGE_{page-1}"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"BBB_PAGE_{page+1}"))
        if nav_buttons:
            buttons.append(nav_buttons)
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="BB")])
    else:
        for text, callback in MENU_STRUCTURE[menu_key]["buttons"]:
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
    logger.debug(f"[MENU] .menufish dipanggil oleh {message.from_user.id}")
    await message.reply_text(
        MENU_STRUCTURE["main"]["title"],
        reply_markup=make_keyboard("main", message.from_user.id)
    )

async def callback_handler(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id

    await callback_query.answer()
    await asyncio.sleep(0.5)

    # Handle transfer
    if data == "TRANSFER_OK":
        TRANSFER_STATE[user_id] = True
        await callback_query.message.edit_text(
            "📥 Masukkan transfer dalam format:\n@username jumlah_umpan\nContoh: @axeliandrea 1",
            reply_markup=None
        )
        logger.debug(f"[TRANSFER] User {user_id} masuk ke mode transfer")
        return

    # Handle BB menu → langsung open leaderboard page 0
    elif data == "BB":
        points = yapping.load_points()
        sorted_points = sorted(points.items(), key=lambda x: x[1]["points"], reverse=True)
        start = 0
        end = start + 10
        display_text = "🏆 Leaderboard Yapping 🏆\n\n"
        for i, (uid, pdata) in enumerate(sorted_points[start:end], start=start+1):
            display_text += f"{i}. {pdata.get('username','Unknown')} - {pdata.get('points',0)} pts | Level {pdata.get('level',0)} {yapping.get_badge(pdata.get('level',0))}\n"

        await callback_query.message.edit_text(display_text, reply_markup=make_keyboard("BBB", user_id, page=0))
        return

    # Handle leaderboard pagination
    elif data.startswith("BBB_PAGE_"):
        page = int(data.split("_")[-1])
        points = yapping.load_points()
        sorted_points = sorted(points.items(), key=lambda x: x[1]["points"], reverse=True)
        start = page * 10
        end = start + 10
        display_text = "🏆 Leaderboard Yapping 🏆\n\n"
        for i, (uid, pdata) in enumerate(sorted_points[start:end], start=start+1):
            display_text += f"{i}. {pdata.get('username','Unknown')} - {pdata.get('points',0)} pts | Level {pdata.get('level',0)} {yapping.get_badge(pdata.get('level',0))}\n"

        await callback_query.message.edit_text(display_text, reply_markup=make_keyboard("BBB", user_id, page))
        return

    # Default menu navigation
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
    app.add_handler(handlers.MessageHandler(open_menu, filters.regex(r"^\.menufish$")))
    app.add_handler(handlers.CallbackQueryHandler(callback_handler))
    app.add_handler(handlers.MessageHandler(handle_transfer_message, filters.text))
