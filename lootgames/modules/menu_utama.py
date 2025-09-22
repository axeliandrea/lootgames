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
# pastikan module gacha_fishing menyediakan async def fishing_loot(client, event, uname, uid, umpan_type)
try:
    from lootgames.modules.gacha_fishing import fishing_loot
except Exception:
    fishing_loot = None

logger = logging.getLogger(__name__)
OWNER_ID = 6395738130
TARGET_GROUP = -1002904817520  # ganti sesuai supergroup bot

# ---------------- STATE ---------------- #
TRANSFER_STATE = {}
TUKAR_POINT_STATE = {}

# ---------------- EMOJI PREMIUM ---------------- #
FISHING_EMOJI = {"char": "🎣", "id": 5463406036410969564}
CATCH_EMOJI = {"char": "🤩", "id": 6235295024817379885}

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
        ],
    },
    # --- UMPAN MENU ---
    "A": {"title": "📋 Menu UMPAN", "buttons": [
        ("COMMON 🐛", "AA_COMMON"),
        ("RARE 🐌", "AA_RARE"),
        ("LEGENDARY 🧇", "AA_LEGEND"),
        ("MYTHIC 🐟", "AA_MYTHIC"),
        ("⬅️ Kembali", "main"),
    ]},
    "AA_COMMON": {"title": "📋 TRANSFER UMPAN KE (Common)", "buttons": [("Klik OK untuk transfer", "TRANSFER_COMMON_OK"), ("⬅️ Kembali", "A")]},
    "AA_RARE": {"title": "📋 TRANSFER UMPAN KE (Rare)", "buttons": [("Klik OK untuk transfer", "TRANSFER_RARE_OK"), ("⬅️ Kembali", "A")]},
    "AA_LEGEND": {"title": "📋 TRANSFER UMPAN KE (Legend)", "buttons": [("Klik OK untuk transfer", "TRANSFER_LEGEND_OK"), ("⬅️ Kembali", "A")]},
    "AA_MYTHIC": {"title": "📋 TRANSFER UMPAN KE (Mythic)", "buttons": [("Klik OK untuk transfer", "TRANSFER_MYTHIC_OK"), ("⬅️ Kembali", "A")]},
    # --- FISHING MENU ---
    "E": {"title": "🎣 FISHING", "buttons": [
        ("PILIH UMPAN", "EE"),
        ("⬅️ Kembali", "main"),
    ]},
    "EE": {"title": "📋 PILIH UMPAN", "buttons": [
        ("Lanjut Pilih Jenis", "EEE"),
        ("⬅️ Kembali", "E"),
    ]},
    "EEE": {"title": "📋 Pilih Jenis Umpan", "buttons": [
        ("COMMON 🐛", "EEE_COMMON"),
        ("RARE 🐌", "EEE_RARE"),
        ("LEGENDARY 🧇", "EEE_LEGEND"),
        ("MYTHIC 🐟", "EEE_MYTHIC"),
        ("⬅️ Kembali", "EE"),
    ]},
    # --- REGISTER ---
    "C": {"title": "📋 MENU REGISTER", "buttons": [("LANJUT", "CC"), ("⬅️ Kembali", "main")]},
    "CC": {"title": "📋 APAKAH KAMU YAKIN INGIN MENJADI PLAYER LOOT?", "buttons": [("PILIH OPSI", "CCC"), ("⬅️ Kembali", "C")]},
    "CCC": {"title": "📋 PILIH OPSI:", "buttons": [("YA", "REGISTER_YES"), ("TIDAK", "REGISTER_NO")]},
    # --- STORE ---
    "D": {"title": "🛒STORE", "buttons": [("BUY UMPAN", "D1"), ("SELL IKAN", "D2"), ("TUKAR POINT", "D3"), ("⬅️ Kembali", "main")]},
    "D3": {"title": "📋 TUKAR POINT", "buttons": [("Lihat Poin & Tukar", "D3A"), ("⬅️ Kembali", "D")]},
    "D3A": {"title": "📋 🔄 POINT CHAT", "buttons": [("TUKAR 🔄 UMPAN", "TUKAR_POINT"), ("⬅️ Kembali", "D3")]},
    # --- YAPPING ---
    "B": {"title": "📋 YAPPING", "buttons": [("Poin Pribadi", "BB"), ("➡️ Leaderboard", "BBB"), ("⬅️ Kembali", "main")]},
}

