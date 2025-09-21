# lootgames/modules/menu_utama.py
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
    MessageEntity,
)
from pyrogram.enums import MessageEntityType
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.modules import yapping, umpan, user_database

logger = logging.getLogger(__name__)
OWNER_ID = 6395738130
TARGET_GROUP = -1002904817520  # ganti ke group id target

# ---------------- STATE ---------------- #
TRANSFER_STATE = {}       # user_id: {"jenis": "A/B/C/D"}
TUKAR_POINT_STATE = {}    # user_id: {"step": step, "jumlah_umpan": n}

# ---------------- EMOJI PREMIUM ---------------- #
FISHING_EMOJI = {"char": "🎣", "id": 5463406036410969564}
CATCH_EMOJI   = {"char": "🤩", "id": 6235295024817379885}

async def send_single_emoji(client: Client, chat_id: int, emoji: dict, text: str = "", reply_to: int = None):
    """Kirim emoji premium dengan dummy ⬛"""
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
    return await client.send_message(chat_id, full_text, entities=entities, reply_to_message_id=reply_to)

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
    # REGISTER
    "C": {"title":"📋 MENU REGISTER","buttons":[("LANJUT","CC"),("⬅️ Kembali","main")]},
    "CC":{"title":"📋 APAKAH KAMU YAKIN INGIN MENJADI PLAYER LOOT?","buttons":[("PILIH OPSI","CCC"),("⬅️ Kembali","C")]},
    "CCC":{"title":"📋 PILIH OPSI:","buttons":[("YA","REGISTER_YES"),("TIDAK","REGISTER_NO")]},
    # STORE
    "D": {"title":"🛒STORE","buttons":[("BUY UMPAN","D1"),("SELL IKAN","D2"),("TUKAR POINT","D3"),("⬅️ Kembali","main")]},
    "D1":{"title":"📋 BUY UMPAN","buttons":[("D1A","D1A"),("⬅️ Kembali","D")]},
    "D2":{"title":"📋 SELL IKAN","buttons":[("D2A","D2A"),("⬅️ Kembali","D")]},
    "D3":{"title":"📋 TUKAR POINT","buttons":[("Lihat Poin & Tukar","D3A"),("⬅️ Kembali","D")]},
    "D3A":{"title":"📋 🔄 POINT CHAT","buttons":[("TUKAR 🔄 UMPAN","TUKAR_POINT"),("⬅️ Kembali","D3")]},
    # YAPPING
    "B": {"title":"📋 YAPPING","buttons":[("Poin Pribadi","BB"),("➡️ Leaderboard","BBB"),("⬅️ Kembali","main")]},
    "BB": {"title":"📋 Poin Pribadi","buttons":[("⬅️ Kembali","B")]},
    "BBB": {"title":"📋 Leaderboard Yapping","buttons":[("⬅️ Kembali","B")]}
}

# Tambahkan fishing confirm menu
for jenis in ["COMMON","RARE","LEGEND","MYTHIC"]:
    MENU_STRUCTURE[f"EEE_{jenis}"] = {
        "title": f"📋 Apakah kamu ingin memancing menggunakan umpan {jenis}?",
        "buttons": [
            ("✅ YA", f"FISH_CONFIRM_{jenis}"),
            ("❌ TIDAK", "EEE")
        ]
    }

# GENERIC MENU (F-L)
for letter in "FGHIJKL":
    key1, key2, key3 = letter, f"{letter}{letter}", f"{letter}{letter}{letter}"
    MENU_STRUCTURE[key1] = {"title": f"📋 Menu {key1}", "buttons": [(f"Menu {key2}", key2), ("⬅️ Kembali", "main")]}
    MENU_STRUCTURE[key2] = {"title": f"📋 Menu {key2}", "buttons": [(f"Menu {key3}", key3), ("⬅️ Kembali", key1)]}
    MENU_STRUCTURE[key3] = {"title": f"📋 Menu {key3} (Tampilan Terakhir)", "buttons": [("⬅️ Kembali", key2)]}

