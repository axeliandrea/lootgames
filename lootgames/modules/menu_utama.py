# lootgames/modules/menu_utama.py FIX 1
import logging
import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.modules import yapping, umpan, user_database
from lootgames.modules import fizz_coin
from lootgames.modules import aquarium
from lootgames.modules.gacha_fishing import fishing_loot
from datetime import datetime, timedelta, date

logger = logging.getLogger(__name__)
OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772  # ganti sesuai supergroup bot

# ---------------- STATE ---------------- #
TRANSFER_STATE = {}       # user_id: {"jenis": "A/B/C/D"}
TUKAR_POINT_STATE = {}    # user_id: {"step": step, "jumlah_umpan": n}
OPEN_MENU_STATE = {}      # user_id: True jika menu aktif
LOGIN_STATE = {}  # user_id: {"last_login_day": int, "streak": int, "umpan_given": set()}
STREAK_REWARDS = {1: 4, 2: 5, 3: 6, 4: 7, 5: 8, 6: 9, 7: 10}

# ---------------- SELL / ITEM CONFIG ---------------- #
# inv_key harus cocok dengan key di aquarium_data.json (nama item di DB)
ITEM_PRICES = {
    "SELL_SMALLFISH":{"name": "𓆝 Small Fish",        "price": 1,  "inv_key": "Small Fish"},
    "SELL_SNAIL":    {"name": "🐌 Snail",              "price": 2,  "inv_key": "Snail"},
    "SELL_OCTOPUS":  {"name": "🐙 Octopus",            "price": 3, "inv_key": "Octopus"},
    "SELL_PUFFER":   {"name": "🐡 Pufferfish",         "price": 5,  "inv_key": "Pufferfish"},
}
# sementara user -> item_code waiting for amount input (chat)
SELL_WAITING = {}  # user_id: item_code

# Optional aliases: jika DB berisi emoji atau variasi penulisan,
# kita bisa map nama yang sering muncul ke bentuk canonical.
INV_KEY_ALIASES = {
    "🤧 Zonk": "Zonk",
    "zonk": "zonk",
    "𓆝 Small Fish": "Small Fish",
    "small fish": "Small Fish",
    "🐌 snail": "Snail",
    "snail": "Snail",
    "🐙 octopus": "Octopus",
    "octopus": "Octopus",
    "🐡 Pufferfish": "Pufferfish",
    "pufferfish": "Pufferfish",
    # tambahkan sesuai kebutuhan 
}

