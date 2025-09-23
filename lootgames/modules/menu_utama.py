# lootgames/modules/menu_utama.py
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.modules import yapping, umpan, user_database
from lootgames.modules.gacha_fishing import fishing_loot

logger = logging.getLogger(__name__)
OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772  # ganti sesuai supergroup bot

# ---------------- STATE ---------------- #
TRANSFER_STATE = {}       # user_id: {"jenis": "A/B/C/D"}
TUKAR_POINT_STATE = {}    # user_id: {"step": step, "jumlah_umpan": n}

# ---------------- MENU STRUCTURE ---------------- #
MENU_STRUCTURE = {
    "main": {"title": "📋 [Menu Utama]", "buttons": [
        ("UMPAN", "A"), ("YAPPING", "B"), ("REGISTER", "C"),
        ("🛒STORE", "D"), ("FISHING", "E"),
        ("Menu F", "F"), ("Menu G", "G")
    ]},
    # UMPAN
    "A": {"title": "📋 Menu UMPAN", "buttons": [
        ("COMMON 🐛", "AA_COMMON"), ("RARE 🐌", "AA_RARE"),
        ("LEGENDARY 🧇", "AA_LEGEND"), ("MYTHIC 🐟", "AA_MYTHIC"),
        ("⬅️ Kembali", "main")
    ]},
    "AA_COMMON": {"title": "📋 TRANSFER UMPAN KE (Common)",
                  "buttons": [("Klik OK untuk transfer", "TRANSFER_COMMON_OK"), ("⬅️ Kembali", "A")]},
    "AA_RARE": {"title": "📋 TRANSFER UMPAN KE (Rare)",
                "buttons": [("Klik OK untuk transfer", "TRANSFER_RARE_OK"), ("⬅️ Kembali", "A")]},
    "AA_LEGEND": {"title": "📋 TRANSFER UMPAN KE (Legend)",
                  "buttons": [("Klik OK untuk transfer", "TRANSFER_LEGEND_OK"), ("⬅️ Kembali", "A")]},
    "AA_MYTHIC": {"title": "📋 TRANSFER UMPAN KE (Mythic)",
                  "buttons": [("Klik OK untuk transfer", "TRANSFER_MYTHIC_OK"), ("⬅️ Kembali", "A")]},

    # FISHING
    "E": {"title": "🎣 FISHING", "buttons": [("PILIH UMPAN", "EE"), ("⬅️ Kembali", "main")]},
    "EE": {"title": "📋 PILIH UMPAN", "buttons": [("Lanjut Pilih Jenis", "EEE"), ("⬅️ Kembali", "E")]},
    "EEE": {"title": "📋 Pilih Jenis Umpan", "buttons": [
        ("COMMON 🐛", "EEE_COMMON"), ("RARE 🐌", "EEE_RARE"),
        ("LEGENDARY 🧇", "EEE_LEGEND"), ("MYTHIC 🐟", "EEE_MYTHIC"),
        ("⬅️ Kembali", "EE")
    ]},

    # REGISTER
    "C": {"title": "📋 MENU REGISTER", "buttons": [("LANJUT", "CC"), ("⬅️ Kembali", "main")]},
    "CC": {"title": "📋 APAKAH KAMU YAKIN INGIN MENJADI PLAYER LOOT?",
           "buttons": [("PILIH OPSI", "CCC"), ("⬅️ Kembali", "C")]},
    "CCC": {"title": "📋 PILIH OPSI:",
            "buttons": [("YA", "REGISTER_YES"), ("TIDAK", "REGISTER_NO")]},

    # STORE
    "D": {"title": "🛒STORE", "buttons": [
        ("BUY UMPAN", "D1"), ("SELL IKAN", "D2"), ("TUKAR POINT", "D3"), ("⬅️ Kembali", "main")
    ]},
    "D1": {"title": "📋 BUY UMPAN", "buttons": [("D1A", "D1A"), ("⬅️ Kembali", "D")]},
    "D2": {"title": "📋 SELL IKAN", "buttons": [("D2A", "D2A"), ("⬅️ Kembali", "D")]},
    "D3": {"title": "📋 TUKAR POINT", "buttons": [("Lihat Poin & Tukar", "D3A"), ("⬅️ Kembali", "D")]},
    "D3A": {"title": "📋 🔄 POINT CHAT",
            "buttons": [("TUKAR 🔄 UMPAN COMMON 🐛", "TUKAR_POINT"), ("⬅️ Kembali", "D3")]},

    # YAPPING
    "B": {"title": "📋 YAPPING", "buttons": [("Poin Pribadi", "BB"), ("➡️ Leaderboard", "BBB"), ("⬅️ Kembali", "main")]},
    "BB": {"title": "📋 Poin Pribadi", "buttons": [("⬅️ Kembali", "B")]},
    "BBB": {"title": "📋 Leaderboard Yapping", "buttons": [("⬅️ Kembali", "B")]}
}

