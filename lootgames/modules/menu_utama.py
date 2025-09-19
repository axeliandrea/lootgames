"""
Menu Utama module for LootGames Telegram Bot
Handles all menu interactions and hierarchical navigation
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class MenuUtama:
    def __init__(self):
        self.menu_structure = self._build_menu_structure()
        
    def _build_menu_structure(self) -> Dict:
        """Build the complete menu structure"""
        menu_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
        
        structure = {
            'main': {
                'title': '🎮 Menu Utama LootGames',
                'items': []
            }
        }
        
        # Build hierarchical menu structure
        for letter in menu_letters:
            # Level 1: Menu A, Menu B, etc.
            menu_id = f"menu_{letter.lower()}"
            structure['main']['items'].append({
                'text': f'🎯 Menu {letter}',
                'callback_data': menu_id
            })
            
            # Level 2: Menu AA, Menu BB, etc.
            level2_id = f"menu_{letter.lower()}{letter.lower()}"
            structure[menu_id] = {
                'title': f'📋 Menu {letter}',
                'items': [{
                    'text': f'🎲 Menu {letter}{letter}',
                    'callback_data': level2_id
                }],
                'back_to': 'main'
            }
            
            # Level 3: Menu AAA, Menu BBB, etc. (Final level)
            level3_id = f"menu_{letter.lower()}{letter.lower()}{letter.lower()}"
            structure[level2_id] = {
                'title': f'🎯 Menu {letter}{letter}',
                'items': [{
                    'text': f'🏆 Menu {letter}{letter}{letter}',
                    'callback_data': level3_id
                }],
                'back_to': menu_id
            }
            
            # Level 3 content (final destination)
            structure[level3_id] = {
                'title': f'🎉 Menu {letter}{letter}{letter}',
                'content': f'✨ Selamat! Anda telah mencapai Menu {letter}{letter}{letter}\
\
'
                          f'🎮 Ini adalah menu terakhir dari jalur {letter}.\
'
                          f'🏅 Terima kasih telah menjelajahi menu LootGames!',
                'back_to': level2_id,
                'is_final': True
            }
        
        return structure
    
    def _create_keyboard(self, menu_data: Dict, current_menu: str) -> InlineKeyboardMarkup:
        """Create inline keyboard for menu"""
        keyboard = []
        
        # Add menu items
        if 'items' in menu_data:
            for item in menu_data['items']:
                keyboard.append([InlineKeyboardButton(
                    item['text'], 
                    callback_data=item['callback_data']
                )])
        
        # Add back button if not main menu
        if 'back_to' in menu_data:
            back_text = "🔙 Kembali"
            if menu_data['back_to'] == 'main':
                back_text = "🏠 Menu Utama"
            
            keyboard.append([InlineKeyboardButton(
                back_text, 
                callback_data=menu_data['back_to']
            )])
        
        # Add close button for final menus
        if menu_data.get('is_final', False):
            keyboard.append([InlineKeyboardButton(
                "❌ Tutup Menu", 
                callback_data="close_menu"
            )])
        
        return InlineKeyboardMarkup(keyboard)
    
    def _get_menu_text(self, menu_data: Dict, menu_key: str) -> str:
        """Get formatted text for menu"""
        title = menu_data.get('title', 'Menu')
        
        if menu_data.get('is_final', False):
            # Final menu with content
            return menu_data.get('content', title)
        
        # Regular menu
        text = f"{title}\
\
"
        
        if menu_key == 'main':
            text += "🎯 Pilih menu yang ingin Anda jelajahi:\
"
            text += "📍 Setiap menu memiliki sub-menu hingga 3 level"
        else:
            text += "📋 Pilih opsi di bawah ini:"
        
        return text
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the main menu"""
        try:
            menu_data = self.menu_structure['main']
            keyboard = self._create_keyboard(menu_data, 'main')
            text = self._get_menu_text(menu_data, 'main')
            
            await update.message.reply_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            logger.info(f"Main menu displayed for user {update.effective_user.id}")
            
        except Exception as e:
            logger.error(f"Error showing main menu: {e}")
            await update.message.reply_text("❌ Gagal menampilkan menu utama.")
    
    async def handle_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle menu navigation callbacks"""
        try:
            query = update.callback_query
            callback_data = query.data
            
            logger.info(f"Menu callback received: {callback_data} from user {update.effective_user.id}")
            
            # Handle close menu
            if callback_data == "close_menu":
                await query.edit_message_text("✅ Menu ditutup. Terima kasih!")
                return
            
            # Get menu data
            if callback_data not in self.menu_structure:
                await query.edit_message_text("❌ Menu tidak ditemukan.")
                return
            
            menu_data = self.menu_structure[callback_data]
            keyboard = self._create_keyboard(menu_data, callback_data)
            text = self._get_menu_text(menu_data, callback_data)
            
            # Update message
            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Error handling menu callback: {e}")
            await query.edit_message_text("❌ Terjadi kesalahan saat memproses menu.")
    
    def get_menu_info(self) -> str:
        """Get information about available menus"""
        total_menus = len([k for k in self.menu_structure.keys() if k != 'main'])
        return f"📊 Total menu tersedia: {total_menus}\
🎯 Menu utama: A-L (12 kategori)\
📱 Setiap kategori memiliki 3 level navigasi"