# ---------------- KEYBOARD / MENU STRUCTURE ---------------- #
MENU_STRUCTURE = {
    # MAIN MENU
    "main": {
        "title": "📋 [Menu Utama]",
        "buttons": [
            ("UMPAN", "A"),
            ("YAPPING", "B"),
            ("REGISTER", "C"),
            ("🛒STORE", "D"),
            ("FISHING", "E"),
            ("HASIL TANGKAPAN", "F"),
            ("LOGIN CHECK IN", "G")
        ]
    },

    # =============== UMPAN =============== #
    "A": {
        "title": "📋 Menu UMPAN",
        "buttons": [
            ("COMMON 🐛", "AA_COMMON"),
            ("RARE 🐌", "AA_RARE"),
            ("LEGENDARY 🧇", "AA_LEGEND"),
            ("MYTHIC 🐟", "AA_MYTHIC"),
            ("⬅️ Kembali", "main")
        ]
    },
    "AA_COMMON": {
        "title": "📋 TRANSFER UMPAN KE (Common)",
        "buttons": [
            ("Klik OK untuk transfer", "TRANSFER_COMMON_OK"),
            ("⬅️ Kembali", "A")
        ]
    },
    "AA_RARE": {
        "title": "📋 TRANSFER UMPAN KE (Rare)",
        "buttons": [
            ("Klik OK untuk transfer", "TRANSFER_RARE_OK"),
            ("⬅️ Kembali", "A")
        ]
    },
    "AA_LEGEND": {
        "title": "📋 TRANSFER UMPAN KE (Legend)",
        "buttons": [
            ("Klik OK untuk transfer", "TRANSFER_LEGEND_OK"),
            ("⬅️ Kembali", "A")
        ]
    },
    "AA_MYTHIC": {
        "title": "📋 TRANSFER UMPAN KE (Mythic)",
        "buttons": [
            ("Klik OK untuk transfer", "TRANSFER_MYTHIC_OK"),
            ("⬅️ Kembali", "A")
        ]
    },

    # =============== FISHING =============== #
    "E": {
        "title": "🎣 FISHING",
        "buttons": [
            ("PILIH UMPAN", "EE"),
            ("⬅️ Kembali", "main")
        ]
    },
    "EE": {
        "title": "📋 PILIH UMPAN",
        "buttons": [
            ("Lanjut Pilih Jenis", "EEE"),
            ("⬅️ Kembali", "E")
        ]
    },
    "EEE": {
        "title": "📋 Pilih Jenis Umpan",
        "buttons": [
            ("COMMON 🐛", "EEE_COMMON"),
            ("RARE 🐌", "EEE_RARE"),
            ("LEGENDARY 🧇", "EEE_LEGEND"),
            ("MYTHIC 🐟", "EEE_MYTHIC"),
            ("⬅️ Kembali", "EE")
        ]
    },

    # =============== REGISTER =============== #
    "C": {
        "title": "📋 MENU REGISTER",
        "buttons": [
            ("LANJUT", "CC"),
            ("⬅️ Kembali", "main")
        ]
    },
    "CC": {
        "title": "📋 APAKAH KAMU YAKIN INGIN MENJADI PLAYER LOOT?",
        "buttons": [
            ("PILIH OPSI", "CCC"),
            ("⬅️ Kembali", "C")
        ]
    },
    "CCC": {
        "title": "📋 PILIH OPSI:",
        "buttons": [
            ("YA", "REGISTER_YES"),
            ("TIDAK", "REGISTER_NO")
        ]
    },

    # =============== STORE =============== #
    "D": {
        "title": "🛒STORE",
        "buttons": [
            ("BUY UMPAN", "D1"),
            ("SELL ITEM", "D2"),
            ("TUKAR POINT", "D3"),
            ("⬅️ Kembali", "main")
        ]
    },
    "D1": {
        "title": "📋 BUY UMPAN",
        "buttons": [
            ("D1A", "D1A"),
            ("⬅️ Kembali", "D")
        ]
    },
    "D2": {
        "title": "📋 SELL ITEM",
        "buttons": [
            ("💰 CEK COIN", "D2C"),
            ("📦 CEK INVENTORY", "D2A"),
            ("💰 DAFTAR HARGA", "D2B"),
            ("⬅️ Kembali", "D")
        ]
    },
    "D2A": {
        "title": "📦 CEK INVENTORY",
        "buttons": [
            ("⬅️ Kembali", "D2")
        ]
    },
    # DAFTAR HARGA -> note: callback format SELL_DETAIL:<code>
    "D2B": {
        "title": "💰 DAFTAR HARGA",
        "buttons": [
            ("𓆝 Small Fish", "SELL_DETAIL:SELL_SMALLFISH"),
            ("🐌 Snail", "SELL_DETAIL:SELL_SNAIL"),
            ("🐙 Octopus", "SELL_DETAIL:SELL_OCTOPUS"),
            ("🐡 Pufferfish", "SELL_DETAIL:SELL_PUFFER"),
            ("⬅️ Kembali", "D2"),
        ]
    },
    "D3": {
        "title": "📋 TUKAR POINT",
        "buttons": [
            ("Lihat Poin & Tukar", "D3A"),
            ("⬅️ Kembali", "D")
        ]
    },
    "D3A": {
        "title": "📋 🔄 POINT CHAT",
        "buttons": [
            ("TUKAR 🔄 UMPAN COMMON 🐛", "TUKAR_POINT"),
            ("⬅️ Kembali", "D3")
        ]
    },

    # =============== YAPPING =============== #
    "B": {
        "title": "📋 YAPPING",
        "buttons": [
            ("Poin Pribadi", "BB"),
            ("➡️ Leaderboard", "BBB"),
            ("⬅️ Kembali", "main")
        ]
    },
    "BB": {
        "title": "📋 Poin Pribadi",
        "buttons": [
            ("⬅️ Kembali", "B")
        ]
    },
    "BBB": {
        "title": "📋 Leaderboard Yapping",
        "buttons": [
            ("⬅️ Kembali", "B")
        ]
    },

    # =============== HASIL TANGKAPAN =============== #
    "F": {
        "title": "📋 HASIL TANGKAPAN",
        "buttons": [
            ("CEK INVENTORY", "FF"),
            ("⬅️ Kembali", "main")
        ]
    },
    "FF": {
        "title": "📋 CEK INVENTORY",
        "buttons": [
            ("LIHAT HASIL TANGKAPAN", "FFF"),
            ("⬅️ Kembali", "F")
        ]
    }
}

