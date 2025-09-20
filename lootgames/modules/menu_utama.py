import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.modules import yapping, umpan, user_database

logger = logging.getLogger(__name__)
OWNER_ID = 6395738130

# ---------------- STATE ---------------- #
TRANSFER_STATE = {}       # user_id: {"jenis": "COMMON/RARE/LEGEND/MYTHIC"}
TUKAR_POINT_STATE = {}    # user_id: {"step": step, "jumlah_umpan": n}

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

# ---------------- MENU UMPAN ---------------- #
MENU_STRUCTURE["A"] = {
    "title": "📋 Menu UMPAN",
    "buttons": [
        ("Jumlah UMPAN", "AA"),
        ("⬅️ Kembali", "main")
    ]
}

MENU_STRUCTURE["AA"] = {
    "title": "📋 Jumlah UMPAN",
    "buttons": [
        ("Common", "AA_COMMON"),
        ("Rare", "AA_RARE"),
        ("Legend", "AA_LEGEND"),
        ("Mythic", "AA_MYTHIC"),
        ("⬅️ Kembali", "A")
    ]
}

MENU_STRUCTURE["AA_COMMON"] = {
    "title": "📋 TRANSFER UMPAN KE (Common)",
    "buttons": [
        ("Klik OK untuk transfer", "TRANSFER_COMMON_OK"),
        ("⬅️ Kembali", "AA")
    ]
}
MENU_STRUCTURE["AA_RARE"] = {
    "title": "📋 TRANSFER UMPAN KE (Rare)",
    "buttons": [
        ("Klik OK untuk transfer", "TRANSFER_RARE_OK"),
        ("⬅️ Kembali", "AA")
    ]
}
MENU_STRUCTURE["AA_LEGEND"] = {
    "title": "📋 TRANSFER UMPAN KE (Legend)",
    "buttons": [
        ("Klik OK untuk transfer", "TRANSFER_LEGEND_OK"),
        ("⬅️ Kembali", "AA")
    ]
}
MENU_STRUCTURE["AA_MYTHIC"] = {
    "title": "📋 TRANSFER UMPAN KE (Mythic)",
    "buttons": [
        ("Klik OK untuk transfer", "TRANSFER_MYTHIC_OK"),
        ("⬅️ Kembali", "AA")
    ]
}

# ---------------- MENU REGISTER ---------------- #
MENU_STRUCTURE["C"] = {"title": "📋 MENU REGISTER", "buttons": [("LANJUT", "CC"), ("⬅️ Kembali", "main")]}
MENU_STRUCTURE["CC"] = {"title": "📋 APAKAH KAMU YAKIN INGIN MENJADI PLAYER LOOT?", "buttons": [("PILIH OPSI", "CCC"), ("⬅️ Kembali", "C")]}
MENU_STRUCTURE["CCC"] = {"title": "📋 PILIH OPSI:", "buttons": [("YA", "REGISTER_YES"), ("TIDAK", "REGISTER_NO")]}

# ---------------- MENU D (STORE) ---------------- #
MENU_STRUCTURE["D"] = {"title": "🛒STORE", "buttons": [("BUY UMPAN", "D1"), ("SELL IKAN", "D2"), ("TUKAR POINT", "D3"), ("⬅️ Kembali", "main")]}
MENU_STRUCTURE["D1"] = {"title": "📋 BUY UMPAN", "buttons": [("D1A", "D1A"), ("⬅️ Kembali", "D")]}
MENU_STRUCTURE["D2"] = {"title": "📋 SELL IKAN", "buttons": [("D2A", "D2A"), ("⬅️ Kembali", "D")]}
MENU_STRUCTURE["D3"] = {"title": "📋 TUKAR POINT", "buttons": [("Lihat Poin & Tukar", "D3A"), ("⬅️ Kembali", "D")]}
MENU_STRUCTURE["D3A"] = {"title": "📋 Menu D3A", "buttons": [("Tukar Point Chat ke Umpan", "TUKAR_POINT"), ("⬅️ Kembali", "D3")]}  

