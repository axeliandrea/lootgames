import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.modules import yapping, umpan, user_database
from lootgames.modules.gacha_fishing import fishing_loot

logger = logging.getLogger(__name__)
OWNER_ID = 6395738130
TARGET_GROUP = -1002904817520  # Ganti sesuai dengan supergroup bot

# ---------------- STATE ---------------- #
TRANSFER_STATE = {}  # user_id: {"jenis": "A/B/C/D"}
TUKAR_POINT_STATE = {}  # user_id: {"step": step, "jumlah_umpan": n}

# ---------------- MENU STRUCTURE ---------------- #
MENU_STRUCTURE = {
    "main": {
        "title": "📋 [Menu Utama]",
        "buttons": [
            ("UMPAN", "A"), ("YAPPING", "B"), ("REGISTER", "C"),
            ("🛒STORE", "D"), ("FISHING", "E"),
            ("Menu F", "F"), ("Menu G", "G"), ("Menu H", "H"),
            ("Menu I", "I"), ("Menu J", "J"), ("Menu K", "K"), ("Menu L", "L")
        ]
    },
    # UMPAN
    "A": {"title": "📋 Menu UMPAN", "buttons": [
        ("COMMON 🐛", "AA_COMMON"), ("RARE 🐌", "AA_RARE"),
        ("LEGENDARY 🧇", "AA_LEGEND"), ("MYTHIC 🐟", "AA_MYTHIC"),
        ("⬅️ Kembali", "main")
    ]},
    "AA_COMMON": {"title": "📋 TRANSFER UMPAN KE (Common)", "buttons": [
        ("Klik OK untuk transfer", "TRANSFER_COMMON_OK"), ("⬅️ Kembali", "A")
    ]},
    "AA_RARE": {"title": "📋 TRANSFER UMPAN KE (Rare)", "buttons": [
        ("Klik OK untuk transfer", "TRANSFER_RARE_OK"), ("⬅️ Kembali", "A")
    ]},
    "AA_LEGEND": {"title": "📋 TRANSFER UMPAN KE (Legend)", "buttons": [
        ("Klik OK untuk transfer", "TRANSFER_LEGEND_OK"), ("⬅️ Kembali", "A")
    ]},
    "AA_MYTHIC": {"title": "📋 TRANSFER UMPAN KE (Mythic)", "buttons": [
        ("Klik OK untuk transfer", "TRANSFER_MYTHIC_OK"), ("⬅️ Kembali", "A")
    ]},
    # FISHING
    "E": {"title": "🎣 FISHING", "buttons": [
        ("PILIH UMPAN", "EE"), ("⬅️ Kembali", "main")
    ]},
    "EE": {"title": "📋 PILIH UMPAN", "buttons": [
        ("Lanjut Pilih Jenis", "EEE"), ("⬅️ Kembali", "E")
    ]},
    "EEE": {"title": "📋 Pilih Jenis Umpan", "buttons": [
        ("COMMON 🐛", "EEE_COMMON"), ("RARE 🐌", "EEE_RARE"),
        ("LEGENDARY 🧇", "EEE_LEGEND"), ("MYTHIC 🐟", "EEE_MYTHIC"),
        ("⬅️ Kembali", "EE")
    ]},
    # REGISTER
    "C": {"title": "📋 MENU REGISTER", "buttons": [
        ("LANJUT", "CC"), ("⬅️ Kembali", "main")
    ]},
    "CC": {"title": "📋 APAKAH KAMU YAKIN INGIN MENJADI PLAYER LOOT?", "buttons": [
        ("PILIH OPSI", "CCC"), ("⬅️ Kembali", "C")
    ]},
    "CCC": {"title": "📋 PILIH OPSI:", "buttons": [
        ("YA", "REGISTER_YES"), ("TIDAK", "REGISTER_NO")
    ]},
    # STORE
    "D": {"title": "🛒STORE", "buttons": [
        ("BUY UMPAN", "D1"), ("SELL IKAN", "D2"), ("TUKAR POINT", "D3"),
        ("⬅️ Kembali", "main")
    ]},
    "D1": {"title": "📋 BUY UMPAN", "buttons": [("D1A", "D1A"), ("⬅️ Kembali", "D")]},
    "D2": {"title": "📋 SELL IKAN", "buttons": [("D2A", "D2A"), ("⬅️ Kembali", "D")]},
    "D3": {"title": "📋 TUKAR POINT", "buttons": [("Lihat Poin & Tukar", "D3A"), ("⬅️ Kembali", "D")]},
    "D3A": {"title": "📋 🔄 POINT CHAT", "buttons": [("TUKAR 🔄 UMPAN", "TUKAR_POINT"), ("⬅️ Kembali", "D3")]},
    # YAPPING
    "B": {"title": "📋 YAPPING", "buttons": [
        ("Poin Pribadi", "BB"), ("➡️ Leaderboard", "BBB"), ("⬅️ Kembali", "main")
    ]},
    "BB": {"title": "📋 Poin Pribadi", "buttons": [("⬅️ Kembali", "B")]},
    "BBB": {"title": "📋 Leaderboard Yapping", "buttons": [("⬅️ Kembali", "B")]}
}