# tambahkan fishing confirm
for jenis in ["COMMON", "RARE", "LEGEND", "MYTHIC"]:
    MENU_STRUCTURE[f"EEE_{jenis}"] = {
        "title": f"📋 Apakah kamu ingin memancing menggunakan umpan {jenis}?",
        "buttons": [
            ("✅ YA", f"FISH_CONFIRM_{jenis}"),
            ("❌ TIDAK", "EEE"),
        ],
    }

# ---------------- KEYBOARD BUILDER ---------------- #
def make_keyboard(menu_key: str, user_id=None, page: int = 0):
    buttons = []

    # --- LEADERBOARD ---
    if menu_key == "BBB" and user_id is not None:
        points = yapping.load_points()
        sorted_points = sorted(points.items(), key=lambda x: x[1].get("points", 0), reverse=True)
        total_pages = (len(sorted_points) - 1) // 10 if len(sorted_points) > 0 else 0

        # leaderboard text
        text = f"🏆 Leaderboard Yapping (Page {page+1}/{total_pages+1}) 🏆\n\n"
        start, end = page * 10, page * 10 + 10
        for i, (uid, pdata) in enumerate(sorted_points[start:end], start=start+1):
            uname = pdata.get("username", f"user{uid}")
            pts = pdata.get("points", 0)
            lvl = pdata.get("level", 0)
            text += f"{i}. @{uname} - {pts} pts | Lv {lvl} {yapping.get_badge(lvl)}\n"

        # navigation
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"BBB_PAGE_{page-1}"))
        if page < total_pages:
            nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"BBB_PAGE_{page+1}"))
        if nav:
            buttons.append(nav)
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="B")])

        return InlineKeyboardMarkup(buttons), text

    # --- POIN PRIBADI (BB) ---
    if menu_key == "BB" and user_id is not None:
        pdata = yapping.load_points().get(str(user_id), {})
        pts = pdata.get("points", 0)
        lvl = pdata.get("level", 0)
        uname = pdata.get("username", f"user{user_id}")
        text = f"📊 Poin Pribadi\n\nUsername: @{uname}\nPoints: {pts} pts\nLevel: {lvl} {yapping.get_badge(lvl)}"
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="B")])
        return InlineKeyboardMarkup(buttons), text

    # default
    for text, cb in MENU_STRUCTURE.get(menu_key, {}).get("buttons", []):
        buttons.append([InlineKeyboardButton(text, callback_data=cb)])
    return InlineKeyboardMarkup(buttons)

# ---------------- CALLBACK HANDLER ---------------- #
async def callback_handler(client: Client, cq: CallbackQuery):
    data, uid = cq.data, cq.from_user.id
    await cq.answer()

    # --- BB / BBB special ---
    if data == "BB":
        kb, txt = make_keyboard("BB", uid)
        try:
            await cq.message.edit_text(txt, reply_markup=kb)
        except:
            await cq.message.reply(txt, reply_markup=kb)
        return
    if data == "BBB":
        kb, txt = make_keyboard("BBB", uid, 0)
        try:
            await cq.message.edit_text(txt, reply_markup=kb)
        except:
            await cq.message.reply(txt, reply_markup=kb)
        return
    if data.startswith("BBB_PAGE_"):
        page = int(data.replace("BBB_PAGE_", ""))
        kb, txt = make_keyboard("BBB", uid, page)
        try:
            await cq.message.edit_text(txt, reply_markup=kb)
        except:
            await cq.message.reply(txt, reply_markup=kb)
        return

    # --- generic navigation ---
    if data in MENU_STRUCTURE:
        kb = make_keyboard(data, uid)
        if isinstance(kb, tuple):
            kb = kb[0]
        try:
            await cq.message.edit_text(MENU_STRUCTURE[data]["title"], reply_markup=kb)
        except:
            await cq.message.reply(MENU_STRUCTURE[data]["title"], reply_markup=kb)
        return

# ---------------- MENU OPEN ---------------- #
async def open_menu(client: Client, message: Message):
    await message.reply(MENU_STRUCTURE["main"]["title"], reply_markup=make_keyboard("main", message.from_user.id))

# ---------------- REGISTER HANDLERS ---------------- #
def register(app: Client):
    app.add_handler(MessageHandler(open_menu,filters.regex(r"^\.menufish$") & filters.private))
    app.add_handler(MessageHandler(open_menu_pm,filters.command("menu") & filters.private))
    app.add_handler(MessageHandler(handle_transfer_message,filters.text & filters.private))
    app.add_handler(CallbackQueryHandler(callback_handler))
    logger.info("[MENU] Handler menu_utama terdaftar.")

    

