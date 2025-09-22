# lootgames/modules/menu_utama.py
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, MessageEntity
from pyrogram.enums import MessageEntityType
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.modules import yapping, umpan, user_database
from lootgames.modules.gacha_fishing import fishing_loot  # import modul gacha
from lootgames.modules.fishing_helper import send_single_emoji, FISHING_EMOJI

logger = logging.getLogger(__name__)
OWNER_ID = 6395738130
TARGET_GROUP = -1002904817520  # ganti sesuai supergroup bot

# ---------------- STATE ---------------- #
TRANSFER_STATE = {}       # user_id: {"jenis": "A/B/C/D"}
TUKAR_POINT_STATE = {}    # user_id: {"step": step, "jumlah_umpan": n}

# ---------------- EMOJI PREMIUM ---------------- #
FISHING_EMOJI = {"char": "🎣", "id": 5463406036410969564}

# ---------------- MENU STRUCTURE ---------------- #
MENU_STRUCTURE = {
    "main": {
        "title": "📋 [Menu Utama]",
        "buttons": [
            ("UMPAN", "A"),
            ("YAPPING", "B"),
            ("REGISTER", "C"),
            ("🛒STORE", "D"),
            ("FISHING", "E"),
            ("Menu F", "F"), ("Menu G", "G"),
            ("Menu H", "H"), ("Menu I", "I"), ("Menu J", "J"),
            ("Menu K", "K"), ("Menu L", "L"),
        ],
    },
    # --- UMPAN MENU ---
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
    # --- FISHING MENU ---
    "E": {"title":"🎣 FISHING","buttons":[
        ("PILIH UMPAN","EE"),
        ("⬅️ Kembali","main")
    ]},
    "EE": {"title":"📋 PILIH UMPAN","buttons":[
        ("Lanjut Pilih Jenis","EEE"),
        ("⬅️ Kembali","E")
    ]},
    "EEE": {"title":"📋 Pilih Jenis Umpan","buttons":[
        ("COMMON 🐛","EEE_COMMON"),
        ("RARE 🐌","EEE_RARE"),
        ("LEGENDARY 🧇","EEE_LEGEND"),
        ("MYTHIC 🐟","EEE_MYTHIC"),
        ("⬅️ Kembali","EE")
    ]},
    # --- REGISTER ---
    "C": {"title":"📋 MENU REGISTER","buttons":[("LANJUT","CC"),("⬅️ Kembali","main")]},
    "CC":{"title":"📋 APAKAH KAMU YAKIN INGIN MENJADI PLAYER LOOT?","buttons":[("PILIH OPSI","CCC"),("⬅️ Kembali","C")]},
    "CCC":{"title":"📋 PILIH OPSI:","buttons":[("YA","REGISTER_YES"),("TIDAK","REGISTER_NO")]},
    # --- STORE ---
    "D": {"title":"🛒STORE","buttons":[("BUY UMPAN","D1"),("SELL IKAN","D2"),("TUKAR POINT","D3"),("⬅️ Kembali","main")]},
    "D1":{"title":"📋 BUY UMPAN","buttons":[("D1A","D1A"),("⬅️ Kembali","D")]},
    "D2":{"title":"📋 SELL IKAN","buttons":[("D2A","D2A"),("⬅️ Kembali","D")]},
    "D3":{"title":"📋 TUKAR POINT","buttons":[("Lihat Poin & Tukar","D3A"),("⬅️ Kembali","D")]},
    "D3A":{"title":"📋 🔄 POINT CHAT","buttons":[("TUKAR 🔄 UMPAN","TUKAR_POINT"),("⬅️ Kembali","D3")]},
    # --- YAPPING ---
    "B": {"title":"📋 YAPPING","buttons":[("Poin Pribadi","BB"),("➡️ Leaderboard","BBB"),("⬅️ Kembali","main")]},
    "BB": {"title":"📋 Poin Pribadi","buttons":[("⬅️ Kembali","B")]},
    "BBB": {"title":"📋 Leaderboard Yapping","buttons":[("⬅️ Kembali","B")]}
}

# GENERIC MENU (F-L)
for letter in "FGHIJKL":
    key1, key2, key3 = letter, f"{letter}{letter}", f"{letter}{letter}{letter}"
    MENU_STRUCTURE[key1] = {"title": f"📋 Menu {key1}", "buttons": [(f"Menu {key2}", key2), ("⬅️ Kembali", "main")]}
    MENU_STRUCTURE[key2] = {"title": f"📋 Menu {key2}", "buttons": [(f"Menu {key3}", key3), ("⬅️ Kembali", key1)]}
    MENU_STRUCTURE[key3] = {"title": f"📋 Menu {key3} (Tampilan Terakhir)", "buttons": [("⬅️ Kembali", key2)]}

