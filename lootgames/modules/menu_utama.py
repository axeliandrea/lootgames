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
    "D3A":{"title":"📋 🔄 POINT CHAT","buttons":[("TUKAR 🔄 UMPAN","TUKAR_POINT"),("⬅️ Kembali","D")]},
    # YAPPING
    "B":{"title":"📋 YAPPING","buttons":[("Poin Pribadi","BB"),("➡️ Leaderboard","BBB"),("⬅️ Kembali","main")]},
    "BB":{"title":"📋 Poin Pribadi","buttons":[("⬅️ Kembali","B")]},
    "BBB":{"title":"📋 Leaderboard Yapping","buttons":[("⬅️ Kembali","B")] }
}

# GENERIC MENU F-L
for l in "FGHIJKL":
    MENU_STRUCTURE[l] = {"title":f"📋 Menu {l}","buttons":[(f"Menu {l*2}",l*2),("⬅️ Kembali","main")] }
    MENU_STRUCTURE[l*2] = {"title":f"📋 Menu {l*2}","buttons":[(f"Menu {l*3}",l*3),("⬅️ Kembali",l)]}
    MENU_STRUCTURE[l*3] = {"title":f"📋 Menu {l*3} (Tampilan Terakhir)","buttons":[("⬅️ Kembali",l*2)]}

# FISH_CONFIRM
for jenis in ["COMMON","RARE","LEGEND","MYTHIC"]:
    MENU_STRUCTURE[f"EEE_{jenis}"] = {
        "title": f"📋 Apakah kamu ingin memancing menggunakan umpan {jenis}?",
        "buttons":[("✅ YA",f"FISH_CONFIRM_{jenis}"),("❌ TIDAK","EEE")]
    }

# ---------------- HELPERS ---------------- #
def _safe_get_points_for(points_dict, uid):
    """Dukung key sebagai str(uid) atau int(uid)."""
    if points_dict is None:
        return {}
    s = points_dict.get(str(uid))
    if s is not None:
        return s
    return points_dict.get(uid, {})

# ---------------- KEYBOARD BUILDER ---------------- #
def make_keyboard(menu_key: str, user_id=None, page: int = 0) -> InlineKeyboardMarkup:
    buttons = []

    # --- LEADERBOARD navigation (BBB) ---
    if menu_key == "BBB" and user_id is not None:
        points = yapping.load_points() or {}
        # normalize items into list of (uid, pdata)
        items = []
        for k, v in points.items():
            # ensure pdata is dict
            if not isinstance(v, dict):
                continue
            items.append((k, v))
        # sort by points safely
        sorted_points = sorted(items, key=lambda x: x[1].get("points", 0), reverse=True)
        total_pages = (len(sorted_points) - 1) // 10 if len(sorted_points) > 0 else 0
        # page nav
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"BBB_PAGE_{page-1}"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"BBB_PAGE_{page+1}"))
        if nav_buttons:
            buttons.append(nav_buttons)
        # Back button
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="B")])

    # --- MENU UMPAN TERBARU ---    
    elif menu_key in ["A","AA_COMMON","AA_RARE","AA_LEGEND","AA_MYTHIC"] and user_id:
        user_umpan = umpan.get_user(user_id) or {"A":{"umpan":0},"B":{"umpan":0},"C":{"umpan":0},"D":{"umpan":0}}
        type_map={"AA_COMMON":"A","AA_RARE":"B","AA_LEGEND":"C","AA_MYTHIC":"D"}
        for text, cb in MENU_STRUCTURE.get(menu_key,{}).get("buttons",[]):
            if cb in type_map:
                tkey=type_map[cb]
                jumlah = 999 if user_id==OWNER_ID else user_umpan.get(tkey,{}).get("umpan",0)
                text+=f" ({jumlah} pcs)"
            buttons.append([InlineKeyboardButton(text,callback_data=cb)])

    # --- MENU FISHING (EEE) ---        
    elif menu_key=="EEE" and user_id:
        user_umpan = umpan.get_user(user_id) or {"A":{"umpan":0},"B":{"umpan":0},"C":{"umpan":0},"D":{"umpan":0}}
        if user_id==OWNER_ID: user_umpan={"A":{"umpan":999},"B":{"umpan":999},"C":{"umpan":999},"D":{"umpan":999}}
        map_type={"EEE_COMMON":("COMMON 🐛","A"),"EEE_RARE":("RARE 🐌","B"),
                  "EEE_LEGEND":("LEGENDARY 🧇","C"),"EEE_MYTHIC":("MYTHIC 🐟","D")}
        for cb,(label,tkey) in map_type.items():
            jumlah=user_umpan.get(tkey,{}).get("umpan",0)
            buttons.append([InlineKeyboardButton(f"{label} ({jumlah} pcs)",callback_data=cb)])
        buttons.append([InlineKeyboardButton("⬅️ Kembali",callback_data="EE")])

    # --- D3A tukar point button show current points ---    
    elif menu_key=="D3A" and user_id:
        pts = yapping.load_points() or {}
        my = _safe_get_points_for(pts, user_id)
        pts_val = my.get("points", 0)
        buttons.append([InlineKeyboardButton(f"TUKAR 🔄 UMPAN (Anda: {pts_val} pts)",callback_data="TUKAR_POINT")])
        buttons.append([InlineKeyboardButton("⬅️ Kembali",callback_data="D3")])

    # --- POIN PRIBADI (BB) show user's points ---    
    elif menu_key=="BB" and user_id is not None:
        pts = yapping.load_points() or {}
        my = _safe_get_points_for(pts, user_id)
        pts_val = my.get("points", 0)
        level = my.get("level", 0)
        # Show as one button (not interactive) and back
        buttons.append([InlineKeyboardButton(f"Poin Anda: {pts_val} pts | Level {level}", callback_data="B")])
        buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="B")])

    else:
        for text, cb in MENU_STRUCTURE.get(menu_key,{}).get("buttons",[]):
            buttons.append([InlineKeyboardButton(text,callback_data=cb)])
    return InlineKeyboardMarkup(buttons)

