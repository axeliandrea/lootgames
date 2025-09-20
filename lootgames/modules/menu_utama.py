import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.modules import yapping, umpan, user_database

logger = logging.getLogger(__name__)
OWNER_ID = 6395738130

# ---------------- STATE ---------------- #
TRANSFER_STATE = {}  # user_id: {"jenis": "COMMON/RARE/LEGEND/MYTHIC"}
TUKAR_POINT_STATE = {}  # user_id: {"step": step, "jumlah_umpan": n}

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
MENU_STRUCTURE["AA"] = {"title": "📋 Jumlah UMPAN", "buttons": [
    ("Common", "AA_COMMON"),
    ("Rare", "AA_RARE"),
    ("Legend", "AA_LEGEND"),
    ("Mythic", "AA_MYTHIC"),
    ("⬅️ Kembali", "A")
]}
MENU_STRUCTURE["AA_COMMON"] = {"title": "📋 TRANSFER UMPAN KE (Common)", "buttons": [("Klik OK untuk transfer", "TRANSFER_COMMON_OK"), ("⬅️ Kembali", "AA")]}
MENU_STRUCTURE["AA_RARE"]   = {"title": "📋 TRANSFER UMPAN KE (Rare)",   "buttons": [("Klik OK untuk transfer", "TRANSFER_RARE_OK"),   ("⬅️ Kembali", "AA")]}
MENU_STRUCTURE["AA_LEGEND"] = {"title": "📋 TRANSFER UMPAN KE (Legend)", "buttons": [("Klik OK untuk transfer", "TRANSFER_LEGEND_OK"), ("⬅️ Kembali", "AA")]}
MENU_STRUCTURE["AA_MYTHIC"] = {"title": "📋 TRANSFER UMPAN KE (Mythic)", "buttons": [("Klik OK untuk transfer", "TRANSFER_MYTHIC_OK"), ("⬅️ Kembali", "AA")]}

# ---------------- REGISTER MENU ---------------- #
MENU_STRUCTURE["C"] = {"title": "📋 MENU REGISTER", "buttons": [("LANJUT", "CC"), ("⬅️ Kembali", "main")]}
MENU_STRUCTURE["CC"] = {"title": "📋 APAKAH KAMU YAKIN INGIN MENJADI PLAYER LOOT?", "buttons": [("PILIH OPSI", "CCC"), ("⬅️ Kembali", "C")]}
MENU_STRUCTURE["CCC"] = {"title": "📋 PILIH OPSI:", "buttons": [("YA", "REGISTER_YES"), ("TIDAK", "REGISTER_NO")]}

# ---------------- STORE MENU ---------------- #
MENU_STRUCTURE["D"] = {"title": "🛒STORE", "buttons": [("BUY UMPAN", "D1"), ("SELL IKAN", "D2"), ("TUKAR POINT", "D3"), ("⬅️ Kembali", "main")]}
MENU_STRUCTURE["D1"] = {"title": "📋 BUY UMPAN", "buttons": [("D1A", "D1A"), ("⬅️ Kembali", "D")]}
MENU_STRUCTURE["D2"] = {"title": "📋 SELL IKAN", "buttons": [("D2A", "D2A"), ("⬅️ Kembali", "D")]}
MENU_STRUCTURE["D3"] = {"title": "📋 TUKAR POINT", "buttons": [("Lihat Poin & Tukar", "D3A"), ("⬅️ Kembali", "D")]}
MENU_STRUCTURE["D3A"] = {"title": "📋 Menu D3A", "buttons": [("Tukar Point Chat ke Umpan", "TUKAR_POINT"), ("⬅️ Kembali", "D3")]}

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