# GENERIC MENU F-G-H
for l in "FGH":
    MENU_STRUCTURE[l] = {"title": f"📋 Menu {l}",
                         "buttons": [(f"Menu {l*2}", l*2), ("⬅️ Kembali", "main")]}
    MENU_STRUCTURE[l*2] = {"title": f"📋 Menu {l*2}",
                            "buttons": [(f"Menu {l*3}", l*3), ("⬅️ Kembali", l)]}
    MENU_STRUCTURE[l*3] = {"title": f"📋 Menu {l*3} (Tampilan Terakhir)",
                            "buttons": [("⬅️ Kembali", l*2)]}

# FISH_CONFIRM
for jenis in ["COMMON", "RARE", "LEGEND", "MYTHIC"]:
    MENU_STRUCTURE[f"EEE_{jenis}"] = {
        "title": f"📋 Apakah kamu ingin memancing menggunakan umpan {jenis}?",
        "buttons": [("✅ YA", f"FISH_CONFIRM_{jenis}"), ("❌ TIDAK", "EEE")]
    }

# ---------------- KEYBOARD BUILDER ---------------- #
def make_keyboard(menu_key: str, user_id=None, page: int = 0) -> InlineKeyboardMarkup:
    buttons = []

    # LEADERBOARD
    if menu_key == "BBB" and user_id:
        points = yapping.load_points()
        sorted_pts = sorted(points.items(), key=lambda x: x[1]["points"], reverse=True)
        total_pages = (len(sorted_pts) - 1) // 10 if sorted_pts else 0
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"BBB_PAGE_{page-1}"))
        if page < total_pages:
            nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"BBB_PAGE_{page+1}"))
        if nav:
            buttons.append(nav)
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="B")])

    # MENU UMPAN
    elif menu_key in ["A", "AA_COMMON", "AA_RARE", "AA_LEGEND", "AA_MYTHIC"] and user_id:
        user_umpan = umpan.get_user(user_id) or {"A": {"umpan": 0}, "B": {"umpan": 0},
                                                 "C": {"umpan": 0}, "D": {"umpan": 0}}
        type_map = {"AA_COMMON": "A", "AA_RARE": "B", "AA_LEGEND": "C", "AA_MYTHIC": "D"}
        for text, cb in MENU_STRUCTURE.get(menu_key, {}).get("buttons", []):
            if cb.startswith("TRANSFER_"):
                jenis = cb.split("_")[1]
                jumlah = 999 if user_id == OWNER_ID else user_umpan.get(type_map.get(menu_key, "A"), {}).get("umpan", 0)
                text = f"{text} ({jumlah} pcs)"
            buttons.append([InlineKeyboardButton(text, callback_data=cb)])

    # FISHING PILIH UMPAN
    elif menu_key == "EEE" and user_id:
        user_umpan = umpan.get_user(user_id) or {"A": {"umpan": 0}, "B": {"umpan": 0},
                                                 "C": {"umpan": 0}, "D": {"umpan": 0}}
        if user_id == OWNER_ID:
            user_umpan = {"A": {"umpan": 999}, "B": {"umpan": 999}, "C": {"umpan": 999}, "D": {"umpan": 999}}
        map_type = {"EEE_COMMON": ("COMMON 🐛", "A"), "EEE_RARE": ("RARE 🐌", "B"),
                    "EEE_LEGEND": ("LEGENDARY 🧇", "C"), "EEE_MYTHIC": ("MYTHIC 🐟", "D")}
        for cb, (label, tkey) in map_type.items():
            jumlah = user_umpan.get(tkey, {}).get("umpan", 0)
            buttons.append([InlineKeyboardButton(f"{label} ({jumlah} pcs)", callback_data=cb)])
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="EE")])

    # STORE TUKAR POINT
    elif menu_key == "D3A" and user_id:
        pts = yapping.load_points().get(str(user_id), {}).get("points", 0)
        buttons.append([InlineKeyboardButton(f"TUKAR 🔄 UMPAN COMMON 🐛 (Anda: {pts} pts)", callback_data="TUKAR_POINT")])
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="D3")])

    # DEFAULT
    else:
        for text, cb in MENU_STRUCTURE.get(menu_key, {}).get("buttons", []):
            buttons.append([InlineKeyboardButton(text, callback_data=cb)])

    return InlineKeyboardMarkup(buttons)

