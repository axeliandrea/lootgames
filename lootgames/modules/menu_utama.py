import logging
import asyncio
from pyrogram import Client, handlers, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

from lootgames.modules import yapping, umpan, user_database

logger = logging.getLogger(__name__)
OWNER_ID = 6395738130

# ---------------- STATE ---------------- #
TRANSFER_STATE = {}  # user_id: True jika menunggu input transfer

# ---------------- MAIN MENU ---------------- #
MENU_STRUCTURE = {
    "main": {
        "title": "📋 [Menu Utama]",
        "buttons": [
            ("UMPAN", "A"),
            ("YAPPING", "B"),
            ("REGISTER", "C"),
            ("Menu D", "D"),
            ("Menu E", "E"), ("Menu F", "F"), ("Menu G", "G"),
            ("Menu H", "H"), ("Menu I", "I"), ("Menu J", "J"),
            ("Menu K", "K"), ("Menu L", "L"),
        ],
    }
}

# ---------------- CUSTOM MENU A → AA → AAA ---------------- #
MENU_STRUCTURE["A"] = {"title": "📋 Menu UMPAN", "buttons": [("Jumlah UMPAN", "AA"), ("⬅️ Kembali", "main")]}
MENU_STRUCTURE["AA"] = {"title": "📋 Jumlah UMPAN", "buttons": [("TRANSFER UMPAN", "AAA"), ("⬅️ Kembali", "A")]}
MENU_STRUCTURE["AAA"] = {"title": "📋 TRANSFER UMPAN KE", "buttons": [("Klik OK untuk transfer", "TRANSFER_OK"), ("⬅️ Kembali", "AA")]}

# ---------------- CUSTOM MENU REGISTER (C → CC → CCC) ---------------- #
MENU_STRUCTURE["C"] = {"title": "📋 MENU REGISTER", "buttons": [("LANJUT", "CC"), ("⬅️ Kembali", "main")]}
MENU_STRUCTURE["CC"] = {"title": "📋 APAKAH KAMU YAKIN INGIN MENJADI PLAYER LOOT?", "buttons": [("PILIH OPSI", "CCC"), ("⬅️ Kembali", "C")]}
MENU_STRUCTURE["CCC"] = {"title": "📋 PILIH OPSI:", "buttons": [("YA", "REGISTER_YES"), ("TIDAK", "REGISTER_NO")]}

# ---------------- GENERATOR MENU D–L ---------------- #
for letter in "DEFGHIJKL":
    key1, key2, key3 = letter, f"{letter}{letter}", f"{letter}{letter}{letter}"
    MENU_STRUCTURE[key1] = {"title": f"📋 Menu {key1}", "buttons": [(f"Menu {key2}", key2), ("⬅️ Kembali", "main")]}
    MENU_STRUCTURE[key2] = {"title": f"📋 Menu {key2}", "buttons": [(f"Menu {key3}", key3), ("⬅️ Kembali", key1)]}
    MENU_STRUCTURE[key3] = {"title": f"📋 Menu {key3} (Tampilan Terakhir)", "buttons": [("⬅️ Kembali", key2)]}

# ---------------- CUSTOM MENU B → BB → BBB ---------------- #
MENU_STRUCTURE["B"] = {"title": "📋 YAPPING", "buttons": [("Total Point Chat", "BB"), ("⬅️ Kembali", "main")]}
MENU_STRUCTURE["BB"] = {"title": "📋 Total Point Chat", "buttons": [("➡️ Leaderboard", "BBB"), ("⬅️ Kembali", "B")]}
MENU_STRUCTURE["BBB"] = {"title": "📋 Leaderboard Yapping", "buttons": [("⬅️ Kembali", "BB")]}

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
        if nav_buttons: buttons.append(nav_buttons)
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="BB")])
    else:
        for text, callback in MENU_STRUCTURE[menu_key]["buttons"]:
            if menu_key == "AA" and user_id is not None and text.startswith("TRANSFER UMPAN"):
                total = umpan.total_umpan(user_id)
                text = f"{text} ({total})"
            buttons.append([InlineKeyboardButton(text, callback_data=callback)])

    return InlineKeyboardMarkup(buttons)

# ---------------- MENU HANDLERS ---------------- #
async def open_menu(client: Client, message: Message):
    logger.debug(f"[MENU] .menufish dipanggil oleh {message.from_user.id}")
    await message.reply(MENU_STRUCTURE["main"]["title"], reply_markup=make_keyboard("main", message.from_user.id))

async def open_menu_pm(client: Client, message: Message):
    user_id = message.from_user.id
    keyboard = make_keyboard("main", user_id)
    await message.reply("📋 Menu Utama:", reply_markup=keyboard)
    logger.debug(f"[PM MENU] User {user_id} membuka Menu Utama di PM bot")

