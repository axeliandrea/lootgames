# lootgames/modules/menu_utama.py
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.modules import yapping, umpan, user_database

logger = logging.getLogger(__name__)
OWNER_ID = 6395738130

# ---------------- STATE ---------------- #
TRANSFER_STATE = {}  # user_id: True jika menunggu input transfer
TUKAR_STATE = {}     # user_id: True jika menunggu input tukar umpan

# ---------------- MAIN MENU ---------------- #
MENU_STRUCTURE = {
    "main": {
        "title": "📋 [Menu Utama]",
        "buttons": [
            ("UMPAN", "A"),
            ("YAPPING", "B"),
            ("REGISTER", "C"),
            ("🛒STORE", "D"),
            ("Menu E", "E"), ("Menu F", "F"), ("Menu G", "G"),
            ("Menu H", "H"), ("Menu I", "I"), ("Menu J", "J"),
            ("Menu K", "K"), ("Menu L", "L"),
        ],
    }
}

# ---------------- CUSTOM MENU ---------------- #
MENU_STRUCTURE["A"] = {"title": "📋 Menu UMPAN", "buttons": [("Jumlah UMPAN", "AA"), ("⬅️ Kembali", "main")]}
MENU_STRUCTURE["AA"] = {"title": "📋 Jumlah UMPAN", "buttons": [("TRANSFER UMPAN", "AAA"), ("⬅️ Kembali", "A")]}
MENU_STRUCTURE["AAA"] = {"title": "📋 TRANSFER UMPAN KE", "buttons": [("Klik OK untuk transfer", "TRANSFER_OK"), ("⬅️ Kembali", "AA")]}

MENU_STRUCTURE["C"] = {"title": "📋 MENU REGISTER", "buttons": [("LANJUT", "CC"), ("⬅️ Kembali", "main")]}
MENU_STRUCTURE["CC"] = {"title": "📋 APAKAH KAMU YAKIN INGIN MENJADI PLAYER LOOT?", "buttons": [("PILIH OPSI", "CCC"), ("⬅️ Kembali", "C")]}
MENU_STRUCTURE["CCC"] = {"title": "📋 PILIH OPSI:", "buttons": [("YA", "REGISTER_YES"), ("TIDAK", "REGISTER_NO")]}

MENU_STRUCTURE["D"] = {"title": "🛒STORE", "buttons": [("BUY UMPAN", "D1"), ("SELL IKAN", "D2"), ("TUKAR POINT", "D3"), ("⬅️ Kembali", "main")]}
MENU_STRUCTURE["D1"] = {"title": "📋 BUY UMPAN", "buttons": [("D1A", "D1A"), ("⬅️ Kembali", "D")]}
MENU_STRUCTURE["D2"] = {"title": "📋 SELL IKAN", "buttons": [("D2A", "D2A"), ("⬅️ Kembali", "D")]}
MENU_STRUCTURE["D3"] = {"title": "📋 TUKAR POINT", "buttons": [("My Point", "D3_MYPOINT"), ("⬅️ Kembali", "D")]}
MENU_STRUCTURE["D1A"] = {"title": "📋 Menu D1A", "buttons": [("D1B", "D1B"), ("⬅️ Kembali", "D1")]}
MENU_STRUCTURE["D2A"] = {"title": "📋 Menu D2A", "buttons": [("D2B", "D2B"), ("⬅️ Kembali", "D2")]}
MENU_STRUCTURE["D3A"] = {"title": "📋 Menu D3A", "buttons": [("D3B", "D3B"), ("⬅️ Kembali", "D3")]}
MENU_STRUCTURE["D1B"] = {"title": "📋 Menu D1B (Tampilan Terakhir)", "buttons": [("⬅️ Kembali", "D1")]}
MENU_STRUCTURE["D2B"] = {"title": "📋 Menu D2B (Tampilan Terakhir)", "buttons": [("⬅️ Kembali", "D2A")]}
MENU_STRUCTURE["D3B"] = {"title": "📋 Menu D3B (Tampilan Terakhir)", "buttons": [("⬅️ Kembali", "D3A")]}