# Tambahan confirm untuk fishing
for jenis in ["COMMON", "RARE", "LEGEND", "MYTHIC"]:
    MENU_STRUCTURE[f"EEE_{jenis}"] = {
        "title": f"📋 Apakah kamu ingin memancing menggunakan umpan {jenis}?",
        "buttons": [
            ("✅ YA", f"FISH_CONFIRM_{jenis}"),
            ("❌ TIDAK", "EEE")
        ]
    }

# ---------------- LOGIN / ABSEN HARIAN ---------------- #
MENU_STRUCTURE["G"] = {
    "title": "📋 LOGIN HARIAN",
    "buttons": [
        ("✅ Absen Hari Ini", "LOGIN_TODAY"),
        ("📅 Lihat Status Login 7 Hari", "LOGIN_STATUS"),
        ("⬅️ Kembali", "main")
    ]
}

# ---------------- Helper untuk normalisasi key ---------------- #

def normalize_key(key: str) -> str:
    """
    Normalisasi nama item dari inventory agar cocok dengan inv_key.
    - Lowercase
    - Hilangkan emoji dan karakter non-alnum (kecuali spasi)
    - Trim spasi berlebih
    """
    if not isinstance(key, str):
        return ""
    # ubah ke lowercase
    s = key.strip().lower()
    # replace non-alphanumeric (tetap simpan spasi)
    s = re.sub(r"[^0-9a-z\s]", "", s)
    # collapse multiple spaces
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def canonical_inv_key_from_any(key: str) -> str:
    """Coba konversi nama key inventory (dari DB) menjadi bentuk canonical yang dipakai di ITEM_PRICES.
    Menggunakan INV_KEY_ALIASES dulu, jika tidak ditemukan, coba normalisasi dan cocokkan dengan
    semua ITEM_PRICES inv_key yang dinormalisasi.
    """
    if not key:
        return ""
    norm = normalize_key(key)
    # cek aliases
    if norm in INV_KEY_ALIASES:
        return INV_KEY_ALIASES[norm]

    # coba match dengan inv_key pada ITEM_PRICES
    for cfg in ITEM_PRICES.values():
        canon = cfg.get("inv_key")
        if normalize_key(canon) == norm:
            return canon
    # fallback - return original key (caller harus tetap handle absence)
    return key

# ---------------- KEYBOARD BUILDER ---------------- #
def make_keyboard(menu_key: str, user_id=None, page: int = 0) -> InlineKeyboardMarkup:
    buttons = []

    # LEADERBOARD
    if menu_key == "BBB" and user_id:
        points = yapping.load_points()
        sorted_pts = sorted(points.items(), key=lambda x: x[1]["points"], reverse=True)
        total_pages = max((len(sorted_pts) - 1) // 10, 0) if len(sorted_pts) > 0 else 0
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

    # HASIL TANGKAPAN INVENTORY
    elif menu_key == "FFF" and user_id:
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="F")])

    # STORE CEK INVENTORY
    elif menu_key == "D2A" and user_id:
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="D2")])

    # DEFAULT
    else:
        for text, cb in MENU_STRUCTURE.get(menu_key, {}).get("buttons", []):
            buttons.append([InlineKeyboardButton(text, callback_data=cb)])
        if not buttons:
            # fallback minimal supaya selalu valid
            buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="main")])

    return InlineKeyboardMarkup(buttons)

# ================= LOGIN HARIAN ================= #
days_of_week = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT", "SABTU", "MINGGU"]
login_rewards = [4, 5, 6, 7, 8, 9, 10]  # pcs Umpan common Type A per hari

def get_today_wib_index():
    """Return current weekday index (0=Senin, 6=Minggu) in WIB."""
    now_wib = datetime.utcnow() + timedelta(hours=7)
    return now_wib.weekday()

