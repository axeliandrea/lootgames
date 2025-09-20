import json
import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from lootgames.modules import menu_utama
from lootgames.config import OWNER_ID


# ---------------- KEYBOARD ---------------- #
def main_menu_keyboard(user_id: int = None):
    """
    Keyboard utama untuk private chat
    """
    keyboard = menu_utama.make_keyboard("main", user_id)

    # tombol tambahan
    join_button = InlineKeyboardButton("JOIN", callback_data="join")
    menu_button = InlineKeyboardButton("MENU", callback_data="menu")
    keyboard.inline_keyboard.append([join_button, menu_button])

    return keyboard

# ---------------- CALLBACK MENU ---------------- #
async def menu_callback(client: Client, callback_query):
    user = callback_query.from_user
    await callback_query.answer()  # jawab callback agar loading hilang

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("💰 Poin Saya", callback_data="mypoints")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="back_main")]
    ])

    await callback_query.message.edit_text(
        f"📋 Menu Utama, {user.first_name} 👋\nPilih opsi di bawah:",
        reply_markup=keyboard
    )
    logger.info(f"[MENU] User {user.id} membuka menu utama")

# ---------------- CALLBACK BACK MAIN ---------------- #
async def back_main_callback(client: Client, callback_query):
    user = callback_query.from_user
    keyboard = main_menu_keyboard(user.id)
    await callback_query.message.edit_text(
        f"📋 Menu utama dikembalikan, {user.first_name} 👋",
        reply_markup=keyboard
    )
    logger.info(f"[BACK] User {user.id} kembali ke main menu")

# ---------------- REGISTER ---------------- #
def register(app: Client):
    """
    Register handler untuk private chat bot
    """
    # handler start
    app.add_handler(
        MessageHandler(start_handler, filters.private & filters.command("start"))
    )

    # callback join
    app.add_handler(
        CallbackQueryHandler(join_callback, filters=filters.create(lambda _, __, query: query.data == "join"))
    )

    # callback menu
    app.add_handler(
        CallbackQueryHandler(menu_callback, filters=filters.create(lambda _, __, query: query.data == "menu"))
    )

    # callback back main
    app.add_handler(
        CallbackQueryHandler(back_main_callback, filters=filters.create(lambda _, __, query: query.data == "back_main"))
    )