# Tambahkan fishing confirm menu
for jenis in ["COMMON","RARE","LEGEND","MYTHIC"]:
    MENU_STRUCTURE[f"EEE_{jenis}"] = {
        "title": f"📋 Apakah kamu ingin memancing menggunakan umpan {jenis}?",
        "buttons": [
            ("✅ YA", f"FISH_CONFIRM_{jenis}"),
            ("❌ TIDAK", "EEE")
        ]
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

    # --- MENU UMPAN TERBARU ---
    elif menu_key in ["A","AA_COMMON","AA_RARE","AA_LEGEND","AA_MYTHIC"] and user_id is not None:
        user_umpan = umpan.get_user(user_id) or {"A":{"umpan":0},"B":{"umpan":0},"C":{"umpan":0},"D":{"umpan":0}}
        type_map = {"AA_COMMON":"A","AA_RARE":"B","AA_LEGEND":"C","AA_MYTHIC":"D"}
        for text, callback in MENU_STRUCTURE.get(menu_key, {}).get("buttons", []):
            if callback in type_map:
                tkey = type_map[callback]
                jumlah = user_umpan.get(tkey, {}).get("umpan", 0)
                if user_id == OWNER_ID:
                    jumlah = 999
                text += f" ({jumlah} pcs)"
            buttons.append([InlineKeyboardButton(text, callback_data=callback)])

    # --- MENU FISHING (EEE) ---
    elif menu_key == "EEE" and user_id is not None:
        user_umpan = umpan.get_user(user_id) or {"A":{"umpan":0},"B":{"umpan":0},"C":{"umpan":0},"D":{"umpan":0}}
        if user_id == OWNER_ID:
            user_umpan = {"A":{"umpan":999},"B":{"umpan":999},"C":{"umpan":999},"D":{"umpan":999}}
        type_map = {
            "EEE_COMMON": ("COMMON 🐛", "A"),
            "EEE_RARE": ("RARE 🐌", "B"),
            "EEE_LEGEND": ("LEGENDARY 🧇", "C"),
            "EEE_MYTHIC": ("MYTHIC 🐟", "D"),
        }
        for cb, (label, tkey) in type_map.items():
            jumlah = user_umpan.get(tkey, {}).get("umpan", 0)
            buttons.append([InlineKeyboardButton(f"{label} ({jumlah} pcs)", callback_data=cb)])
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="EE")])

    # --- TUKAR POINT CHAT ---
    elif menu_key == "D3A" and user_id is not None:
        user_points = yapping.load_points().get(str(user_id), {}).get("points", 0)
        buttons.append([InlineKeyboardButton(f"TUKAR 🔄 UMPAN (Anda: {user_points} pts)", callback_data="TUKAR_POINT")])
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="D3")])

    # --- GENERIC MENU ---
    else:
        for text, callback in MENU_STRUCTURE.get(menu_key, {}).get("buttons", []):
            buttons.append([InlineKeyboardButton(text, callback_data=callback)])

    return InlineKeyboardMarkup(buttons)

# ---------------- SEND PREMIUM EMOJI ---------------- #
async def send_single_emoji(client: Client, chat_id: int, emoji: dict, text: str = "", reply_to: int = None):
    dummy = "⬛"
    full_text = dummy + text
    entities = [
        MessageEntity(
            type=MessageEntityType.CUSTOM_EMOJI,
            offset=0,
            length=len(dummy),
            custom_emoji_id=int(emoji["id"])
        )
    ]
    try:
        return await client.send_message(chat_id, full_text, entities=entities, reply_to_message_id=reply_to)
    except Exception as e:
        logger.error(f"Gagal kirim emoji ke {chat_id}: {e}")
        try:
            await client.send_message(OWNER_ID, f"⚠️ Error kirim emoji ke {chat_id}: {e}")
        except:
            pass
        return None

# ---------------- CALLBACK HANDLER ---------------- #
async def callback_handler(client: Client, callback_query: CallbackQuery):
    data, user_id = callback_query.data, callback_query.from_user.id
    logger.info(f"[DEBUG] callback received -> user_id: {user_id}, data: {data}")
    await callback_query.answer()
    await asyncio.sleep(0.1)

    # --- FISHING CONFIRM ---
    if data.startswith("FISH_CONFIRM_"):
        jenis = data.replace("FISH_CONFIRM_","")
        jenis_map = {"COMMON":"A","RARE":"B","LEGEND":"C","MYTHIC":"D"}
        jenis_key = jenis_map.get(jenis,"A")
        username = callback_query.from_user.username or f"user{user_id}"

        if user_id != OWNER_ID:
            user_data = umpan.get_user(user_id)
            if not user_data or user_data.get(jenis_key,{}).get("umpan",0) <= 0:
                await callback_query.answer("❌ Umpan tidak cukup!", show_alert=True)
                return
            umpan.remove_umpan(user_id, jenis_key, 1)

        # panggil modul gacha untuk loot (perbaikan: tambahkan user_id)
        asyncio.create_task(fishing_loot(client, TARGET_GROUP, username, user_id))
        await callback_query.message.edit_text(f"🎣 Kamu berhasil melempar umpan {jenis} ke kolam!")
        return

    # --- LEADERBOARD PAGE NAV ---
    if data.startswith("BBB_PAGE_"):
        page = int(data.replace("BBB_PAGE_",""))
        await show_leaderboard(callback_query, user_id, page)
        return

    # --- GENERIC MENU NAVIGATION ---
    if data in MENU_STRUCTURE:
        await callback_query.message.edit_text(
            MENU_STRUCTURE[data]["title"],
            reply_markup=make_keyboard(data, user_id)
        )
        return

