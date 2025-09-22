import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.modules import yapping, umpan, user_database
from lootgames.modules.gacha_fishing import fishing_loot

logger = logging.getLogger(__name__)
OWNER_ID = 6395738130
TARGET_GROUP = -1002904817520  # ganti sesuai supergroup bot

# ---------------- STATE ---------------- #
TRANSFER_STATE = {}       # user_id: {"jenis": "A/B/C/D"}
TUKAR_POINT_STATE = {}    # user_id: {"step": step, "jumlah_umpan": n}

# ---------------- MENU STRUCTURE ---------------- #
MENU_STRUCTURE = {
    "main": {"title": "📋 [Menu Utama]", "buttons": [
        ("UMPAN", "A"), ("YAPPING", "B"), ("REGISTER", "C"),
        ("🛒STORE", "D"), ("FISHING", "E"),
        ("Menu F","F"),("Menu G","G"),("Menu H","H"),
        ("Menu I","I"),("Menu J","J"),("Menu K","K"),("Menu L","L")
    ]},
    # UMPAN
    "A":{"title":"📋 Menu UMPAN","buttons":[
        ("COMMON 🐛","AA_COMMON"),("RARE 🐌","AA_RARE"),
        ("LEGENDARY 🧇","AA_LEGEND"),("MYTHIC 🐟","AA_MYTHIC"),
        ("⬅️ Kembali","main")
    ]},
    "AA_COMMON":{"title":"📋 TRANSFER UMPAN KE (Common)","buttons":[("Klik OK untuk transfer","TRANSFER_COMMON_OK"),("⬅️ Kembali","A")]},
    "AA_RARE":{"title":"📋 TRANSFER UMPAN KE (Rare)","buttons":[("Klik OK untuk transfer","TRANSFER_RARE_OK"),("⬅️ Kembali","A")]},
    "AA_LEGEND":{"title":"📋 TRANSFER UMPAN KE (Legend)","buttons":[("Klik OK untuk transfer","TRANSFER_LEGEND_OK"),("⬅️ Kembali","A")]},
    "AA_MYTHIC":{"title":"📋 TRANSFER UMPAN KE (Mythic)","buttons":[("Klik OK untuk transfer","TRANSFER_MYTHIC_OK"),("⬅️ Kembali","A")]},
    # FISHING
    "E":{"title":"🎣 FISHING","buttons":[("PILIH UMPAN","EE"),("⬅️ Kembali","main")]},
    "EE":{"title":"📋 PILIH UMPAN","buttons":[("Lanjut Pilih Jenis","EEE"),("⬅️ Kembali","E")]},
    "EEE":{"title":"📋 Pilih Jenis Umpan","buttons":[
        ("COMMON 🐛","EEE_COMMON"),("RARE 🐌","EEE_RARE"),
        ("LEGENDARY 🧇","EEE_LEGEND"),("MYTHIC 🐟","EEE_MYTHIC"),
        ("⬅️ Kembali","EE")
    ]},
    # REGISTER
    "C":{"title":"📋 MENU REGISTER","buttons":[("LANJUT","CC"),("⬅️ Kembali","main")]},
    "CC":{"title":"📋 APAKAH KAMU YAKIN INGIN MENJADI PLAYER LOOT?","buttons":[("PILIH OPSI","CCC"),("⬅️ Kembali","C")]},
    "CCC":{"title":"📋 PILIH OPSI:","buttons":[("YA","REGISTER_YES"),("TIDAK","REGISTER_NO")]},
    # STORE
    "D":{"title":"🛒STORE","buttons":[("BUY UMPAN","D1"),("SELL IKAN","D2"),("TUKAR POINT","D3"),("⬅️ Kembali","main")]},
    "D1":{"title":"📋 BUY UMPAN","buttons":[("D1A","D1A"),("⬅️ Kembali","D")]},
    "D2":{"title":"📋 SELL IKAN","buttons":[("D2A","D2A"),("⬅️ Kembali","D")]},
    "D3":{"title":"📋 TUKAR POINT","buttons":[("Lihat Poin & Tukar","D3A"),("⬅️ Kembali","D")]},
    "D3A":{"title":"📋 🔄 POINT CHAT","buttons":[("TUKAR 🔄 UMPAN","TUKAR_POINT"),("⬅️ Kembali","D3")]},
    # YAPPING
    "B": {"title":"📋 YAPPING","buttons":[
        ("Poin Pribadi","BB"),
        ("➡️ Leaderboard","BBB"),
        ("⬅️ Kembali","main")
    ]},
    "BB": {"title":"📋 Poin Pribadi","buttons":[("⬅️ Kembali","B")]},
    "BBB": {"title":"📋 Leaderboard Yapping","buttons":[("⬅️ Kembali","B")]},
}