# ---------------- GENERIC MENU (E-L) ---------------- #
for letter in "EFGHIJKL":
    key1, key2, key3 = letter, f"{letter}{letter}", f"{letter}{letter}{letter}"
    MENU_STRUCTURE[key1] = {"title": f"📋 Menu {key1}", "buttons": [(f"Menu {key2}", key2), ("⬅️ Kembali", "main")]}
    MENU_STRUCTURE[key2] = {"title": f"📋 Menu {key2}", "buttons": [(f"Menu {key3}", key3), ("⬅️ Kembali", key1)]}
    MENU_STRUCTURE[key3] = {"title": f"📋 Menu {key3} (Tampilan Terakhir)", "buttons": [("⬅️ Kembali", key2)]}

# ---------------- MENU YAPPING ---------------- #
MENU_STRUCTURE["B"] = {"title": "📋 YAPPING", "buttons": [("Poin Pribadi", "BB"), ("➡️ Leaderboard", "BBB"), ("⬅️ Kembali", "main")]}
MENU_STRUCTURE["BB"] = {"title": "📋 Poin Pribadi", "buttons": [("⬅️ Kembali", "B")]}
MENU_STRUCTURE["BBB"] = {"title": "📋 Leaderboard Yapping", "buttons": [("⬅️ Kembali", "B")]}

# ---------------- KEYBOARD ---------------- #
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
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="B")])
    else:
        for text, callback in MENU_STRUCTURE[menu_key]["buttons"]:
            if menu_key == "AA" and user_id is not None and text.startswith("TRANSFER UMPAN"):
                total = umpan.total_umpan(user_id)
                text = f"{text} ({total})"
            buttons.append([InlineKeyboardButton(text, callback_data=callback)])
    return InlineKeyboardMarkup(buttons)

# ---------------- MENU HANDLERS ---------------- #
async def open_menu(client: Client, message: Message):
    await message.reply(MENU_STRUCTURE["main"]["title"], reply_markup=make_keyboard("main", message.from_user.id))

async def open_menu_pm(client: Client, message: Message):
    user_id = message.from_user.id
    keyboard = make_keyboard("main", user_id)
    await message.reply("📋 Menu Utama:", reply_markup=keyboard)

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
    await asyncio.sleep(0.1)

    # --- REGISTER ---
    if data == "REGISTER_YES":
        username = callback_query.from_user.username or f"user{user_id}"
        user_database.set_player_loot(user_id, True, username)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Scan ID & USN", callback_data=f"SCAN_{user_id}")],
            [InlineKeyboardButton("⬅️ Kembali", callback_data="C")]
        ])
        try:
            await callback_query.message.edit_text(
                f"🎉 Selamat @{username}\nID: {user_id}\nAnda sudah menjadi Player Loot!",
                reply_markup=keyboard
            )
            await client.send_message(OWNER_ID, f"📢 User baru Player Loot!\n👤 @{username}\n🆔 {user_id}")
        except Exception as e:
            await callback_query.answer(f"❌ Gagal edit pesan: {e}", show_alert=True)
        return
    elif data == "REGISTER_NO":
        await callback_query.message.edit_text(MENU_STRUCTURE["C"]["title"], reply_markup=make_keyboard("C", user_id))
        return

    # --- SCAN ID & USN ---
    elif data.startswith("SCAN_"):
        try:
            scan_user_id = int(data.split("_")[1])
            user_data = user_database.get_user_data(scan_user_id)
            uname = user_data.get("username", "Unknown")
            await callback_query.message.edit_text(
                f"🔍 Info User:\n\nUser ID: {scan_user_id}\nUsername: @{uname}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data="C")]])
            )
        except Exception as e:
            await callback_query.answer(f"❌ Error saat scan user: {e}", show_alert=True)
        return

    # --- TRANSFER ---
    if data == "TRANSFER_OK":
        TRANSFER_STATE[user_id] = True
        await callback_query.message.edit_text(
            "📥 Masukkan transfer format:\n@username jumlah_umpan\nContoh: @axeliandrea 1",
            reply_markup=None
        )
        return

    # --- POIN PRIBADI ---
    if data == "BB":
        points = yapping.load_points()
        user_data = points.get(str(user_id))
        if not user_data:
            text = "📊 Anda belum memiliki poin chat."
        else:
            text = f"📊 Poin Pribadi:\n\n- {user_data.get('username','Unknown')} - {user_data.get('points',0)} pts | Level {user_data.get('level',0)} {yapping.get_badge(user_data.get('level',0))}"
        if text != callback_query.message.text:
            await callback_query.message.edit_text(text, reply_markup=make_keyboard("BB", user_id))
        return

    # --- LEADERBOARD ---
    elif data == "BBB":
        await show_leaderboard(callback_query, user_id, 0)
        return
    elif data.startswith("BBB_PAGE_"):
        page = int(data.split("_")[-1])
        await show_leaderboard(callback_query, user_id, page)
        return

    # --- TUKAR POINT → My Point ---
    if data == "D3_MYPOINT":
        points = yapping.load_points()
        user_data = points.get(str(user_id))
        if not user_data:
            text = "📊 My Point : Anda belum memiliki poin chat."
        else:
            uname = user_data.get("username", "Unknown")
            text = f"📊 My Point : @{uname} - {user_data.get('points',0)} pts | Level {user_data.get('level',0)} {yapping.get_badge(user_data.get('level',0))}"
        if text != callback_query.message.text:
            await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Kembali", callback_data="D3")],
                [InlineKeyboardButton("Tukar Umpan", callback_data="D3_TUKAR")]
            ]))
        return

    # --- TUKAR POINT → Tukar Umpan ---
    if data == "D3_TUKAR":
        TUKAR_STATE[user_id] = True
        await callback_query.message.edit_text(
            "📥 Masukkan jumlah umpan yang ingin ditukar (1 umpan = 100 poin chat):",
            reply_markup=None
        )
        return

    # --- GENERIC MENU NAVIGATION ---
    if data in MENU_STRUCTURE:
        if data != callback_query.message.text:  # prevent MESSAGE_NOT_MODIFIED
            await callback_query.message.edit_text(MENU_STRUCTURE[data]["title"], reply_markup=make_keyboard(data, user_id))
    else:
        await callback_query.answer("Menu tidak tersedia.", show_alert=True)

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

        recipient_id = user_database.get_user_id_by_username(username)
        if recipient_id is None:
            await message.reply(f"❌ Username {username} tidak ada di database!")
            TRANSFER_STATE[user_id] = False
            return

        # OWNER TRANSFER
        if user_id == OWNER_ID:
            umpan.add_umpan(recipient_id, amount)
            await message.reply(f"✅ Transfer {amount} umpan ke {username} berhasil!")
            TRANSFER_STATE[user_id] = False
            return

        # USER TRANSFER
        sender_total = umpan.total_umpan(user_id)
        if sender_total < amount:
            await message.reply(f"❌ Umpan tidak cukup! Anda memiliki {sender_total} umpan.")
            TRANSFER_STATE[user_id] = False
            return

        # Proses transfer
        umpan.add_umpan(recipient_id, amount)
        umpan.add_umpan(user_id, -amount)
        await message.reply(f"✅ Transfer {amount} umpan ke {username} berhasil!")
        TRANSFER_STATE[user_id] = False
    except Exception as e:
        await message.reply(f"❌ Terjadi error saat transfer: {e}")
        TRANSFER_STATE[user_id] = False