MENU_STRUCTURE["D1A"] = {"title": "📋 Menu D1A", "buttons": [("D1B", "D1B"), ("⬅️ Kembali", "D1")]}
MENU_STRUCTURE["D2A"] = {"title": "📋 Menu D2A", "buttons": [("D2B", "D2B"), ("⬅️ Kembali", "D2")]}
MENU_STRUCTURE["D1B"] = {"title": "📋 Menu D1B (Tampilan Terakhir)", "buttons": [("⬅️ Kembali", "D1")]}
MENU_STRUCTURE["D2B"] = {"title": "📋 Menu D2B (Tampilan Terakhir)", "buttons": [("⬅️ Kembali", "D2A")]}

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
    elif menu_key.startswith("AA_") and user_id is not None:
        # submenu transfer umpan
        for text, callback in MENU_STRUCTURE[menu_key]["buttons"]:
            if callback.startswith("TRANSFER_"):
                jenis = callback.replace("TRANSFER_", "").replace("_OK", "").capitalize()
                total = umpan.total_umpan(user_id)  # bisa diubah sesuai jenis
                text = f"{text} (Anda: {total})"
            buttons.append([InlineKeyboardButton(text, callback_data=callback)])
    elif menu_key == "D3A" and user_id is not None:
        user_points = yapping.load_points().get(str(user_id), {}).get("points", 0)
        text_button = f"Tukar Point Chat → Umpan (Anda: {user_points} pts)"
        buttons.append([InlineKeyboardButton(text_button, callback_data="TUKAR_POINT")])
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="D3")])
    else:
        for text, callback in MENU_STRUCTURE.get(menu_key, {}).get("buttons", []):
            buttons.append([InlineKeyboardButton(text, callback_data=callback)])
    return InlineKeyboardMarkup(buttons)

# ---------------- CALLBACK HANDLER ---------------- #
async def callback_handler(client: Client, callback_query: CallbackQuery):
    data, user_id = callback_query.data, callback_query.from_user.id
    await callback_query.answer()
    await asyncio.sleep(0.2)

    # --- TRANSFER PER JENIS --- #
    if data.startswith("TRANSFER_"):
        jenis = data.replace("TRANSFER_", "").replace("_OK", "").upper()
        TRANSFER_STATE[user_id] = {"jenis": jenis}
        await callback_query.message.edit_text(
            f"📥 Masukkan transfer format:\n@username jumlah_umpan\nContoh: @axeliandrea 1\n\nJenis: {jenis}",
            reply_markup=None
        )
        logger.debug(f"[TRANSFER] User {user_id} masuk mode transfer jenis {jenis}")
        return

    # --- REGISTER --- #
    if data == "REGISTER_YES":
        username = callback_query.from_user.username or f"user{user_id}"
        user_database.set_player_loot(user_id, True, username)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 Scan ID & USN", callback_data=f"SCAN_{user_id}")
        ], [InlineKeyboardButton("⬅️ Kembali", callback_data="C")]])
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

    # --- GENERIC MENU NAVIGATION --- #
    if data in MENU_STRUCTURE:
        await callback_query.message.edit_text(MENU_STRUCTURE[data]["title"], reply_markup=make_keyboard(data, user_id))
    else:
        await callback_query.answer("Menu tidak tersedia.", show_alert=True)
        logger.error(f"❌ Callback {data} tidak dikenal!")

# ---------------- HANDLE TRANSFER MESSAGE ---------------- #
async def handle_transfer_message(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in TRANSFER_STATE:
        try:
            jenis = TRANSFER_STATE[user_id]["jenis"]  # COMMON / RARE / LEGEND / MYTHIC
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

            # OWNER unlimited transfer
            if user_id == OWNER_ID:
                umpan.add_umpan(recipient_id, jenis, amount)
                await message.reply(f"✅ Transfer {amount} umpan {jenis} ke {username} berhasil! (Owner unlimited)")
                TRANSFER_STATE.pop(user_id, None)
                return

            # User biasa
            sender_data = umpan.get_user(user_id)
            if sender_data["umpan"].get(jenis, 0) < amount:
                await message.reply("❌ Umpan tidak cukup!")
            else:
                umpan.remove_umpan(user_id, jenis, amount)
                umpan.add_umpan(recipient_id, jenis, amount)
                await message.reply(f"✅ Transfer {amount} umpan {jenis} ke {username} berhasil!")

            TRANSFER_STATE.pop(user_id, None)
        except Exception as e:
            await message.reply(f"❌ Error: {e}")
            TRANSFER_STATE.pop(user_id, None)

# ---------------- REGISTER HANDLER ---------------- #
def register(app: Client):
    app.add_handler(MessageHandler(callback_handler, filters=filters.create(lambda _, __, q: isinstance(q, CallbackQuery))))
    app.add_handler(MessageHandler(handle_transfer_message, filters.text))
    umpan.register_topup(app)