# ---------------- CALLBACK HANDLER ---------------- #
async def callback_handler(client: Client, cq: CallbackQuery):
    data, user_id = cq.data, cq.from_user.id
    logger.info(f"[DEBUG] callback -> user:{user_id}, data:{data}")
    await cq.answer()

    # ---------------- REGISTER FLOW ---------------- #
    if data == "REGISTER_YES":
        uname = cq.from_user.username or "TanpaUsername"
        text = "🎉 Selamat kamu menjadi Player Loot!"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📇 SCAN ID & USN", callback_data="REGISTER_SCAN")],
            [InlineKeyboardButton("⬅️ Kembali", callback_data="main")]
        ])
        await cq.message.edit_text(text, reply_markup=kb)
        user_database.set_player_loot(user_id, True, uname)
        try:
            await client.send_message(OWNER_ID, f"📢 [REGISTER] Player baru mendaftar!\n👤 @{uname}\n🆔 {user_id}")
        except Exception as e:
            logger.error(f"Gagal kirim notif register ke owner: {e}")
        return

    if data == "REGISTER_SCAN":
        uname = cq.from_user.username or "TanpaUsername"
        text = f"📇 Data Player\n👤 @{uname}\n🆔 {user_id}"
        await cq.message.edit_text(text, reply_markup=make_keyboard("main", user_id))
        return

    # TRANSFER START
    if data.startswith("TRANSFER_"):
        jenis = data.split("_")[1]
        map_jenis = {"COMMON": "A", "RARE": "B", "LEGEND": "C", "MYTHIC": "D"}
        TRANSFER_STATE[user_id] = {"jenis": map_jenis.get(jenis)}
        await cq.message.reply("✍️ Masukkan format transfer: `@username jumlah`")
        return

    # FISHING
    if data.startswith("FISH_CONFIRM_"):
        jenis = data.replace("FISH_CONFIRM_", "")
        jenis_map = {"COMMON": "A", "RARE": "B", "LEGEND": "C", "MYTHIC": "D"}
        jk = jenis_map.get(jenis, "A")
        uname = cq.from_user.username or f"user{user_id}"
        if user_id != OWNER_ID:
            ud = umpan.get_user(user_id)
            if not ud or ud.get(jk, {}).get("umpan", 0) <= 0:
                await cq.answer("❌ Umpan tidak cukup!", show_alert=True)
                return
            umpan.remove_umpan(user_id, jk, 1)
        await cq.message.edit_text(f"🎣 Kamu berhasil melempar umpan {jenis} ke kolam!")

        async def fishing_task():
            try:
                await asyncio.sleep(2)
                await client.send_message(TARGET_GROUP, f"🎣 @{uname} sedang memancing...")
                loot_result = await fishing_loot(client, None, uname, user_id, umpan_type=jenis)
                await asyncio.sleep(15)
                await client.send_message(TARGET_GROUP, f"🎣 @{uname} mendapatkan {loot_result}!")
            except Exception as e:
                logger.error(f"Gagal fishing_task: {e}")
        asyncio.create_task(fishing_task())
        return

    # LEADERBOARD PAGING
    if data.startswith("BBB_PAGE_"):
        page = int(data.replace("BBB_PAGE_", ""))
        await show_leaderboard(cq, user_id, page)
        return

    # POIN PRIBADI
    if data == "BB":
        pts = yapping.load_points()
        udata = pts.get(str(user_id))
        if not udata:
            text = "❌ Kamu belum punya poin."
        else:
            lvl = udata.get("level", 0)
            badge = yapping.get_badge(lvl)
            text = f"📊 Poin Pribadi\n👤 {udata.get('username','Unknown')}\n⭐ {udata.get('points',0)} pts\n🏅 Level {lvl} {badge}"
        await cq.message.edit_text(text, reply_markup=make_keyboard("BB", user_id))
        return

    # LEADERBOARD
    if data == "BBB":
        await show_leaderboard(cq, user_id, 0)
        return

    # TUKAR POINT
    if data == "TUKAR_POINT":
        TUKAR_POINT_STATE[user_id] = {"step": 1, "jumlah_umpan": 0}
        await cq.message.reply("Masukkan jumlah umpan COMMON 🐛 yang ingin ditukar (100 poin = 1 umpan):")
        return

    if data == "TUKAR_CONFIRM":
        info = TUKAR_POINT_STATE.get(user_id)
        if not info or info.get("step") != 2:
            await cq.answer("❌ Proses tidak valid.", show_alert=True)
            return
        jml = info["jumlah_umpan"]
        pts = yapping.load_points().get(str(user_id), {}).get("points", 0)
        if pts < jml * 100:
            await cq.answer("❌ Point tidak cukup.", show_alert=True)
            TUKAR_POINT_STATE.pop(user_id, None)
            return
        yaping.update_points(user_id, -jml * 100)
        umpan.add_umpan(user_id, "A", jml)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data="D3A")]])
        await cq.message.edit_text(f"✅ Tukar berhasil! {jml} umpan COMMON 🐛 ditambahkan ke akunmu.", reply_markup=kb)
        TUKAR_POINT_STATE.pop(user_id, None)
        return

    # NAVIGASI MENU
    if data in MENU_STRUCTURE:
        await cq.message.edit_text(MENU_STRUCTURE[data]["title"], reply_markup=make_keyboard(data, user_id))
        return