# ---------------- HANDLE TUKAR MESSAGE ---------------- #
async def handle_tukar_message(client: Client, message: Message):
    user_id = message.from_user.id
    if not TUKAR_STATE.get(user_id):
        return
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            await message.reply("Jumlah umpan harus > 0.")
            return

        points_data = yapping.load_points()
        user_data = points_data.get(str(user_id), {"points":0})
        required_points = amount * 100
        if user_data["points"] < required_points:
            await message.reply(f"❌ Poin tidak cukup. Anda memiliki {user_data['points']} pts, membutuhkan {required_points} pts.")
            return

        # Proses tukar
        umpan.add_umpan(user_id, amount)
        user_data["points"] -= required_points
        points_data[str(user_id)] = user_data
        yapping.save_points(points_data)

        await message.reply(f"✅ Tukar {required_points} poin menjadi {amount} umpan berhasil!")
        TUKAR_STATE[user_id] = False
    except ValueError:
        await message.reply("Format salah. Masukkan jumlah angka umpan yang ingin ditukar.")
    except Exception as e:
        await message.reply(f"❌ Terjadi error: {e}")
        TUKAR_STATE[user_id] = False

# ---------------- REGISTER HANDLERS ---------------- #
def register_handlers(app: Client):
    app.add_handler(MessageHandler(open_menu, filters.command("menu") & filters.private))
    app.add_handler(MessageHandler(open_menu_pm, filters.command("menu_pm") & filters.private))
    app.add_handler(MessageHandler(handle_transfer_message, filters.text & filters.private))
    app.add_handler(MessageHandler(handle_tukar_message, filters.text & filters.private))
    app.add_handler(CallbackQueryHandler(callback_handler))
