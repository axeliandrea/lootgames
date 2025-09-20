# lootgames/modules/menu_utama.py
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

from lootgames.modules import yapping, umpan, user_database

logger = logging.getLogger(__name__)
OWNER_ID = 6395738130

# ---------------- STATE ---------------- #
TRANSFER_STATE = {}  # user_id: menunggu transfer
TUKAR_STATE = {}     # user_id: menunggu tukar umpan

# ---------------- MENU STRUCTURE ---------------- #
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
    },
    # UMPAN
    "A": {"title": "📋 Menu UMPAN", "buttons": [("Jumlah UMPAN", "AA"), ("⬅️ Kembali", "main")]},
    "AA": {"title": "📋 Jumlah UMPAN", "buttons": [("TRANSFER UMPAN", "AAA"), ("⬅️ Kembali", "A")]},
    "AAA": {"title": "📋 TRANSFER UMPAN KE", "buttons": [("Klik OK untuk transfer", "TRANSFER_OK"), ("⬅️ Kembali", "AA")]},
    # REGISTER
    "C": {"title": "📋 MENU REGISTER", "buttons": [("LANJUT", "CC"), ("⬅️ Kembali", "main")]},
    "CC": {"title": "📋 APAKAH KAMU YAKIN INGIN MENJADI PLAYER LOOT?", "buttons": [("PILIH OPSI", "CCC"), ("⬅️ Kembali", "C")]},
    "CCC": {"title": "📋 PILIH OPSI:", "buttons": [("YA", "REGISTER_YES"), ("TIDAK", "REGISTER_NO")]},
    # STORE
    "D": {"title": "🛒STORE", "buttons": [("BUY UMPAN", "D1"), ("SELL IKAN", "D2"), ("TUKAR POINT", "D3"), ("⬅️ Kembali", "main")]},
    "D1": {"title": "📋 BUY UMPAN", "buttons": [("D1A", "D1A"), ("⬅️ Kembali", "D")]},
    "D1A": {"title": "📋 Menu D1A", "buttons": [("D1B", "D1B"), ("⬅️ Kembali", "D1")]},
    "D1B": {"title": "📋 Menu D1B (Tampilan Terakhir)", "buttons": [("⬅️ Kembali", "D1")]},
    "D2": {"title": "📋 SELL IKAN", "buttons": [("D2A", "D2A"), ("⬅️ Kembali", "D")]},
    "D2A": {"title": "📋 Menu D2A", "buttons": [("D2B", "D2B"), ("⬅️ Kembali", "D2")]},
    "D2B": {"title": "📋 Menu D2B (Tampilan Terakhir)", "buttons": [("⬅️ Kembali", "D2A")]},
    "D3": {"title": "📋 TUKAR POINT", "buttons": [("My Point", "D3_MYPOINT"), ("⬅️ Kembali", "D")]},
    "D3A": {"title": "📋 Menu D3A", "buttons": [("D3B", "D3B"), ("⬅️ Kembali", "D3")]},
    "D3B": {"title": "📋 Menu D3B (Tampilan Terakhir)", "buttons": [("⬅️ Kembali", "D3A")]},
    # YAPPING
    "B": {"title": "📋 YAPPING", "buttons": [("Poin Pribadi", "BB"), ("➡️ Leaderboard", "BBB"), ("⬅️ Kembali", "main")]},
    "BB": {"title": "📋 Poin Pribadi", "buttons": [("⬅️ Kembali", "B")]},
    "BBB": {"title": "📋 Leaderboard Yapping", "buttons": [("⬅️ Kembali", "B")]}
}

# GENERIC MENU E-L
for letter in "EFGHIJKL":
    k1, k2, k3 = letter, letter*2, letter*3
    MENU_STRUCTURE[k1] = {"title": f"📋 Menu {k1}", "buttons": [(f"Menu {k2}", k2), ("⬅️ Kembali", "main")]}
    MENU_STRUCTURE[k2] = {"title": f"📋 Menu {k2}", "buttons": [(f"Menu {k3}", k3), ("⬅️ Kembali", k1)]}
    MENU_STRUCTURE[k3] = {"title": f"📋 Menu {k3} (Tampilan Terakhir)", "buttons": [("⬅️ Kembali", k2)]}

# ---------------- KEYBOARD ---------------- #
def make_keyboard(menu_key: str, user_id=None, page: int = 0) -> InlineKeyboardMarkup:
    buttons = []
    if menu_key == "BBB" and user_id is not None:
        points = yapping.load_points()
        sorted_points = sorted(points.items(), key=lambda x: x[1]["points"], reverse=True)
        total_pages = (len(sorted_points)-1)//10
        if page > 0: buttons.append([InlineKeyboardButton("⬅️ Prev", callback_data=f"BBB_PAGE_{page-1}")])
        if page < total_pages: buttons[-1].append(InlineKeyboardButton("➡️ Next", callback_data=f"BBB_PAGE_{page+1}"))
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
    await message.reply("📋 Menu Utama:", reply_markup=make_keyboard("main", message.from_user.id))