# ---------------- CALLBACK HANDLER ---------------- #
async def callback_handler(client: Client, cq: CallbackQuery):
    data, user_id = cq.data, cq.from_user.id
    logger.info(f"[DEBUG] callback -> user:{user_id}, data:{data}")
    await cq.answer()
    await asyncio.sleep(0.1)

    # FISHING
    if data.startswith("FISH_CONFIRM_"):
        jenis = data.replace("FISH_CONFIRM_","")
        jenis_map={"COMMON":"A","RARE":"B","LEGEND":"C","MYTHIC":"D"}
        jk=jenis_map.get(jenis,"A")
        uname=cq.from_user.username or f"user{user_id}"
        if user_id!=OWNER_ID:
            ud=umpan.get_user(user_id) or {}
            if not ud or ud.get(jk,{}).get("umpan",0)<=0:
                await cq.answer("❌ Umpan tidak cukup!",show_alert=True)
                return
            umpan.remove_umpan(user_id,jk,1)
        try: await cq.message.edit_text(f"🎣 Kamu berhasil melempar umpan {jenis} ke kolam!")
        except: pass

        async def fishing_task():
            try:
                # tunggu 2 detik untuk animasi awal
                await asyncio.sleep(2)
                # Kirim info awal memancing
                await client.send_message(TARGET_GROUP,
                                          f"🎣 @{uname} sedang memancing di group ini, kira2 dapet apa ya?")
                # proses loot
                loot_result = await fishing_loot(client, None, uname, user_id, umpan_type=jenis)
                # tunggu 15 detik sebelum kirim hasil
                await asyncio.sleep(15)
                await client.send_message(TARGET_GROUP,f"🎣 @{uname} mendapatkan {loot_result}!")
            except Exception as e:
                logger.error(f"Gagal kirim info reward: {e}")
        asyncio.create_task(fishing_task())
        return

    # LEADERBOARD PAGING
    if data.startswith("BBB_PAGE_"):
        page=int(data.replace("BBB_PAGE_",""))
        await show_leaderboard(cq,user_id,page)
        return

    # NAVIGASI MENU
    if data in MENU_STRUCTURE:
        try: await cq.message.edit_text(MENU_STRUCTURE[data]["title"],reply_markup=make_keyboard(data,user_id))
        except Exception as e:
            logger.error(f"Edit menu gagal: {e}")
        return

    # TUKAR POINT
    if data=="TUKAR_POINT":
        TUKAR_POINT_STATE[user_id]={"step":1,"jumlah_umpan":0}
        await cq.message.reply("Masukkan jumlah umpan yang ingin ditukar:")
        return
    if data=="TUKAR_CONFIRM":
        info=TUKAR_POINT_STATE.get(user_id)
        if not info or info.get("step")!=2:
            await cq.answer("❌ Proses tidak valid.",show_alert=True)
            return
        jml=info["jumlah_umpan"]
        pts=yapping.load_points().get(str(user_id),{}).get("points",0)
        if pts<jml*100:
            await cq.answer("❌ Point tidak cukup.",show_alert=True)
            TUKAR_POINT_STATE.pop(user_id,None)
            return
        yapping.update_points(user_id,-jml*100)
        umpan.add_umpan(user_id,"A",jml)
        await cq.message.reply(f"✅ Tukar berhasil! {jml} umpan ditambahkan ke akunmu.")
        TUKAR_POINT_STATE.pop(user_id,None)
        return