# ---------------- KEYBOARD BUILDER ---------------- #
def make_keyboard(menu_key: str, user_id=None, page: int = 0) -> InlineKeyboardMarkup:
    buttons = []
    # --- LEADERBOARD ---
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
    # --- MENU UMPAN ---
    elif menu_key in ["A", "AA_COMMON", "AA_RARE", "AA_LEGEND", "AA_MYTHIC"] and user_id is not None:
        user_umpan = umpan.get_user(user_id)
        type_map = {"AA_COMMON": "A", "AA_RARE": "B", "AA_LEGEND": "C", "AA_MYTHIC": "D"}
        for text, callback in MENU_STRUCTURE.get(menu_key, {}).get("buttons", []):
            if callback in type_map:
                tkey = type_map[callback]
                jumlah = user_umpan[tkey]["umpan"]
                if user_id == OWNER_ID:
                    jumlah = 999
                text += f" ({jumlah} pcs)"
            buttons.append([InlineKeyboardButton(text, callback_data=callback)])
    # --- TUKAR POINT CHAT ---
    elif menu_key == "D3A" and user_id is not None:
        user_points = yapping.load_points().get(str(user_id), {}).get("points", 0)
        buttons.append([InlineKeyboardButton(f"Tukar Point Chat → Umpan (Anda: {user_points} pts)", callback_data="TUKAR_POINT")])
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="D3")])
    # --- GENERIC MENU ---
    else:
        for text, callback in MENU_STRUCTURE.get(menu_key, {}).get("buttons", []):
            buttons.append([InlineKeyboardButton(text, callback_data=callback)])
    return InlineKeyboardMarkup(buttons)