async def show_leaderboard(callback_query: CallbackQuery, user_id: int, page: int = 0):
    points = yapping.load_points()
    sorted_points = sorted(points.items(), key=lambda x: x[1]["points"], reverse=True)
    total_pages = (len(sorted_points)-1)//10
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

    # REGISTER
    if data == "REGISTER_YES":
        username = callback_query.from_user.username or f"user{user_id}"
        user_database.set_player_loot(user_id, True, username)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📋 Scan ID & USN", callback_data=f"SCAN_{user_id}")],
                                         [InlineKeyboardButton("⬅️ Kembali", callback_data="C")]])
        await callback_query.message.edit_text(f"🎉 Selamat @{username}\nID: {user_id}\nAnda sudah menjadi Player Loot!", reply_markup=keyboard)
        await client.send_message(OWNER_ID, f"📢 User baru Player Loot!\n👤 @{username}\n🆔 {user_id}")
        return
    elif data == "REGISTER_NO":
        await callback_query.message.edit_text(MENU_STRUCTURE["C"]["title"], reply_markup=make_keyboard("C", user_id))
        return

    # SCAN ID & USN
    if data.startswith("SCAN_"):
        scan_user_id = int(data.split("_")[1])
        user_data = user_database.get_user_data(scan_user_id)
        uname = user_data.get("username","Unknown")
        await callback_query.message.edit_text(f"🔍 Info User:\n\nUser ID: {scan_user_id}\nUsername: @{uname}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data="C")]]))
        return

    # TRANSFER
    if data == "TRANSFER_OK":
        TRANSFER_STATE[user_id] = True
        await callback_query.message.edit_text("📥 Masukkan transfer format:\n@username jumlah_umpan\nContoh: @axeliandrea 1", reply_markup=None)
        return

    # POIN PRIBADI
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

    # LEADERBOARD
    if data == "BBB":
        await show_leaderboard(callback_query, user_id, 0)
        return
    if data.startswith("BBB_PAGE_"):
        page = int(data.split("_")[-1])
        await show_leaderboard(callback_query, user_id, page)
        return

    # TUKAR POINT
    if data == "D3_MYPOINT":
        points = yapping.load_points()
        user_data = points.get(str(user_id))
        uname = user_data.get("username","Unknown") if user_data else "Unknown"
        pts = user_data.get("points",0) if user_data else 0
        level = user_data.get("level",0) if user_data else 0
        text = f"📊 My Point : @{uname} - {pts} pts | Level {level} {yapping.get_badge(level)}"
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Kembali", callback_data="D3")],
            [InlineKeyboardButton("Tukar Umpan", callback_data="D3_TUKAR")]
        ]))
        return

    if data == "D3_TUKAR":
        TUKAR_STATE[user_id] = True
        await callback_query.message.edit_text("📥 Masukkan jumlah umpan yang ingin ditukar (1 umpan = 100 poin chat):", reply_markup=None)
        return

    # GENERIC NAVIGATION
    if data in MENU_STRUCTURE:
        if data != callback_query.message.text:
            await callback_query.message.edit_text(MENU_STRUCTURE[data]["title"], reply_markup=make_keyboard(data, user_id))
    else:
        await callback_query.answer("Menu tidak tersedia.", show_alert=True)

# ---------------- HANDLE TRANSFER ---------------- #
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
        recipient_id = user_database.get_user_id_by_username(username)
        if recipient_id is None:
            await message.reply(f"❌ Username {username} tidak ada di database!")
            TRANSFER_STATE[user_id] = False
            return
        sender_total = umpan.total_umpan(user_id)
        if user_id != OWNER_ID and sender_total < amount:
            await message.reply(f"❌ Umpan tidak cukup! Anda memiliki {sender_total} umpan.")
            TRANSFER_STATE[user_id] = False
            return
        umpan.add_umpan(recipient_id, amount)
        if user_id != OWNER_ID:
            umpan.add_umpan(user_id, -amount)
        await message.reply(f"✅ Transfer {amount} umpan ke {username} berhasil!")
        TRANSFER_STATE[user_id] = False
    except Exception as e:
        await message.reply(f"❌ Terjadi error saat transfer: {e}")
        TRANSFER_STATE[user_id] = False

# ---------------- HANDLE TUKAR ---------------- #
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
        required = amount*100
        if user_data["points"] < required:
            await message.reply(f"❌ Poin tidak cukup. Anda memiliki {user_data['points']} pts, membutuhkan {required} pts.")
            return
        umpan.add_umpan(user_id, amount)
        user_data["points"] -= required
        points_data[str(user_id)] = user_data
        yapping.save_points(points_data)
        await message.reply(f"✅ Tukar {required} poin menjadi {amount} umpan berhasil!")
        TUKAR_STATE[user_id] = False
    except ValueError:
        await message.reply("Format salah. Masukkan angka.")
    except Exception as e:
        await message.reply(f"❌ Terjadi error: {e}")
        TUKAR_STATE[user_id] = False

# ---------------- REGISTER HANDLERS ---------------- #
def register(app: Client):
    from pyrogram.handlers import MessageHandler, CallbackQueryHandler
    app.add_handler(MessageHandler(open_menu, filters.command("menu") & filters.private))
    app.add_handler(MessageHandler(open_menu_pm, filters.command("menu_pm") & filters.private))
    app.add_handler(MessageHandler(handle_transfer_message, filters.text & filters.private))
    app.add_handler(MessageHandler(handle_tukar_message, filters.text & filters.private))
    app.add_handler(CallbackQueryHandler(callback_handler))