def generate_login_status(login_status: list[bool]) -> str:
    """
    login_status: list 7 bool (False=tidak login, True=login)
    """
    days = ["SENIN","SELASA","RABU","KAMIS","JUMAT","SABTU","MINGGU"]
    rewards = [4,5,6,7,8,9,10]  # reward per hari

    status_text = "📅 Status LOGIN 7 Hari Terakhir:\n"
    for i, day in enumerate(days):
        status = "✅" if login_status[i] else "❌"
        status_text += f"LOGIN-{i+1}: {status}{day}\n"

    status_text += "\nReward login Umpan common Type A:\n"
    for day, reward in zip(days, rewards):
        status_text += f"{day} {reward}x pcs Umpan common Type A\n"

    return status_text

# sekarang baru bisa dipanggil
login_status = [False, False, False, True, False, False, False]
print(generate_login_status(login_status))

# ---------------- CALLBACK HANDLER ---------------- #
async def callback_handler(client: Client, cq: CallbackQuery):
    data, user_id = cq.data, cq.from_user.id
    logger.info(f"[DEBUG] callback -> user:{user_id}, data:{data}")
    await cq.answer()

    # ===== LOGIN HARIAN CALLBACK =====
    if data == "LOGIN_TODAY":
        # inisialisasi user jika belum ada
        init_user_login(user_id)
        today = get_today_int()
        user_login = LOGIN_STATE[user_id]

        if user_login["last_login_day"] == today:
            await cq.answer("❌ Kamu sudah absen hari ini!", show_alert=True)
            return

        # update streak dan hari terakhir
        user_login["streak"] += 1
        user_login["login_dates"].add(today)

        # berikan 1 Umpan COMMON A jika belum pernah diterima
        reward = STREAK_REWARDS.get(user_login["streak"], 10)  # max 10 umpan
        reward_key = f"COMMON_{user_login['streak']}"  # track per streak
        if reward_key not in user_login["umpan_given"]:
            umpan.add_umpan(user_id, "A", reward)
            user_login["umpan_given"].add(reward_key)
            msg = f"🎉 Absen berhasil! Kamu mendapatkan {reward} Umpan COMMON 🐛. Streak: {user_login['streak']} hari."
        else:
            msg = f"✅ Absen berhasil! Tapi umpan sudah diterima sebelumnya. Streak: {user_login['streak']} hari."

        await cq.message.edit_text(msg, reply_markup=make_keyboard("G", user_id))
        return

    # di awal callback_handler
    days_of_week_id = ["SENIN","SELASA","RABU","KAMIS","JUMAT","SABTU","MINGGU"]

    if data == "LOGIN_TODAY":
        init_user_login(user_id)
        today = get_today_int()
        user_login = LOGIN_STATE[user_id]

        if user_login["last_login_day"] == today:
            await cq.answer("❌ Kamu sudah absen hari ini!", show_alert=True)
            return

        # update streak dan hari terakhir
        user_login["streak"] += 1
        user_login["last_login_day"] = today
        user_login["login_dates"].add(today)  # ✅ tambahkan ke set

        reward = STREAK_REWARDS.get(user_login["streak"], 10)
        reward_key = f"COMMON_{user_login['streak']}"
        if reward_key not in user_login["umpan_given"]:
            umpan.add_umpan(user_id, "A", reward)
            user_login["umpan_given"].add(reward_key)
            msg = f"🎉 Absen berhasil! Kamu mendapatkan {reward} Umpan COMMON 🐛. Streak: {user_login['streak']} hari."
        else:
            msg = f"✅ Absen berhasil! Tapi umpan sudah diterima sebelumnya. Streak: {user_login['streak']} hari."

        await cq.message.edit_text(msg, reply_markup=make_keyboard("G", user_id))

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
            await client.send_message(
                OWNER_ID,
                f"📢 [REGISTER] Player baru mendaftar!\n\n👤 Username: @{uname}\n🆔 User ID: {user_id}"
            )
        except Exception as e:
            logger.error(f"Gagal kirim notif register ke owner: {e}")
        return

    if data == "REGISTER_SCAN":
        uname = cq.from_user.username or "TanpaUsername"
        text = f"📇 Data Player\n\n👤 Username: @{uname}\n🆔 User ID: {user_id}"
        await cq.message.edit_text(text, reply_markup=make_keyboard("main", user_id))
        return

    # TRANSFER START
    if data.startswith("TRANSFER_"):
        jenis = data.split("_")[1]
        map_jenis = {"COMMON": "A", "RARE": "B", "LEGEND": "C", "MYTHIC": "D"}
        TRANSFER_STATE[user_id] = {"jenis": map_jenis.get(jenis)}
        await cq.message.reply("✍️ Masukkan format transfer: `@username jumlah`\nContoh: `@user 2`")
        return

    # CHECK COIN Fizz
    if data == "D2C":
        uid = cq.from_user.id
        try:
            # load langsung dari DB
            user_id = cq.from_user.id
            total_coin = fizz_coin.get_coin(user_id)
            text = f"💰 Total coinmu saat ini: {total_coin} fizz coin"

            # Cek apakah text sama dengan pesan sekarang, jika sama tambahkan invisible char supaya aman
            if cq.message.text == text:
                text += "\u200b"  # zero-width space untuk memaksa edit
            
            kb = make_keyboard("D2", user_id)  # tombol kembali ke menu SELL ITEM
            await cq.message.edit_text(text, reply_markup=kb)
        except Exception as e:
            # fallback aman jika tetap gagal edit
            await cq.answer(f"💰 Total coinmu: {total_coin}", show_alert=True)
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
    
        # Tombol kembali
        kb_back = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data="E")]])
    
        await cq.message.edit_text(f"🎣 Kamu berhasil melempar umpan {jenis} ke kolam!", reply_markup=kb_back)

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
            text = f"📊 Poin Pribadi\n\n👤 {udata.get('username','Unknown')}\n⭐ {udata.get('points',0)} pts\n🏅 Level {lvl} {badge}"
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
        yapping.update_points(user_id, -jml * 100)
        umpan.add_umpan(user_id, "A", jml)  # ✅ hanya COMMON
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data="D3A")]])
        await cq.message.edit_text(f"✅ Tukar berhasil! {jml} umpan COMMON 🐛 ditambahkan ke akunmu.", reply_markup=kb)
        TUKAR_POINT_STATE.pop(user_id, None)
        return

    # SELL FLOW: DETAIL -> START -> CONFIRM / CANCEL
    # data format: SELL_DETAIL:<code> , SELL_START:<code> , SELL_CONFIRM:<code>:<amount> , SELL_CANCEL
    if data.startswith("SELL_DETAIL:"):
        item_code = data.split(":", 1)[1]
        item = ITEM_PRICES.get(item_code)
        if not item:
            await cq.answer("Item tidak ditemukan.", show_alert=True)
            return
        # show price + opsi jual (mulai)
        text = f"💰 Harga {item['name']}\n1x = {item['price']} coin\n\nKetik jumlah yang ingin kamu jual, atau pilih tombol untuk mulai."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Jual Sekarang (ketik jumlah)", callback_data=f"SELL_START:{item_code}")],
            [InlineKeyboardButton("⬅️ Kembali", callback_data="D2B")]
        ])
        await cq.message.edit_text(text, reply_markup=kb)
        return

    if data.startswith("SELL_START:"):
        item_code = data.split(":", 1)[1]
        # tandai user menunggu input jumlah via chat
        SELL_WAITING[user_id] = item_code
        item = ITEM_PRICES.get(item_code)
        if not item:
            await cq.answer("Item tidak ditemukan.", show_alert=True)
            SELL_WAITING.pop(user_id, None)
            return
        await cq.message.edit_text(f"📝 Ketik jumlah {item['name']} yang ingin kamu jual (contoh: 2)\nKetik 0 untuk batal.")
        return

    if data.startswith("SELL_CONFIRM:"):
        # format SELL_CONFIRM:<code>:<amount>
        parts = data.split(":")
        if len(parts) != 3:
            await cq.answer("Data konfirmasi tidak valid.", show_alert=True)
            return
        item_code = parts[1]
        try:
            amount = int(parts[2])
        except ValueError:
            await cq.answer("Jumlah tidak valid.", show_alert=True)
            return
        item = ITEM_PRICES.get(item_code)
        if not item:
            await cq.answer("Item tidak ditemukan.", show_alert=True)
            return

        # load DB, cek stok (menggunakan normalisasi key)
        db = aquarium.load_data()
        user_inv = db.get(str(user_id), {}) or {}
        # buat mapping normalized_key -> (orig_key, value)
        normalized_inv = {}
        for k, v in user_inv.items():
            norm = normalize_key(k)
            normalized_inv[norm] = (k, v)

        target_norm = normalize_key(item["inv_key"])  # normalisasi inv_key
        # cek alias mapping juga
        canon_key = None
        if target_norm in normalized_inv:
            canon_key, stock = normalized_inv[target_norm]
        else:
            # coba cari lewat INV_KEY_ALIASES dan perbandingan terhadap normalized ITEM_PRICES
            # attempt: match any inventory key to this item
            stock = 0
            for orig_k, val in user_inv.items():
                if canonical_inv_key_from_any(orig_k) == item["inv_key"]:
                    canon_key = orig_k
                    stock = val
                    break

        if amount <= 0 or amount > stock:
            await cq.answer("Stok tidak cukup atau jumlah salah.", show_alert=True)
            return

        # kurangi stok
        new_stock = stock - amount
        if new_stock > 0:
            user_inv[canon_key or item["inv_key"]] = new_stock
        else:
            # hapus key jika 0
            user_inv.pop(canon_key or item["inv_key"], None)

        db[str(user_id)] = user_inv
        try:
            aquarium.save_data(db)
        except Exception as e:
            logger.error(f"Gagal save aquarium setelah jual: {e}")
            await cq.answer("Gagal menyimpan data. Coba lagi nanti.", show_alert=True)
            return

        earned = amount * item["price"]
        new_total = fizz_coin.add_coin(user_id, earned)  # ✅ simpan ke database
        await cq.message.reply_text(
            f"✅ Berhasil menjual {amount}x {item['name']}.\n"
            f"Kamu mendapatkan {earned} coin fizz.\n"
            f"💰 Total coinmu sekarang: {new_total} fizz coin\n"
            f"Sisa stok {item['name']}: {new_stock}",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("⬅️ Kembali", callback_data="D2")]
                ]
            )
        )
        return

    if data == "SELL_CANCEL":
        SELL_WAITING.pop(user_id, None)
        # lebih aman fallback ke D2 jika ada, kalau tidak ada ke main
        try:
            await cq.message.edit_text("❌ Penjualan dibatalkan.", reply_markup=make_keyboard("D2", user_id))
        except Exception:
            await cq.message.edit_text("❌ Penjualan dibatalkan.", reply_markup=make_keyboard("main", user_id))
        return

    # CEK INVENTORY STORE
    if data == "D2A":
        inv_text = aquarium.list_inventory(user_id)
        kb = make_keyboard("D2A", user_id)
        await cq.message.edit_text(f"📦 Inventorymu:\n\n{inv_text}", reply_markup=kb)
        return

    # CEK INVENTORY (hasil tangkapan)
    if data == "FFF":
        inv_text = aquarium.list_inventory(user_id)
        kb = make_keyboard("FFF", user_id)
        await cq.message.edit_text(f"🎣 Inventorymu:\n\n{inv_text}", reply_markup=kb)
        return

    # NAVIGASI MENU
    if data in MENU_STRUCTURE:
        await cq.message.edit_text(MENU_STRUCTURE[data]["title"], reply_markup=make_keyboard(data, user_id))
        return