# ---------------- HANDLE TRANSFER & TUKAR INPUT ---------------- #
async def handle_transfer_message(client: Client, message: Message):
    uid = message.from_user.id
    uname = message.from_user.username or f"user{uid}"

    # TRANSFER
    if TRANSFER_STATE.get(uid):
        try:
            jenis = TRANSFER_STATE[uid]["jenis"]
            parts = message.text.strip().split()
            if len(parts) != 2:
                return await message.reply("Format salah. Contoh: @username 1")
            rname, amt = parts
            if not rname.startswith("@"):
                return await message.reply("Username harus diawali '@'.")
            amt = int(amt)
            if amt <= 0:
                return await message.reply("Jumlah harus > 0.")
            rid = user_database.get_user_id_by_username(rname)
            if rid is None:
                await message.reply(f"❌ Username {rname} tidak ada di database!")
                TRANSFER_STATE.pop(uid, None)
                return
            if uid == OWNER_ID:
                umpan.add_umpan(rid, jenis, amt)
            else:
                sd = umpan.get_user(uid)
                if sd[jenis]["umpan"] < amt:
                    return await message.reply("❌ Umpan tidak cukup!")
                umpan.remove_umpan(uid, jenis, amt)
                umpan.add_umpan(rid, jenis, amt)
            await message.reply(f"✅ Transfer {amt} umpan ke {rname} berhasil!", reply_markup=make_keyboard("main", uid))
            try:
                await client.send_message(rid, f"🎁 Kamu mendapat {amt} umpan dari @{uname}")
            except Exception as e:
                logger.error(f"Gagal notif penerima {rid}: {e}")
        except Exception as e:
            await message.reply(f"❌ Error: {e}")
        TRANSFER_STATE.pop(uid, None)
        return

    # TUKAR POINT
    if TUKAR_POINT_STATE.get(uid):
        step = TUKAR_POINT_STATE[uid].get("step", 0)
        if step != 1:
            return
        try:
            jumlah = int(message.text.strip())
            if jumlah <= 0:
                return await message.reply("Jumlah umpan harus > 0.")
            pts = yapping.load_points().get(str(uid), {}).get("points", 0)
            if pts < jumlah * 100:
                return await message.reply(f"❌ Point tidak cukup ({pts} pts, butuh {jumlah * 100} pts).")
            TUKAR_POINT_STATE[uid]["jumlah_umpan"] = jumlah
            TUKAR_POINT_STATE[uid]["step"] = 2
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ YA", callback_data="TUKAR_CONFIRM")],
                [InlineKeyboardButton("❌ Batal", callback_data="D3A")]
            ])
            await message.reply(f"📊 Yakin ingin menukar {jumlah} umpan COMMON 🐛?\n(100 chat points = 1 umpan)", reply_markup=kb)
        except ValueError:
            await message.reply("Format salah. Masukkan angka jumlah umpan.")
        return

# ---------------- SHOW LEADERBOARD ---------------- #
async def show_leaderboard(cq: CallbackQuery, uid: int, page: int = 0):
    pts = yapping.load_points()
    sorted_pts = sorted(pts.items(), key=lambda x: x[1]["points"], reverse=True)
    total_pages = (len(sorted_pts) - 1) // 10 if sorted_pts else 0
    start, end = page * 10, page * 10 + 10
    text = f"🏆 Leaderboard Yapping (Page {page+1}/{total_pages+1}) 🏆\n\n"
    for i, (u, pdata) in enumerate(sorted_pts[start:end], start=start + 1):
        text += f"{i}. {pdata.get('username','Unknown')} - {pdata.get('points',0)} pts | Level {pdata.get('level',0)} {yapping.get_badge(pdata.get('level',0))}\n"
    await cq.message.edit_text(text, reply_markup=make_keyboard("BBB", uid, page))

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
    app.add_handler(MessageHandler(handle_transfer_message, filters.text & filters.private))
    app.add_handler(CallbackQueryHandler(callback_handler))
    logger.info("[MENU] Handler menu_utama terdaftar.")