# ---------------- CALLBACK HANDLER ---------------- #
async def callback_handler(client: Client, callback_query: CallbackQuery):
    data, user_id = callback_query.data, callback_query.from_user.id
    try: await callback_query.answer()
    except: pass
    await asyncio.sleep(0.15)

    # TRANSFER
    if data.startswith("TRANSFER_"):
        jenis_map = {"COMMON": "A", "RARE": "B", "LEGEND": "C", "MYTHIC": "D"}
        jenis_key = data.replace("TRANSFER_", "").replace("_OK", "").upper()
        jenis = jenis_map.get(jenis_key, "A")
        TRANSFER_STATE[user_id] = {"jenis": jenis}
        try:
            await callback_query.message.edit_text(
                f"📥 Masukkan transfer format:\n@username jumlah\nJenis: {jenis_key}"
            )
        except: pass
        return

    # REGISTER
    if data == "REGISTER_YES":
        username = callback_query.from_user.username or f"user{user_id}"
        user_database.set_player_loot(user_id, True, username)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📋 Scan ID & USN", callback_data=f"SCAN_{user_id}")],[InlineKeyboardButton("⬅️ Kembali", callback_data="C")]])
        try:
            await callback_query.message.edit_text(
                f"🎉 Selamat @{username}\nAnda sudah menjadi Player Loot!",
                reply_markup=keyboard
            )
            await client.send_message(OWNER_ID, f"📢 User baru Player Loot!\n👤 @{username}\n🆔 {user_id}")
        except Exception as e:
            logger.error(f"Gagal notif owner/register: {e}")
        return
    elif data == "REGISTER_NO":
        try:
            await callback_query.message.edit_text(MENU_STRUCTURE["C"]["title"], reply_markup=make_keyboard("C", user_id))
        except: pass
        return

    # SCAN
    if data.startswith("SCAN_"):
        try:
            scan_user_id = int(data.split("_")[1])
            user_data = user_database.get_user_data(scan_user_id)
            uname = user_data.get("username", "Unknown")
            await callback_query.message.edit_text(
                f"🔍 Info User:\nUser ID: {scan_user_id}\nUsername: @{uname}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data="C")]]))
        except:
            await callback_query.answer("❌ Error scan user.", show_alert=True)
        return

    # POIN PRIBADI
    if data == "BB":
        points = yapping.load_points()
        user_data = points.get(str(user_id))
        if not user_data:
            text = "📊 Anda belum memiliki poin chat."
        else:
            text = f"📊 Poin Pribadi:\n- {user_data.get('username', 'Unknown')} - {user_data.get('points', 0)} pts | Level {user_data.get('level', 0)} {yapping.get_badge(user_data.get('level', 0))}"
        try:
            await callback_query.message.edit_text(text, reply_markup=make_keyboard("BB", user_id))
        except: pass
        return

    # LEADERBOARD
    if data == "BBB":
        await show_leaderboard(callback_query, user_id, 0)
        return
    if data.startswith("BBB_PAGE_"):
        page = int(data.split("_")[-1])
        await show_leaderboard(callback_query, user_id, page)
        return

    # TUKAR POINT CHAT
    if data == "TUKAR_POINT":
        points = yapping.load_points().get(str(user_id), {}).get("points", 0)
        if points < 100:
            await callback_query.answer("❌ Minimal 100 chat points untuk 1 umpan.", show_alert=True)
            return
        TUKAR_POINT_STATE[user_id] = {"step": 1, "jumlah_umpan": 0}
        try:
            await callback_query.message.edit_text(
                f"📊 Anda memiliki {points} chat points.\nBerapa umpan yang ingin ditukar? (1 umpan = 100 chat points)"
            )
        except: pass
        return

    if data == "TUKAR_CONFIRM" and user_id in TUKAR_POINT_STATE:
        jumlah_umpan = TUKAR_POINT_STATE[user_id]["jumlah_umpan"]
        total_points = jumlah_umpan * 100
        points_data = yapping.load_points()
        user_data = points_data.get(str(user_id), {})
        if user_data.get("points", 0) < total_points:
            await callback_query.answer("❌ Point chat tidak cukup.", show_alert=True)
            TUKAR_POINT_STATE.pop(user_id, None)
            return
        user_data["points"] -= total_points
        points_data[str(user_id)] = user_data
        yapping.save_points(points_data)
        umpan.add_umpan(user_id, "A", jumlah_umpan)
        try:
            await callback_query.message.edit_text(
                f"✅ Tukar berhasil! {jumlah_umpan} umpan telah ditambahkan.\nSisa chat points: {user_data['points']}",
                reply_markup=make_keyboard("D3", user_id)
            )
        except: pass
        TUKAR_POINT_STATE.pop(user_id, None)
        return

    # NAVIGATION
    if data in MENU_STRUCTURE:
        try:
            await callback_query.message.edit_text(MENU_STRUCTURE[data]["title"], reply_markup=make_keyboard(data, user_id))
        except: pass
        return

    # fallback
    try:
        await callback_query.answer("Menu tidak tersedia.", show_alert=True)
    except: pass

# ---------------- HANDLE TRANSFER & TUKAR MESSAGE ---------------- #
async def handle_transfer_message(client: Client, message: Message):
    user_id = message.from_user.id
    sender_username = message.from_user.username or f"user{user_id}"

    # TRANSFER
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
            umpan.init_user_if_missing(recipient_id, username.lstrip("@"))
            success, msg = umpan.transfer_umpan(user_id, recipient_id, jenis, amount)
            if success:
                await message.reply(f"✅ Transfer {amount} umpan ({jenis}) ke {username} berhasil!", reply_markup=make_keyboard("main", user_id))
                try:
                    await client.send_message(recipient_id, f"🎁 Kamu menerima {amount} umpan ({jenis}) dari @{sender_username}")
                except Exception as e:
                    logger.warning(f"Gagal notif penerima {recipient_id}: {e}")
                try:
                    recipient_data = umpan.get_user(recipient_id)
                    new_total = recipient_data[jenis]["umpan"]
                    await client.send_message(user_id, f"📌 Penerima sekarang punya {new_total} umpan tipe {jenis}.")
                except: pass
            else:
                await message.reply(f"❌ Transfer gagal: {msg}")
            TRANSFER_STATE.pop(user_id, None)
        except Exception as e:
            await message.reply(f"❌ Error: {e}")
            TRANSFER_STATE.pop(user_id, None)
        return

    # TUKAR POINT CHAT
    if TUKAR_POINT_STATE.get(user_id):
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
            await message.reply(
                f"📊 Anda yakin ingin menukar {jumlah_umpan} umpan?\n(100 chat points = 1 umpan)",
                reply_markup=keyboard
            )
        except ValueError:
            await message.reply("Format salah. Masukkan angka jumlah umpan.")
        return

# ---------------- REGISTER HANDLERS ---------------- #
def register(app: Client):
    # Menu utama
    app.add_handler(MessageHandler(open_menu, filters.regex(r"^\.menufish$") & filters.private))
    app.add_handler(MessageHandler(open_menu_pm, filters.command("menu") & filters.private))
    # Transfer & tukar point chat
    app.add_handler(MessageHandler(handle_transfer_message, filters.text & filters.private))
    # Callback query
    app.add_handler(CallbackQueryHandler(callback_handler))
    logger.info("[MENU] Handler menu_utama terdaftar.")