# ---------------- KEYBOARD BUILDER ---------------- #
def make_keyboard(menu_key: str, user_id=None, page: int = 0) -> InlineKeyboardMarkup:
    buttons = []
    # tampilkan dynamic sesuai menu
    if menu_key == "EEE" and user_id is not None:
        user_umpan = umpan.get_user(user_id) or {"A":{"umpan":0},"B":{"umpan":0},"C":{"umpan":0},"D":{"umpan":0}}
        if user_id == OWNER_ID:
            user_umpan = {"A":{"umpan":999},"B":{"umpan":999},"C":{"umpan":999},"D":{"umpan":999}}
        type_map = {"EEE_COMMON":("COMMON 🐛","A"),"EEE_RARE":("RARE 🐌","B"),"EEE_LEGEND":("LEGENDARY 🧇","C"),"EEE_MYTHIC":("MYTHIC 🐟","D")}
        for cb,(label,tkey) in type_map.items():
            jumlah = user_umpan.get(tkey,{}).get("umpan",0)
            buttons.append([InlineKeyboardButton(f"{label} ({jumlah} pcs)", callback_data=cb)])
        buttons.append([InlineKeyboardButton("⬅️ Kembali","EE")])
    else:
        for text,callback in MENU_STRUCTURE.get(menu_key,{}).get("buttons",[]):
            buttons.append([InlineKeyboardButton(text, callback_data=callback)])
    return InlineKeyboardMarkup(buttons)

# ---------------- CALLBACK HANDLER ---------------- #
async def callback_handler(client: Client, callback_query: CallbackQuery):
    data,user_id = callback_query.data, callback_query.from_user.id
    await callback_query.answer()

    # Fishing confirm
    if data.startswith("FISH_CONFIRM_"):
        jenis = data.replace("FISH_CONFIRM_","")
        jenis_map = {"COMMON":"A","RARE":"B","LEGEND":"C","MYTHIC":"D"}
        jenis_key = jenis_map.get(jenis,"A")
        username = callback_query.from_user.username or f"user{user_id}"

        # cek stok
        if user_id != OWNER_ID:
            user_data = umpan.get_user(user_id)
            if not user_data or user_data.get(jenis_key,{}).get("umpan",0)<=0:
                await callback_query.answer("❌ Umpan tidak cukup!",show_alert=True)
                return
            umpan.remove_umpan(user_id,jenis_key,1)

        # kirim lempar umpan ke group
        msg = await send_single_emoji(
            client,
            TARGET_GROUP,
            FISHING_EMOJI,
            f" @{username} ini sedang melempar umpan ({jenis}) untuk memancing.."
        )

        # info ke user
        await callback_query.message.edit_text(f"🎣 Kamu berhasil melempar umpan {jenis} ke kolam!")

        # setelah 10 detik → hasil ikan
        async def delayed():
            await asyncio.sleep(10)
            await send_single_emoji(
                client,
                TARGET_GROUP,
                CATCH_EMOJI,
                f" @{username} berhasil mendapatkan seekor ikan!",
                reply_to=msg.id
            )
        asyncio.create_task(delayed())
        return

    # generic menu
    if data in MENU_STRUCTURE:
        await callback_query.message.edit_text(MENU_STRUCTURE[data]["title"], reply_markup=make_keyboard(data,user_id))
    else:
        await callback_query.answer("Menu tidak tersedia.",show_alert=True)

# ---------------- REGISTER HANDLERS ---------------- #
def register(app: Client):
    app.add_handler(MessageHandler(open_menu, filters.regex(r"^\.menufish$") & filters.private))
    app.add_handler(MessageHandler(open_menu_pm, filters.command("menu") & filters.private))
    app.add_handler(MessageHandler(handle_transfer_message, filters.text & filters.private))
    app.add_handler(CallbackQueryHandler(callback_handler))
    logger.info("[MENU] Handler menu_utama terdaftar.")

# (open_menu, open_menu_pm, handle_transfer_message, dll tetap sama seperti versi sebelumnya)