async def show_leaderboard(callback_query: CallbackQuery, user_id: int, page: int = 0):
    points = yapping.load_points()
    sorted_points = sorted(points.items(), key=lambda x: x[1]["points"], reverse=True)
    total_pages = (len(sorted_points) - 1) // 10
    start, end = page*10, page*10+10
    text = f"🏆 Leaderboard Yapping (Page {page+1}/{total_pages+1}) 🏆\n\n"
    for i, (uid, pdata) in enumerate(sorted_points[start:end], start=start+1):
        text += f"{i}. {pdata.get('username','Unknown')} - {pdata.get('points',0)} pts | Level {pdata.get('level',0)} {yapping.get_badge(pdata.get('level',0))}\n"
    await callback_query.message.edit_text(text, reply_markup=make_keyboard("BBB", user_id, page))

# ---------------- CALLBACK HANDLER ---------------- #
async def callback_handler(client: Client, callback_query: CallbackQuery):
    data, user_id = callback_query.data, callback_query.from_user.id
    await callback_query.answer()
    await asyncio.sleep(0.3)

    # --- REGISTER YA/TIDAK ---
    if data == "REGISTER_YES":
        username = callback_query.from_user.username or f"user{user_id}"
        user_database.set_player_loot(user_id, True, username)

        await callback_query.message.edit_text(
            f"🎉 Selamat {username}, anda sudah menjadi Player Loot!",
            reply_markup=make_keyboard("C", user_id)
        )

        try:
            await client.send_message(
                OWNER_ID,
                f"📢 User baru telah mendaftar Player Loot!\n\n"
                f"👤 Username: @{username}\n"
                f"🆔 User ID: {user_id}"
            )
        except Exception as e:
            logger.error(f"Gagal kirim notifikasi ke OWNER: {e}")
        return

    elif data == "REGISTER_NO":
        await callback_query.message.edit_text(
            MENU_STRUCTURE["C"]["title"],
            reply_markup=make_keyboard("C", user_id)
        )
        return

    # --- TRANSFER UMPAN ---
    if data == "TRANSFER_OK":
        TRANSFER_STATE[user_id] = True
        await callback_query.message.edit_text(
            "📥 Masukkan transfer format:\n@username jumlah_umpan\nContoh: @axeliandrea 1",
            reply_markup=None
        )
        logger.debug(f"[TRANSFER] User {user_id} masuk mode transfer")
        return

    # --- YAPPING MENU ---
    elif data == "BB":
        points = yapping.load_points()
        text = "📊 Total Chat Points:\n\n" if points else "📊 Total Chat Points kosong."
        for uid, pdata in points.items():
            text += f"- {pdata.get('username','Unknown')} - {pdata.get('points',0)} pts | Level {pdata.get('level',0)} {yapping.get_badge(pdata.get('level',0))}\n"
        await callback_query.message.edit_text(text, reply_markup=make_keyboard("BB", user_id))
        return
    elif data == "BBB":
        await show_leaderboard(callback_query, user_id, 0)
        return
    elif data.startswith("BBB_PAGE_"):
        page = int(data.split("_")[-1])
        await show_leaderboard(callback_query, user_id, page)
        return

    # --- MENU LAINNYA ---
    elif data in MENU_STRUCTURE:
        await callback_query.message.edit_text(MENU_STRUCTURE[data]["title"], reply_markup=make_keyboard(data, user_id))
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
            await message.reply("Format salah. Contoh: @username 1")
            return

        username, amount = parts
        if not username.startswith("@"):
            await message.reply("Username harus diawali '@'.")
            return
        amount = int(amount)
        if amount <= 0:
            await message.reply("Jumlah harus > 0.")
            return

        # --- Ambil recipient_id dari user_database (sinkron dengan umpan jika belum ada) ---
        recipient_id = user_database.get_user_id_by_username(username)
        if recipient_id is None:
            await message.reply(f"❌ Username {username} tidak ada di database!")
            TRANSFER_STATE[user_id] = False
            return

        sender_data = umpan.get_user(user_id)
        total_sender = sum(sender_data["umpan"].values())
        if total_sender < amount:
            await message.reply("❌ Umpan tidak cukup!")
        else:
            remaining = amount
            for jenis in ["A", "B", "C"]:
                if sender_data["umpan"][jenis] >= remaining:
                    umpan.remove_umpan(user_id, jenis, remaining)
                    remaining = 0
                    break
                else:
                    sub = sender_data["umpan"][jenis]
                    umpan.remove_umpan(user_id, jenis, sub)
                    remaining -= sub
            umpan.add_umpan(recipient_id, "A", amount)
            await message.reply(f"✅ Transfer {amount} umpan ke {username} berhasil!", reply_markup=make_keyboard("main", user_id))
            logger.debug(f"[TRANSFER] {user_id} → {recipient_id} ({amount} umpan)")

        TRANSFER_STATE[user_id] = False
    except Exception as e:
        await message.reply(f"❌ Error: {e}")
        TRANSFER_STATE[user_id] = False

# ---------------- REGISTER ---------------- #
def register(app: Client):
    app.add_handler(handlers.MessageHandler(open_menu, filters.regex(r"^\.menufish$")))
    app.add_handler(handlers.MessageHandler(open_menu_pm, filters.private & filters.regex(r"^/menu$")))
    app.add_handler(handlers.CallbackQueryHandler(callback_handler))
    app.add_handler(handlers.MessageHandler(handle_transfer_message, filters.text))
    umpan.register_topup(app)