# ---------------- HANDLE TRANSFER, TUKAR & SELL AMOUNT (TEXT INPUT) ---------------- #
async def handle_transfer_message(client: Client, message: Message):
    uid = message.from_user.id
    uname = message.from_user.username or f"user{uid}"

    # SELL AMOUNT via chat (user previously pressed SELL_START -> SELL_WAITING populated)
    if SELL_WAITING.get(uid):
        item_code = SELL_WAITING.pop(uid)
        item = ITEM_PRICES.get(item_code)
        if not item:
            return await message.reply("Item tidak ditemukan. Proses dibatalkan.")
        text = message.text.strip()
        # allow '0' to cancel
        if not text.isdigit():
            return await message.reply("Format salah. Masukkan angka jumlah yang ingin dijual.")
        amount = int(text)
        if amount <= 0:
            return await message.reply("Penjualan dibatalkan (jumlah <= 0).")

        # cek stok menggunakan normalisasi
        db = aquarium.load_data()
        user_inv = db.get(str(uid), {}) or {}
        normalized_inv = {}
        for k, v in user_inv.items():
            normalized_inv[normalize_key(k)] = (k, v)

        target_norm = normalize_key(item["inv_key"])  # target inv_key normal
        canon_key = None
        stock = 0
        if target_norm in normalized_inv:
            canon_key, stock = normalized_inv[target_norm]
        else:
            for orig_k, val in user_inv.items():
                if canonical_inv_key_from_any(orig_k) == item["inv_key"]:
                    canon_key = orig_k
                    stock = val
                    break

        if stock <= 0:
            return await message.reply(f"❌ Kamu tidak memiliki {item['name']} sama sekali.")
        if amount > stock:
            return await message.reply(f"❌ Stok tidak cukup ({stock} pcs).")

        # minta konfirmasi dengan tombol YA/TIDAK
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Ya", callback_data=f"SELL_CONFIRM:{item_code}:{amount}"),
                InlineKeyboardButton("❌ Tidak", callback_data="SELL_CANCEL")
            ]
        ])
        return await message.reply(
            f"📌 Konfirmasi\nApakah kamu yakin ingin menjual {amount}x {item['name']}?\nStok kamu: {stock}",
            reply_markup=kb
        )

    # TRANSFER (existing)
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
            await message.reply(f"✅ Transfer {amt} umpan ke {rname} berhasil!",
                                reply_markup=make_keyboard("main", uid))
            try:
                await client.send_message(rid, f"🎁 Kamu mendapat {amt} umpan dari @{uname}")
            except Exception as e:
                logger.error(f"Gagal notif penerima {rid}: {e}")
        except Exception as e:
            await message.reply(f"❌ Error: {e}")
        TRANSFER_STATE.pop(uid, None)
        return

    # TUKAR POINT (existing)
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
    total_pages = max((len(sorted_pts) - 1) // 10, 0) if len(sorted_pts) > 0 else 0
    start, end = page * 10, page * 10 + 10
    text = f"🏆 Leaderboard Yapping (Page {page+1}/{total_pages+1}) 🏆\n\n"
    for i, (u, pdata) in enumerate(sorted_pts[start:end], start=start + 1):
        text += f"{i}. {pdata.get('username','Unknown')} - {pdata.get('points',0)} pts | Level {pdata.get('level',0)} {yapping.get_badge(pdata.get('level',0))}\n"
    await cq.message.edit_text(text, reply_markup=make_keyboard("BBB", uid, page))

# ---------------- MENU OPEN ---------------- #
async def open_menu(client: Client, message: Message):
    uid = message.from_user.id
    if OPEN_MENU_STATE.get(uid):
        return await message.reply("⚠️ Menu sudah terbuka, jangan panggil lagi.")
    OPEN_MENU_STATE[uid] = True
    await message.reply(MENU_STRUCTURE["main"]["title"], reply_markup=make_keyboard("main", uid))

async def open_menu_pm(client: Client, message: Message):
    uid = message.from_user.id
    if OPEN_MENU_STATE.get(uid):
        return await message.reply("⚠️ Menu sudah terbuka, jangan panggil lagi.")
    OPEN_MENU_STATE[uid] = True
    await message.reply("📋 Menu Utama:", reply_markup=make_keyboard("main", uid))

def get_today_int():
    now_utc = datetime.utcnow()
    now_wib = now_utc + timedelta(hours=7)
    return int(now_wib.strftime("%Y%m%d"))

def init_user_login(user_id: int):
    if user_id not in LOGIN_STATE:
        LOGIN_STATE[user_id] = {
            "last_login_day": 0,
            "streak": 0,
            "umpan_given": set(),
            "login_dates": set()  # tambahkan ini
        }

# ---------------- REGISTER HANDLERS ---------------- #
def register(app: Client):
    # register handlers already expected by your app:
    app.add_handler(MessageHandler(open_menu, filters.regex(r"^\.menufish$") & filters.private))
    app.add_handler(MessageHandler(open_menu_pm, filters.command("menu") & filters.private))
    # this handler will also handle SELL amount input because SELL_WAITING is checked inside
    app.add_handler(MessageHandler(handle_transfer_message, filters.text & filters.private))
    app.add_handler(CallbackQueryHandler(callback_handler))
    logger.info("[MENU] Handler menu_utama terdaftar.")










