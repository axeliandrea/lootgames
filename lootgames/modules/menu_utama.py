# lootgames/modules/menu_utama.py FINAL FULL
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.modules import yapping, umpan, user_database

logger = logging.getLogger(__name__)
OWNER_ID = 6395738130

# ---------------- STATE ---------------- #
TRANSFER_STATE = {}  # user_id: {"jenis": "A/B/C/D"}
TUKAR_POINT_STATE = {}  # user_id: {"step": step, "jumlah_umpan": n}

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
    # UMPAN MENU
    "A": {"title":"📋 Menu UMPAN","buttons":[
        ("COMMON 🐛","AA_COMMON"),
        ("RARE 🐌","AA_RARE"),
        ("LEGENDARY 🧇","AA_LEGEND"),
        ("MYTHIC 🐟","AA_MYTHIC"),
        ("⬅️ Kembali","main")
    ]},
    "AA_COMMON": {"title":"📋 TRANSFER UMPAN KE (Common)","buttons":[("Klik OK untuk transfer","TRANSFER_COMMON_OK"),("⬅️ Kembali","A")]},
    "AA_RARE": {"title":"📋 TRANSFER UMPAN KE (Rare)","buttons":[("Klik OK untuk transfer","TRANSFER_RARE_OK"),("⬅️ Kembali","A")]},
    "AA_LEGEND": {"title":"📋 TRANSFER UMPAN KE (Legend)","buttons":[("Klik OK untuk transfer","TRANSFER_LEGEND_OK"),("⬅️ Kembali","A")]},
    "AA_MYTHIC": {"title":"📋 TRANSFER UMPAN KE (Mythic)","buttons":[("Klik OK untuk transfer","TRANSFER_MYTHIC_OK"),("⬅️ Kembali","A")]},
    # REGISTER
    "C": {"title":"📋 MENU REGISTER","buttons":[("LANJUT","CC"),("⬅️ Kembali","main")]},
    "CC":{"title":"📋 APAKAH KAMU YAKIN INGIN MENJADI PLAYER LOOT?","buttons":[("PILIH OPSI","CCC"),("⬅️ Kembali","C")]},
    "CCC":{"title":"📋 PILIH OPSI:","buttons":[("YA","REGISTER_YES"),("TIDAK","REGISTER_NO")]},
    # STORE
    "D": {"title":"🛒STORE","buttons":[("BUY UMPAN","D1"),("SELL IKAN","D2"),("TUKAR POINT","D3"),("⬅️ Kembali","main")]},
    "D1":{"title":"📋 BUY UMPAN","buttons":[("D1A","D1A"),("⬅️ Kembali","D")]},
    "D2":{"title":"📋 SELL IKAN","buttons":[("D2A","D2A"),("⬅️ Kembali","D")]},
    "D3":{"title":"📋 TUKAR POINT","buttons":[("Lihat Poin & Tukar","D3A"),("⬅️ Kembali","D")]},
    "D3A":{"title":"📋 Menu D3A","buttons":[("Tukar Point Chat ke Umpan","TUKAR_POINT"),("⬅️ Kembali","D3")]},
    # YAPPING
    "B": {"title":"📋 YAPPING","buttons":[("Poin Pribadi","BB"),("➡️ Leaderboard","BBB"),("⬅️ Kembali","main")]},
    "BB": {"title":"📋 Poin Pribadi","buttons":[("⬅️ Kembali","B")]},
    "BBB": {"title":"📋 Leaderboard Yapping","buttons":[("⬅️ Kembali","B"])}
}

# GENERIC MENU (E-L)
for letter in "EFGHIJKL":
    key1, key2, key3 = letter, f"{letter}{letter}", f"{letter}{letter}{letter}"
    MENU_STRUCTURE[key1] = {"title": f"📋 Menu {key1}", "buttons": [(f"Menu {key2}", key2), ("⬅️ Kembali", "main")]}
    MENU_STRUCTURE[key2] = {"title": f"📋 Menu {key2}", "buttons": [(f"Menu {key3}", key3), ("⬅️ Kembali", key1)]}
    MENU_STRUCTURE[key3] = {"title": f"📋 Menu {key3} (Tampilan Terakhir)", "buttons": [("⬅️ Kembali", key2)]}

# ---------------- KEYBOARD BUILDER ---------------- #
def make_keyboard(menu_key: str, user_id=None, page: int = 0) -> InlineKeyboardMarkup:
    buttons = []

    # --- LEADERBOARD --- #
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

    # --- MENU UMPAN --- #
    elif menu_key in ["A","AA_COMMON","AA_RARE","AA_LEGEND","AA_MYTHIC"] and user_id is not None:
        user_umpan = umpan.get_user(user_id)
        type_map = {"AA_COMMON":"A","AA_RARE":"B","AA_LEGEND":"C","AA_MYTHIC":"D"}
        for text, callback in MENU_STRUCTURE.get(menu_key, {}).get("buttons", []):
            if callback in type_map:
                tkey = type_map[callback]
                jumlah = user_umpan[tkey]["umpan"]
                if user_id == OWNER_ID:
                    jumlah = 999
                text += f" ({jumlah} pcs)"
            buttons.append([InlineKeyboardButton(text, callback_data=callback)])

    # --- TUKAR POINT CHAT --- #
    elif menu_key == "D3A" and user_id is not None:
        user_points = yapping.load_points().get(str(user_id), {}).get("points", 0)
        buttons.append([InlineKeyboardButton(f"Tukar Point Chat → Umpan (Anda: {user_points} pts)", callback_data="TUKAR_POINT")])
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="D3")])

    # --- GENERIC MENU --- #
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