# ---------------- HANDLE TRANSFER & TUKAR MESSAGE ---------------- #
async def handle_transfer_message(client: Client, message: Message):
    user_id = message.from_user.id
    username_sender = message.from_user.username or f"user{user_id}"

    # --- TRANSFER UMPAN ---
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
                await client.send_message(recipient_id, f"🎁 Kamu mendapatkan {amount} umpan dari (@{username_sender})")
            except Exception as e:
                logger.error(f"Gagal kirim notif ke penerima {recipient_id}: {e}")
            TRANSFER_STATE.pop(user_id, None)
        except Exception as e:
            await message.reply(f"❌ Error: {e}")
            TRANSFER_STATE.pop(user_id, None)
        return

    # --- TUKAR POINT CHAT KE UMPAN ---
    if TUKAR_POINT_STATE.get(user_id):
        step = TUKAR_POINT_STATE[user_id].get("step",0)
        if step != 1:
            return
        try:
            jumlah_umpan = int(message.text.strip())
            if jumlah_umpan <= 0:
                await message.reply("Jumlah umpan harus > 0.")
                return
            points_data = yapping.load_points()
            user_data = points_data.get(str(user_id), {})
            if user_data.get("points",0) < jumlah_umpan*100:
                await message.reply(f"❌ Point chat tidak cukup. Anda memiliki {user_data.get('points',0)} pts, tapi butuh {jumlah_umpan*100} pts.")
                return
            TUKAR_POINT_STATE[user_id]["jumlah_umpan"] = jumlah_umpan
            TUKAR_POINT_STATE[user_id]["step"] = 2
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ YA", callback_data="TUKAR_CONFIRM")],
                [InlineKeyboardButton("❌ Batal", callback_data="D3A")]
            ])
            await message.reply(f"📊 Anda yakin ingin menukar {jumlah_umpan} umpan?\n(100 chat points = 1 umpan)", reply_markup=keyboard)
        except ValueError:
            await message.reply("Format salah. Masukkan angka jumlah umpan.")
        return

# ---------------- SHOW LEADERBOARD ---------------- #
async def show_leaderboard(callback_query: CallbackQuery, user_id: int, page: int = 0):
    points = yapping.load_points()
    sorted_points = sorted(points.items(), key=lambda x: x[1]["points"], reverse=True)
    total_pages = (len(sorted_points) - 1) // 10 if len(sorted_points) > 0 else 0
    start, end = page*10, page*10+10
    text = f"🏆 Leaderboard Yapping (Page {page+1}/{total_pages+1}) 🏆\n\n"
    for i, (uid, pdata) in enumerate(sorted_points[start:end], start=start+1):
        text += f"{i}. {pdata.get('username','Unknown')} - {pdata.get('points',0)} pts | Level {pdata.get('level',0)} {yapping.get_badge(pdata.get('level',0))}\n"
    await callback_query.message.edit_text(text, reply_markup=make_keyboard("BBB", user_id, page))

# ---------------- MENU OPEN ---------------- #
async def open_menu(client: Client, message: Message):
    await message.reply(MENU_STRUCTURE["main"]["title"], reply_markup=make_keyboard("main", message.from_user.id))

async def open_menu_pm(client: Client, message: Message):
    user_id = message.from_user.id
    keyboard = make_keyboard("main", user_id)
    await message.reply("📋 Menu Utama:", reply_markup=keyboard)

# ---------------- REGISTER HANDLERS ---------------- #
def register(app: Client):
    app.add_handler(MessageHandler(open_menu, filters.regex(r"^\.menufish$") & filters.private))
    app.add_handler(MessageHandler(open_menu_pm, filters.command("menu") & filters.private))
    app.add_handler(MessageHandler(handle_transfer_message, filters.text & filters.private))
    app.add_handler(CallbackQueryHandler(callback_handler))
    logger.info("[MENU] Handler menu_utama terdaftar.")