# ---------------- KEYBOARD BUILDER ---------------- #
def make_keyboard(menu_key: str, user_id=None, page: int = 0) -> InlineKeyboardMarkup:
    buttons = []
    if menu_key == "BBB" and user_id is not None:
        points = yapping.load_points()
        sorted_points = sorted(points.items(), key=lambda x: x[1]["points"], reverse=True)
        total_pages = (len(sorted_points) - 1) // 10 if len(sorted_points) > 0 else 0
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"BBB_PAGE_{page-1}"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"BBB_PAGE_{page+1}"))
        if nav_buttons:
            buttons.append(nav_buttons)
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="B")])
    elif menu_key.startswith("AA") and user_id is not None:
        for text, callback in MENU_STRUCTURE.get(menu_key, {}).get("buttons", []):
            buttons.append([InlineKeyboardButton(text, callback_data=callback)])
    elif menu_key == "D3A" and user_id is not None:
        user_points = yapping.load_points().get(str(user_id), {}).get("points", 0)
        buttons.append([InlineKeyboardButton(f"Tukar Point Chat → Umpan (Anda: {user_points} pts)", callback_data="TUKAR_POINT")])
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="D3")])
    else:
        for text, callback in MENU_STRUCTURE.get(menu_key, {}).get("buttons", []):
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
    total_pages = (len(sorted_points) - 1) // 10 if len(sorted_points) > 0 else 0
    start, end = page*10, page*10+10
    text = f"🏆 Leaderboard Yapping (Page {page+1}/{total_pages+1}) 🏆\n\n"
    for i, (uid, pdata) in enumerate(sorted_points[start:end], start=start+1):
        text += f"{i}. {pdata.get('username','Unknown')} - {pdata.get('points',0)} pts | Level {pdata.get('level',0)} {yapping.get_badge(pdata.get('level',0))}\n"
    await callback_query.message.edit_text(text, reply_markup=make_keyboard("BBB", user_id, page))

# ---------------- CALLBACK HANDLER ---------------- #
async def callback_handler(client: Client, callback_query: CallbackQuery):
    data, user_id = callback_query.data, callback_query.from_user.id
    await callback_query.answer()
    await asyncio.sleep(0.2)

    # --- TRANSFER PER JENIS ---
    if data.startswith("TRANSFER_"):
        jenis_map = {
            "COMMON": "A",
            "RARE": "B",
            "LEGEND": "C",
            "MYTHIC": "D"
        }
        jenis_key = data.replace("TRANSFER_", "").replace("_OK", "").upper()
        jenis = jenis_map.get(jenis_key, "A")
        TRANSFER_STATE[user_id] = {"jenis": jenis}
        await callback_query.message.edit_text(
            f"📥 Masukkan transfer format:\n@username jumlah_umpan\nContoh: @axeliandrea 1\n\nJenis: {jenis_key}",
            reply_markup=None
        )
        logger.debug(f"[TRANSFER] User {user_id} masuk mode transfer jenis {jenis_key}")
        return

    # --- REGISTER ---
    if data == "REGISTER_YES":
        username = callback_query.from_user.username or f"user{user_id}"
        user_database.set_player_loot(user_id, True, username)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📋 Scan ID & USN", callback_data=f"SCAN_{user_id}")], [InlineKeyboardButton("⬅️ Kembali", callback_data="C")]])
        await callback_query.message.edit_text(
            f"🎉 Selamat @{username}\nID: {user_id}\nAnda sudah menjadi Player Loot!",
            reply_markup=keyboard
        )
        try:
            await client.send_message(OWNER_ID, f"📢 User baru Player Loot!\n👤 @{username}\n🆔 {user_id}")
        except Exception as e:
            logger.error(f"Gagal kirim notif OWNER: {e}")
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
            await callback_query.answer("❌ Error saat scan user.", show_alert=True)
            logger.error(f"SCAN ERROR: {e}")
        return

    # --- POIN PRIBADI ---
    if data == "BB":
        points = yapping.load_points()
        user_data = points.get(str(user_id))
        if not user_data:
            text = "📊 Anda belum memiliki poin chat."
        else:
            text = f"📊 Poin Pribadi:\n\n- {user_data.get('username','Unknown')} - {user_data.get('points',0)} pts | Level {user_data.get('level',0)} {yapping.get_badge(user_data.get('level',0))}"
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

    # --- TUKAR POINT CHAT KE UMPAN ---
    elif data == "TUKAR_POINT":
        points = yapping.load_points().get(str(user_id), {}).get("points", 0)
        if points < 100:
            await callback_query.answer("❌ Point chat tidak cukup minimal 100 untuk 1 umpan.", show_alert=True)
            return
        TUKAR_POINT_STATE[user_id] = {"step": 1, "jumlah_umpan": 0}
        await callback_query.message.edit_text(
            f"📊 Anda memiliki {points} chat points.\nBerapa umpan yang ingin ditukar? (1 umpan = 100 chat points)",
            reply_markup=None
        )
        return

    elif data == "TUKAR_CONFIRM" and user_id in TUKAR_POINT_STATE:
        jumlah_umpan = TUKAR_POINT_STATE[user_id]["jumlah_umpan"]
        total_points = jumlah_umpan * 100
        points_data = yapping.load_points()
        user_data = points_data.get(str(user_id), {})
        if user_data.get("points",0) < total_points:
            await callback_query.answer("❌ Point chat tidak cukup.", show_alert=True)
            TUKAR_POINT_STATE.pop(user_id, None)
            return
        # kurangi chat points
        user_data["points"] -= total_points
        points_data[str(user_id)] = user_data
        yapping.save_points(points_data)
        # tambah umpan Common sebagai default
        umpan.add_umpan(user_id, "A", jumlah_umpan)
        await callback_query.message.edit_text(
            f"✅ Tukar berhasil! {jumlah_umpan} umpan telah ditambahkan.\nSisa chat points: {user_data['points']}",
            reply_markup=make_keyboard("D3", user_id)
        )
        TUKAR_POINT_STATE.pop(user_id, None)
        return

    # --- GENERIC MENU NAVIGATION ---
    if data in MENU_STRUCTURE:
        await callback_query.message.edit_text(MENU_STRUCTURE[data]["title"], reply_markup=make_keyboard(data, user_id))
    else:
        await callback_query.answer("Menu tidak tersedia.", show_alert=True)
        logger.error(f"❌ Callback {data} tidak dikenal!")