# ---------------- CALLBACK HANDLER ---------------- #
async def callback_handler(client: Client, callback_query: CallbackQuery):
    data, user_id = callback_query.data, callback_query.from_user.id
    await callback_query.answer()
    await asyncio.sleep(0.2)

    # --- TRANSFER UMPAN --- #
    if data.startswith("TRANSFER_"):
        jenis_map = {"COMMON":"A","RARE":"B","LEGEND":"C","MYTHIC":"D"}
        jenis_key = data.replace("TRANSFER_", "").replace("_OK", "").upper()
        jenis = jenis_map.get(jenis_key, "A")
        TRANSFER_STATE[user_id] = {"jenis": jenis}
        await callback_query.message.edit_text(
            f"📥 Masukkan transfer format:\n@username jumlah_umpan\nContoh: @axeliandrea 1\n\nJenis: {jenis_key}",
            reply_markup=None
        )
        return

    # --- TUKAR POINT CHAT --- #
    if data == "TUKAR_POINT":
        user_points = yapping.load_points().get(str(user_id), {}).get("points", 0)
        if user_points < 100:
            await callback_query.answer("❌ Point chat minimal 100 untuk 1 umpan.", show_alert=True)
            return
        TUKAR_POINT_STATE[user_id] = {"step": 1, "jumlah_umpan": 0}
        await callback_query.message.edit_text(
            f"📊 Anda memiliki {user_points} chat points.\nBerapa umpan yang ingin ditukar? (1 umpan = 100 chat points)"
        )
        return

    # --- KONFIRMASI TUKAR --- #
    if data == "TUKAR_CONFIRM" and user_id in TUKAR_POINT_STATE:
        jumlah_umpan = TUKAR_POINT_STATE[user_id]["jumlah_umpan"]
        points_data = yapping.load_points()
        user_data = points_data.get(str(user_id), {})
        total_points_needed = jumlah_umpan * 100
        if user_data.get("points", 0) < total_points_needed:
            await callback_query.answer("❌ Point chat tidak cukup.", show_alert=True)
            TUKAR_POINT_STATE.pop(user_id, None)
            return
        user_data["points"] -= total_points_needed
        points_data[str(user_id)] = user_data
        yapping.save_points(points_data)
        umpan.add_umpan(user_id, "A", jumlah_umpan)
        await callback_query.message.edit_text(
            f"✅ Tukar berhasil! {jumlah_umpan} umpan telah ditambahkan.\nSisa chat points: {user_data['points']}",
            reply_markup=make_keyboard("D3", user_id)
        )
        TUKAR_POINT_STATE.pop(user_id, None)
        return

    # --- REGISTER --- #
    if data == "REGISTER_YES":
        username = callback_query.from_user.username or f"user{user_id}"
        user_database.set_player_loot(user_id, True, username)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📋 Scan ID & USN", callback_data=f"SCAN_{user_id}")],
                                         [InlineKeyboardButton("⬅️ Kembali", callback_data="C")]])
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

# ---------------- HANDLE TRANSFER & TUKAR MESSAGE ---------------- #
async def handle_transfer_message(client: Client, message: Message):
    user_id = message.from_user.id
    sender_username = message.from_user.username or f"user{user_id}"

    # --- TRANSFER UMPAN --- #
    if TRANSFER_STATE.get(user_id):
        try:
            jenis = TRANSFER_STATE[user_id]["jenis"]
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

            if user_id == OWNER_ID:
                umpan.add_umpan(recipient_id, jenis, amount)
            else:
                sender_data = umpan.get_user(user_id)
                if sender_data[jenis]["umpan"] < amount:
                    await message.reply("❌ Umpan tidak cukup!")
                    return
                umpan.remove_umpan(user_id, jenis, amount)
                umpan.add_umpan(recipient_id, jenis, amount)

            await message.reply(f"✅ Transfer {amount} umpan ke {username} berhasil!", reply_markup=make_keyboard("main", user_id))
            try:
                await client.send_message(recipient_id, f"🎁 Kamu mendapatkan {amount} umpan dari (@{sender_username})")
            except Exception as e:
                logger.error(f"Gagal kirim notif ke penerima {recipient_id}: {e}")
            TRANSFER_STATE.pop(user_id, None)
        except Exception as e:
            await message.reply(f"❌ Error: {e}")
            TRANSFER_STATE.pop(user_id, None)
        return

    # --- INPUT JUMLAH TUKAR POINT --- #
    if TUKAR_POINT_STATE.get(user_id) and TUKAR_POINT_STATE[user_id]["step"] == 1:
        try:
            jumlah_umpan = int(message.text.strip())
            if jumlah_umpan <= 0:
                await message.reply("Jumlah umpan harus > 0.")
                return
            points_data = yapping.load_points()
            user_data = points_data.get(str(user_id), {})
            if user_data.get("points", 0) < jumlah_umpan * 100:
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
            await message.reply("Format salah. Masukkan angka jumlah umpan.")
        return

# ---------------- REGISTER HANDLERS ---------------- #
def register(app: Client):
    app.add_handler(MessageHandler(open_menu, filters.regex(r"^\.menufish$") & filters.private))
    app.add_handler(MessageHandler(open_menu_pm, filters.command("menu") & filters.private))
    app.add_handler(MessageHandler(handle_transfer_message, filters.text & filters.private))
    app.add_handler(CallbackQueryHandler(callback_handler))
    logger.info("[MENU] Handler menu_utama FULL terdaftar.")