# ---------------- HANDLE TRANSFER & TUKAR INPUT ---------------- #
async def handle_transfer_message(client: Client,message:Message):
    uid=message.from_user.id
    uname=message.from_user.username or f"user{uid}"

    # TRANSFER
    if TRANSFER_STATE.get(uid):
        try:
            jenis=TRANSFER_STATE[uid]["jenis"]
            parts=message.text.strip().split()
            if len(parts)!=2: return await message.reply("Format salah. Contoh: @username 1")
            rname,amt=parts
            if not rname.startswith("@"): return await message.reply("Username harus diawali '@'.")
            amt=int(amt)
            if amt<=0: return await message.reply("Jumlah harus > 0.")
            rid=user_database.get_user_id_by_username(rname)
            if rid is None:
                await message.reply(f"❌ Username {rname} tidak ada di database!")
                TRANSFER_STATE.pop(uid,None)
                return
            if uid==OWNER_ID:
                umpan.add_umpan(rid,jenis,amt)
            else:
                sd=umpan.get_user(uid) or {}
                if sd.get(jenis,{}).get("umpan",0)<amt: return await message.reply("❌ Umpan tidak cukup!")
                umpan.remove_umpan(uid,jenis,amt)
                umpan.add_umpan(rid,jenis,amt)
            await message.reply(f"✅ Transfer {amt} umpan ke {rname} berhasil!",reply_markup=make_keyboard("main",uid))
            try: await client.send_message(rid,f"🎁 Kamu mendapatkan {amt} umpan dari (@{uname})")
            except Exception as e: logger.error(f"Gagal notif penerima {rid}: {e}")
        except Exception as e:
            await message.reply(f"❌ Error: {e}")
        TRANSFER_STATE.pop(uid,None)
        return

    # TUKAR POINT INPUT
    if TUKAR_POINT_STATE.get(uid):
        step=TUKAR_POINT_STATE[uid].get("step",0)
        if step!=1: return
        try:
            jumlah=int(message.text.strip())
            if jumlah<=0: return await message.reply("Jumlah umpan harus > 0.")
            pts=yapping.load_points() or {}
            my = _safe_get_points_for(pts, uid)
            if my.get("points",0)<jumlah*100: return await message.reply(f"❌ Point chat tidak cukup ({my.get('points',0)} pts, butuh {jumlah*100} pts).")
            TUKAR_POINT_STATE[uid]["jumlah_umpan"]=jumlah
            TUKAR_POINT_STATE[uid]["step"]=2
            kb=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ YA",callback_data="TUKAR_CONFIRM")],
                [InlineKeyboardButton("❌ Batal",callback_data="D3A")]
            ])
            await message.reply(f"📊 Anda yakin ingin menukar {jumlah} umpan?\n(100 chat points = 1 umpan)",reply_markup=kb)
        except ValueError:
            await message.reply("Format salah. Masukkan angka jumlah umpan.")
        return

# ---------------- SHOW LEADERBOARD ---------------- #
async def show_leaderboard(cq: CallbackQuery, uid:int, page:int=0):
    pts = yapping.load_points() or {}
    items = []
    for k, v in pts.items():
        if not isinstance(v, dict):
            continue
        items.append((k, v))
    sorted_pts = sorted(items, key=lambda x: x[1].get("points", 0), reverse=True)
    total_pages = (len(sorted_pts)-1)//10 if len(sorted_pts)>0 else 0
    page = max(0, min(page, total_pages))
    start, end = page*10, page*10+10
    display_page = page + 1
    text = f"🏆 Leaderboard Yapping (Page {display_page}/{total_pages+1 if total_pages>=0 else 1}) 🏆\n\n"
    for i, (u, pdata) in enumerate(sorted_pts[start:end], start=start+1):
        uname = pdata.get('username') or (f"user{u}" if isinstance(u, int) else f"user{u}")
        points = pdata.get('points', 0)
        level = pdata.get('level', 0)
        badge = yapping.get_badge(level) if hasattr(yapping, "get_badge") else ""
        text += f"{i}. {uname} - {points} pts | Level {level} {badge}\n"
    # fallback message if empty
    if len(sorted_pts) == 0:
        text += "Belum ada data poin.\n"
    try:
        await cq.message.edit_text(text, reply_markup=make_keyboard("BBB", uid, page))
    except Exception as e:
        logger.error(f"Gagal edit leaderboard: {e}")

# ---------------- MENU OPEN ---------------- #
async def open_menu(client:Client,message:Message):
    await message.reply(MENU_STRUCTURE["main"]["title"],reply_markup=make_keyboard("main",message.from_user.id))

async def open_menu_pm(client:Client,message:Message):
    uid=message.from_user.id
    await message.reply("📋 Menu Utama:",reply_markup=make_keyboard("main",uid))

# ---------------- REGISTER HANDLERS ---------------- #
def register(app: Client):
    app.add_handler(MessageHandler(open_menu,filters.regex(r"^\.menufish$") & filters.private))
    app.add_handler(MessageHandler(open_menu_pm,filters.command("menu") & filters.private))
    app.add_handler(MessageHandler(handle_transfer_message,filters.text & filters.private))
    app.add_handler(CallbackQueryHandler(callback_handler))
    logger.info("[MENU] Handler menu_utama terdaftar.")
