#!/usr/bin/env python3
"""
LootGames Telegram Bot
Main entry point for the bot application
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN, ALLOWED_GROUP_ID, OWNER_ID, LOG_LEVEL, LOG_FORMAT
from modules.menu_utama import MenuUtama

# Configure logging
logging.basicConfig(
    format=LOG_FORMAT,
    level=getattr(logging, LOG_LEVEL.upper())
)
logger = logging.getLogger(__name__)

class LootGamesBot:
    def __init__(self):
        self.menu_handler = MenuUtama()
        
    async def menufish_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the .menufish command"""
        try:
            # Check if command is from allowed group
            if update.effective_chat.id != ALLOWED_GROUP_ID:
                logger.warning(f"Command received from unauthorized group: {update.effective_chat.id}")
                return
            
            # Send the main menu
            await self.menu_handler.show_main_menu(update, context)
            
        except Exception as e:
            logger.error(f"Error in menufish_command: {e}")
            await update.message.reply_text("❌ Terjadi kesalahan saat menampilkan menu.")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        try:
            query = update.callback_query
            await query.answer()
            
            # Check if callback is from allowed group
            if query.message.chat.id != ALLOWED_GROUP_ID:
                logger.warning(f"Callback received from unauthorized group: {query.message.chat.id}")
                return
            
            # Handle the callback
            await self.menu_handler.handle_menu_callback(update, context)
            
        except Exception as e:
            logger.error(f"Error in handle_callback: {e}")
            await query.edit_message_text("❌ Terjadi kesalahan saat memproses pilihan menu.")

    def setup_handlers(self, app: Application):
        """Setup all command and callback handlers"""
        # Command handlers
        app.add_handler(CommandHandler("menufish", self.menufish_command))
        
        # Callback query handler
        app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        logger.info("All handlers have been set up successfully")

async def main():
    """Main function to start the bot"""
    logger.info("Starting LootGames Telegram Bot...")
    
    # Validate configuration
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ BOT_TOKEN tidak ditemukan! Silakan atur token di config.py")
        return
    
    try:
        # Create bot instance
        bot = LootGamesBot()
        
        # Create application
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Setup handlers
        bot.setup_handlers(app)
        
        # Start the bot
        logger.info(f"🚀 Bot started successfully!")
        logger.info(f"📱 Monitoring group: {ALLOWED_GROUP_ID}")
        logger.info(f"👑 Owner ID: {OWNER_ID}")
        logger.info(f"🎮 Use /menufish command to show menu")
        
        # Run the bot until stopped
        await app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