# GENERIC MENU F-L
for l in "FGHIJKL":
    MENU_STRUCTURE[l] = {"title": f"📋 Menu {l}", "buttons": [(f"Menu {l*2}", l*2), ("⬅️ Kembali", "main")]}
    MENU_STRUCTURE[l*2] = {"title": f"📋 Menu {l*2}", "buttons": [(f"Menu {l*3}", l*3), ("⬅️ Kembali", l)]}
    MENU_STRUCTURE[l*3] = {"title": f"📋 Menu {l*3} (Tampilan Terakhir)", "buttons": [("⬅️ Kembali", l*2)]}

# FISH_CONFIRM
for jenis in ["COMMON", "RARE", "LEGEND", "MYTHIC"]:
    MENU_STRUCTURE[f"EEE_{jenis}"] = {
        "title": f"📋 Apakah kamu ingin memancing menggunakan umpan {jenis}?",
        "buttons": [("✅ YA", f"FISH_CONFIRM_{jenis}"), ("❌ TIDAK", "EEE")]
    }

# ---------------- KEYBOARD BUILDER ---------------- #
def make_keyboard(menu_key: str, user_id=None, page: int = 0) -> InlineKeyboardMarkup:
    buttons = []

    # --- LEADERBOARD --- (Yapping)
    if menu_key == "BBB" and user_id:
        points = yapping.load_points()
        sorted_pts = sorted(points.items(), key=lambda x: x[1]["points"], reverse=True)
        total_pages = (len(sorted_pts) - 1) // 10 if len(sorted_pts) > 0 else 0
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"BBB_PAGE_{page-1}"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"BBB_PAGE_{page+1}"))
        if nav_buttons:
            buttons.append(nav_buttons)
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="B")])

    # --- MENU UMPAN ---
    elif menu_key in ["A", "AA_COMMON", "AA_RARE", "AA_LEGEND", "AA_MYTHIC"] and user_id:
        user_umpan = umpan.get_user(user_id) or {"A": {"umpan": 0}, "B": {"umpan": 0}, "C": {"umpan": 0}, "D": {"umpan": 0}}
        type_map = {"AA_COMMON": "A", "AA_RARE": "B", "AA_LEGEND": "C", "AA_MYTHIC": "D"}
        for text, callback in MENU_STRUCTURE.get(menu_key, {}).get("buttons", []):
            if callback in type_map:
                tkey = type_map[callback]
                jumlah = 999 if user_id == OWNER_ID else user_umpan.get(tkey, {}).get("umpan", 0)
                text += f" ({jumlah} pcs)"
            buttons.append([InlineKeyboardButton(text, callback_data=callback)])

    # --- GENERIC MENU ---
    else:
        for text, callback in MENU_STRUCTURE.get(menu_key, {}).get("buttons", []):
            buttons.append([InlineKeyboardButton(text, callback_data=callback)])

    return InlineKeyboardMarkup(buttons)

# ---------------- CALLBACK HANDLER ---------------- #
async def callback_handler(client: Client, callback_query: CallbackQuery):
    data, user_id = callback_query.data, callback_query.from_user.id
    logger.info(f"[DEBUG] callback -> user:{user_id}, data:{data}")
    await callback_query.answer()
    await asyncio.sleep(0.1)

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
        except Exception:
            pass
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
        except Exception:
            pass
        return

    # Fallback: NAVIGATION
    if data in MENU_STRUCTURE:
        try:
            await callback_query.message.edit_text(MENU_STRUCTURE[data]["title"], reply_markup=make_keyboard(data, user_id))
        except Exception:
            pass
        return

# ---------------- SHOW LEADERBOARD ---------------- #
async def show_leaderboard(callback_query: CallbackQuery, user_id: int, page: int = 0):
    points = yapping.load_points()
    sorted_points = sorted(points.items(), key=lambda x: x[1]["points"], reverse=True)
    total_pages = (len(sorted_points) - 1) // 10 if len(sorted_points) > 0 else 0
    start, end = page * 10, page * 10 + 10
    text = f"🏆 Leaderboard Yapping (Page {page + 1}/{total_pages + 1}) 🏆\n\n"
    for i, (u, pdata) in enumerate(sorted_points[start:end], start=start + 1):
        text += f"{i}. {pdata.get('username', 'Unknown')} - {pdata.get('points', 0)} pts | Level {pdata.get('level', 0)} {yapping.get_badge(pdata.get('level', 0))}\n"
    try:
        await callback_query.message.edit_text(text, reply_markup=make_keyboard("BBB", user_id, page))
    except Exception:
        pass

# ---------------- MENU OPEN ---------------- #
async def open_menu(client: Client, message: Message):
    await message.reply(MENU_STRUCTURE["main"]["title"], reply_markup=make_keyboard("main", message.from_user.id))

async def open_menu_pm(client: Client, message: Message):
    uid = message.from_user.id
    await message.reply("📋 Menu Utama:", reply_markup=make_keyboard("main", uid))

# ---------------- REGISTER HANDLERS ---------------- #
def register(app: Client):
    app.add_handler(MessageHandler(open_menu, filters.regex(r"^\.menufish$") & filters.private))
    app.add_handler(MessageHandler(open_menu_pm, filters.command("menu") & filters.private))
    app.add_handler(CallbackQueryHandler(callback_handler))
    logger.info("[MENU] Handler menu_utama terdaftar.")
