"""
Hint information command handlers for Language Learning Bot.
FIXED: Removed code duplication, improved architecture, better user experience.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.logger import setup_logger
from app.utils.hint_constants import (
    get_all_hint_types, 
    get_hint_name, 
    get_hint_icon,
)
from app.bot.states.centralized_states import UserStates
from app.utils.message_utils import get_user_info, get_message_from_callback

# Создаем роутер для обработчиков подсказок
hint_router = Router()

# Set up logging
logger = setup_logger(__name__)

def _get_hint_info_content() -> dict:
    """
    Централизованная информация о подсказках для лучшей поддерживаемости.
    
    Returns:
        dict: Structured hint information with all details
    """
    return {
        "title": "💡 Система подсказок",
        "description": (
            "Подсказки помогают вам лучше запоминать иностранные слова! "
            "Они выстроены в логическую цепочку, которая помогает вспомнить иностранный перевод для русского слова."
        ),
        "hint_types": {
            hint_type: {
                "name": get_hint_name(hint_type),
                "icon": get_hint_icon(hint_type),
                "description": _get_hint_type_description(hint_type)
            }
            for hint_type in get_all_hint_types()
        },
        "usage": {
            "title": "🎯 Как использовать подсказки:",
            "steps": [
                "1. Во время изучения слов (/study) вы увидите кнопки подсказок",
                "2. Нажмите на нужный тип подсказки",
                "3. Если подсказки нет - создайте её",
                "4. Если подсказка есть - просмотрите или отредактируйте",
                "5. Активные подсказки отображаются прямо в сообщении со словом"
            ]
        },
        "settings": {
            "title": "⚙️ Настройка подсказок:",
            "description": (
                "В настройках (/settings) вы можете индивидуально включать и отключать "
                "каждый тип подсказок. Отключенные типы не будут показываться во время изучения."
            )
        },
        "important": {
            "title": "❗️ Важная информация:",
            "points": [
                "• Использование любой подсказки означает, что пользователь не помнит слово",
                "• Слово с использованной подсказкой будет показано для повторения через 1 день",
                "• Подсказки сохраняются индивидуально для каждого пользователя",
                "• Вы можете создавать текстовые подсказки или записывать голосовые заметки",
                "• Подсказки можно редактировать в любое время"
            ]
        },
        "use_settings": "Используйте /settings для настройки отдельных типов подсказок",
        "footer": "Для получения дополнительной справки используйте команду /help",
    }

def _get_hint_type_description(hint_type: str) -> str:
    """
    Детальные описания для каждого типа подсказки.
    
    Args:
        hint_type: Type of hint
        
    Returns:
        str: Detailed description of the hint type
    """
    descriptions = {
        "meaning": (
            "Дополнительные образы, контекст слова. "
            "Помогает придумать переход к фонетической ассоциации."
        ),
        "phoneticassociation": (
            "Ассоциации звучания слогов или частей слова - с знакомыми русскими словами или звуками. "
            "Основывается на ассоциации русского значения."
            "Помогает придумать переход к фонетическому звучанию."
        ),
        "phoneticsound": (
            "Разбиение слова на слоги и звуки для лучшего запоминания. "
            "Основывается на ассоциации фонетического звучания."
            "Помогает запомнить, как правильно произносить слово по частям."
        ),
        "writing": (
            "Мнемонические приемы для запоминания написания слова. "
            "Может основываться на любой из предыдущих ассоциаций."
            "Особенно полезно для языков с нелатинскими алфавитами или сложным написанием."
        )
    }
    
    return descriptions.get(hint_type, "Специальный тип подсказки для улучшения запоминания.")

def _format_hint_info_text(hint_info: dict, user_hint_settings: dict = None) -> str:
    """
    Форматирование информации о подсказках с учетом пользовательских настроек.
    
    Args:
        hint_info: Structured hint information  
        user_hint_settings: User's individual hint settings
        
    Returns:
        str: Formatted hint information text
    """
    text = f"{hint_info['title']}\n\n"
    text += f"{hint_info['description']}\n\n"
    
    # Add hint types information
    text += "🔍 <b>Типы подсказок:</b>\n\n"
    
    for hint_type, info in hint_info['hint_types'].items():
        icon = info['icon']
        name = info['name']
        description = info['description']
        
        # Check if this hint type is enabled in user settings  
        if user_hint_settings:
            setting_key = f"show_{hint_type}" if hint_type == "hint_meaning" else f"show_hint_{hint_type}"
            # Map hint types to setting keys properly
            setting_mapping = {
                "meaning": "show_hint_meaning",
                "phoneticassociation": "show_hint_phoneticassociation", 
                "phoneticsound": "show_hint_phoneticsound",
                "writing": "show_hint_writing"
            }
            setting_key = setting_mapping.get(hint_type, f"show_hint_{hint_type}")
            is_enabled = user_hint_settings.get(setting_key, True)
            status = "✅" if is_enabled else "❌"
        else:
            status = "❓"
        
        text += f"{status} {icon} <b>{name}</b>\n{description}\n\n"
    
    # Add usage information
    text += f"{hint_info['usage']['title']}\n"
    for step in hint_info['usage']['steps']:
        text += f"{step}\n"
    text += "\n"
    
    # Add settings information
    text += f"{hint_info['settings']['title']}\n"
    text += f"{hint_info['settings']['description']}\n\n"
    
    # Add important information
    text += f"{hint_info['important']['title']}\n"
    for point in hint_info['important']['points']:
        text += f"{point}\n"
    text += "\n"
    
    text += hint_info['use_settings']
    text += "\n"
    text += "\n"

    text += hint_info['footer']
    
    return text

@hint_router.message(Command("hint"))
async def cmd_hint(message: Message, state: FSMContext):
    await process_hint(message, state)

@hint_router.callback_query(F.data == "show_hint_info")
async def process_show_hint_info_callback(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to show hint information.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info(f"'show_hint_info' callback from {callback.from_user.full_name}")
    
    await callback.answer("💡 О подсказках...")
    
    await process_hint(callback, state)

async def process_hint(message_or_callback, state: FSMContext):
    """
    Handle the /hint command which provides information about hint functionality.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    user_id, username, full_name = get_user_info(message_or_callback)
    message = get_message_from_callback(message_or_callback)

    logger.info(f"'/hint' command from {full_name} ({username})")

    # Set state for viewing hint info
    await state.set_state(UserStates.viewing_hint_info)
    
    # Get and format hint information
    hint_info = _get_hint_info_content()
    hint_text = _format_hint_info_text(hint_info, user_hint_settings=None)
    

    # Send hint information
    await message.answer(hint_text, parse_mode="HTML")

# Export router and utilities
__all__ = [
    'hint_router',
]