# ---------------- HANDLE TRANSFER & TUKAR MESSAGE ---------------- #
async def handle_transfer_message(client: Client, message: Message):
    user_id = message.from_user.id
    # --- TRANSFER UMPAN ---
    if TRANSFER_STATE.get(user_id):
        try:
            jenis = TRANSFER_STATE[user_id]["jenis"]  # A/B/C/D
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
                TRANSFER_STATE.pop(user_id, None)
                return

            # --- OWNER TRANSFER ---
            if user_id == OWNER_ID:
                umpan.add_umpan(recipient_id, jenis, amount)
                await message.reply(f"✅ Transfer {amount} umpan ke {username} berhasil! (Owner unlimited)", reply_markup=make_keyboard("main", user_id))
                TRANSFER_STATE.pop(user_id, None)
                return

            # --- USER NORMAL ---
            sender_data = umpan.get_user(user_id)
            if sender_data["umpan"].get(jenis, 0) < amount:
                await message.reply("❌ Umpan tidak cukup!")
            else:
                umpan.remove_umpan(user_id, jenis, amount)
                umpan.add_umpan(recipient_id, jenis, amount)
                await message.reply(f"✅ Transfer {amount} umpan ke {username} berhasil!", reply_markup=make_keyboard("main", user_id))

            TRANSFER_STATE.pop(user_id, None)
        except Exception as e:
            await message.reply(f"❌ Error: {e}")
            TRANSFER_STATE.pop(user_id, None)
        return

    # --- TUKAR POINT CHAT KE UMPAN ---
    if TUKAR_POINT_STATE.get(user_id):
        try:
            jumlah_umpan = int(message.text.strip())
            if jumlah_umpan <= 0:
                await message.reply("Jumlah umpan harus > 0.")
                return
            points_data = yapping.load_points()
            user_data = points_data.get(str(user_id), {})
            if user_data.get("points",0) < jumlah_umpan*100:
                await message.reply("❌ Point chat tidak cukup.")
                return
            TUKAR_POINT_STATE[user_id]["jumlah_umpan"] = jumlah_umpan
            TUKAR_POINT_STATE[user_id]["step"] = 2
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ YA", callback_data="TUKAR_CONFIRM")],
                [InlineKeyboardButton("❌ Batal", callback_data="D3A")]
            ])
            await message.reply(f"Anda yakin ingin menukar {jumlah_umpan} umpan?\n(100 chat points = 1 umpan)", reply_markup=keyboard)
        except:
            await message.reply("Format salah. Masukkan angka jumlah umpan yang ingin ditukar.")

# ---------------- REGISTER HANDLER ---------------- #
def register(app: Client):
    """
    Pastikan fungsi ini dipanggil dari main bot (mis. register(app))
    """
    # pesan .menufish
    app.add_handler(MessageHandler(open_menu, filters.regex(r"^\.menufish$")))

    # PM /menu
    app.add_handler(MessageHandler(open_menu_pm, filters.private & filters.regex(r"^/menu$")))

    # callback query handler
    app.add_handler(CallbackQueryHandler(callback_handler))

    # pesan teks umum (dipakai untuk transfer & tukar)
    app.add_handler(MessageHandler(handle_transfer_message, filters.text))

    # jika modul umpan punya hook/topup
    try:
        umpan.register_topup(app)
    except Exception as e:
        logger.debug(f"umpan.register_topup gagal: {e}")
