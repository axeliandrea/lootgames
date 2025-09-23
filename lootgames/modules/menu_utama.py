# lootgames/modules/menu_utama.py
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from lootgames.modules import yapping, umpan, user_database
from lootgames.modules import aquarium
from lootgames.modules.gacha_fishing import fishing_loot

logger = logging.getLogger(__name__)
OWNER_ID = 6395738130
TARGET_GROUP = -1002946278772  # ganti sesuai supergroup bot

# ---------------- STATE ---------------- #
TRANSFER_STATE = {}       # user_id: {"jenis": "A/B/C/D"}
TUKAR_POINT_STATE = {}    # user_id: {"step": step, "jumlah_umpan": n}
OPEN_MENU_STATE = {}      # user_id: True jika menu aktif

# ---------------- SELL / ITEM CONFIG ---------------- #
# inv_key harus cocok dengan key di aquarium_data.json (nama item di DB)
ITEM_PRICES = {
    "SELL_EMBER":    {"name": "🧺 Ember Pecah",        "price": 1,  "inv_key": "Ember Pecah"},
    "SELL_CRAB":     {"name": "🦀 Crab",               "price": 10, "inv_key": "Crab"},
    "SELL_ZONK":     {"name": "🤧 Zonk",               "price": 1,  "inv_key": "Zonk"},
    "SELL_TISUE":    {"name": "🧻 Roll Tisue Bekas",   "price": 1,  "inv_key": "Roll Tisue Bekas"},
    "SELL_SEPATU":   {"name": "🥾 Sepatu Butut",       "price": 1,  "inv_key": "Sepatu Butut"},
    "SELL_SMALLFISH":{"name": "𓆝 Small Fish",        "price": 5,  "inv_key": "Small Fish"},
    "SELL_PUFFER":   {"name": "🐡 Pufferfish",         "price": 7,  "inv_key": "Pufferfish"},
    "SELL_TURTLE":   {"name": "🐢 Turtle",             "price": 10, "inv_key": "Turtle"},
    "SELL_SNAIL":    {"name": "🐌 Snail",              "price": 4,  "inv_key": "Snail"},
    "SELL_OCTOPUS":  {"name": "🐙 Octopus",            "price": 12, "inv_key": "Octopus"},
}
# sementara user -> item_code waiting for amount input (chat)
SELL_WAITING = {}  # user_id: item_code

# ---------------- MENU STRUCTURE ---------------- #
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
            ("Menu G", "G")
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
            ("🧺 Ember Pecah", "SELL_DETAIL:SELL_EMBER"),
            ("🦀 Crab", "SELL_DETAIL:SELL_CRAB"),
            ("🤧 Zonk", "SELL_DETAIL:SELL_ZONK"),
            ("🧻 Roll Tisue Bekas", "SELL_DETAIL:SELL_TISUE"),
            ("🥾 Sepatu Butut", "SELL_DETAIL:SELL_SEPATU"),
            ("𓆝 Small Fish", "SELL_DETAIL:SELL_SMALLFISH"),
            ("🐡 Pufferfish", "SELL_DETAIL:SELL_PUFFER"),
            ("🐢 Turtle", "SELL_DETAIL:SELL_TURTLE"),
            ("🐌 Snail", "SELL_DETAIL:SELL_SNAIL"),
            ("🐙 Octopus", "SELL_DETAIL:SELL_OCTOPUS"),
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

# ---------------- KEYBOARD BUILDER ---------------- #
def make_keyboard(menu_key: str, user_id=None, page: int = 0) -> InlineKeyboardMarkup:
    buttons = []

    # LEADERBOARD
    if menu_key == "BBB" and user_id:
        points = yapping.load_points()
        sorted_pts = sorted(points.items(), key=lambda x: x[1]["points"], reverse=True)
        total_pages = (len(sorted_pts) - 1) // 10 if len(sorted_pts) > 0 else 0
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

        # load DB, cek stok
        db = aquarium.load_data()
        user_inv = db.get(str(user_id), {}) or {}
        stock = user_inv.get(item["inv_key"], 0)
        if amount <= 0 or amount > stock:
            await cq.answer("Stok tidak cukup atau jumlah salah.", show_alert=True)
            return

        # kurangi stok
        new_stock = stock - amount
        if new_stock > 0:
            user_inv[item["inv_key"]] = new_stock
        else:
            # hapus key jika 0
            user_inv.pop(item["inv_key"], None)

        db[str(user_id)] = user_inv
        try:
            aquarium.save_data(db)
        except Exception as e:
            logger.error(f"Gagal save aquarium setelah jual: {e}")
            await cq.answer("Gagal menyimpan data. Coba lagi nanti.", show_alert=True)
            return

        earned = amount * item["price"]
        # NOTE: belum menambahkan coin ke wallet (belum ada fizz_coin module) — hanya notifikasi
        await cq.message.edit_text(
            f"✅ Berhasil menjual {amount}x {item['name']}.\n"
            f"Kamu mendapatkan {earned} coin fizz (simulasi).\n"
            f"Sisa stok {item['name']}: {new_stock}"
        )
        return

    if data == "SELL_CANCEL":
        SELL_WAITING.pop(user_id, None)
        await cq.message.edit_text("❌ Penjualan dibatalkan.", reply_markup=make_keyboard("D2", user_id))
        return

    # CEK INVENTORY STORE
    if data == "D2A":
        inv_text = aquarium.list_inventory(user_id)
        kb = make_keyboard("D2A", user_id)
        await cq.message.edit_text(f"📦 Inventorymu:\n\n{inv_text}", reply_markup=kb)
        return

    # NAVIGASI MENU
    if data in MENU_STRUCTURE:
        await cq.message.edit_text(MENU_STRUCTURE[data]["title"], reply_markup=make_keyboard(data, user_id))
        return

# CEK INVENTORY (hasil tangkapan)
    if data == "FFF":
        inv_text = aquarium.list_inventory(user_id)
        kb = make_keyboard("FFF", user_id)
        await cq.message.edit_text(f"🎣 Inventorymu:\n\n{inv_text}", reply_markup=kb)
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

        # cek stok
        db = aquarium.load_data()
        user_inv = db.get(str(uid), {}) or {}
        stock = user_inv.get(item["inv_key"], 0)
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
    total_pages = (len(sorted_pts) - 1) // 10 if len(sorted_pts) > 0 else 0
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

# ---------------- REGISTER HANDLERS ---------------- #
def register(app: Client):
    # register handlers already expected by your app:
    app.add_handler(MessageHandler(open_menu, filters.regex(r"^\.menufish$") & filters.private))
    app.add_handler(MessageHandler(open_menu_pm, filters.command("menu") & filters.private))
    # this handler will also handle SELL amount input because SELL_WAITING is checked inside
    app.add_handler(MessageHandler(handle_transfer_message, filters.text & filters.private))
    app.add_handler(CallbackQueryHandler(callback_handler))
    logger.info("[MENU] Handler menu_utama terdaftar.")
