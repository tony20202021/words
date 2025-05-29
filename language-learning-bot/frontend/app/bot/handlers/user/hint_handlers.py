"""
Hint information command handlers for Language Learning Bot.
FIXED: Removed code duplication, improved architecture, better user experience.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import safe_api_call
from app.utils.hint_constants import (
    get_all_hint_types, 
    get_hint_name, 
    get_hint_icon,
    HINT_SETTING_KEYS,
    get_hint_setting_name
)
from app.utils.hint_settings_utils import get_individual_hint_settings
from app.bot.states.centralized_states import UserStates

# Создаем роутер для обработчиков подсказок
hint_router = Router()

# Set up logging
logger = setup_logger(__name__)

# НОВОЕ: Централизованная функция для обеспечения существования пользователя
async def _ensure_user_exists_quietly(user_info, api_client) -> bool:
    """
    Ensure user exists in database (quiet version for info context).
    НОВОЕ: Тихая версия для информационного контекста - без детального логирования ошибок.
    
    Args:
        user_info: User information from Telegram
        api_client: API client instance
        
    Returns:
        bool: True if user exists or was created successfully
    """
    user_id = user_info.id
    
    # Check if user exists
    success, users = await safe_api_call(
        lambda: api_client.get_user_by_telegram_id(user_id),
        None,
        "проверка пользователя для информации о подсказках",
        handle_errors=False
    )
    
    if not success:
        return False
    
    # User already exists
    if users and len(users) > 0:
        return True
    
    # Create new user
    new_user_data = {
        "telegram_id": user_id,
        "username": user_info.username,
        "first_name": user_info.first_name,
        "last_name": user_info.last_name
    }
    
    success, _ = await safe_api_call(
        lambda: api_client.create_user(new_user_data),
        None,
        "создание пользователя для информации о подсказках",
        handle_errors=False
    )
    
    return success

def _get_hint_info_content() -> dict:
    """
    Get structured hint information content.
    НОВОЕ: Централизованная информация о подсказках для лучшей поддерживаемости.
    
    Returns:
        dict: Structured hint information with all details
    """
    return {
        "title": "💡 Система подсказок",
        "description": (
            "Подсказки помогают вам лучше запоминать иностранные слова! "
            "Каждый тип подсказки работает по-своему и может быть настроен индивидуально."
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
                "• Использование любой подсказки автоматически устанавливает оценку 0 для слова",
                "• Слово с использованной подсказкой будет показано для повторения через 1 день",
                "• Подсказки сохраняются индивидуально для каждого пользователя",
                "• Вы можете создавать текстовые подсказки или записывать голосовые заметки",
                "• Подсказки можно редактировать и удалять в любое время"
            ]
        },
        "footer": "Для получения дополнительной справки используйте команду /help"
    }

def _get_hint_type_description(hint_type: str) -> str:
    """
    Get detailed description for a specific hint type.
    НОВОЕ: Детальные описания для каждого типа подсказки.
    
    Args:
        hint_type: Type of hint
        
    Returns:
        str: Detailed description of the hint type
    """
    descriptions = {
        "phoneticsound": (
            "Разбиение слова на слоги и звуки для лучшего произношения. "
            "Помогает понять, как правильно произносить слово по частям."
        ),
        "phoneticassociation": (
            "Ассоциации звучания слова с знакомыми русскими словами или звуками. "
            "Помогает запомнить произношение через знакомые звуковые образы."
        ),
        "meaning": (
            "Дополнительные значения, синонимы, контекст использования слова. "
            "Помогает лучше понять смысл и случаи применения слова."
        ),
        "writing": (
            "Мнемонические приемы для запоминания написания слова. "
            "Особенно полезно для языков с нелатинскими алфавитами или сложным написанием."
        )
    }
    
    return descriptions.get(hint_type, "Специальный тип подсказки для улучшения запоминания.")

def _format_hint_info_text(hint_info: dict, user_hint_settings: dict = None) -> str:
    """
    Format hint information into readable text.
    НОВОЕ: Форматирование информации о подсказках с учетом пользовательских настроек.
    
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
    
    text += hint_info['footer']
    
    return text

@hint_router.message(Command("hint"))
async def cmd_hint(message: Message, state: FSMContext):
    """
    Handle the /hint command which provides information about hint functionality.
    ОБНОВЛЕНО: Улучшена архитектура, добавлена информация о пользовательских настройках.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    logger.info(f"'/hint' command from {full_name} ({username})")

    # Set state for viewing hint info
    await state.set_state(UserStates.viewing_hint_info)
    
    # Preserve existing state data
    current_data = await state.get_data()
    await state.update_data(**current_data)

    # Get API client and try to ensure user exists (best effort)
    api_client = get_api_client_from_bot(message.bot)
    user_hint_settings = None
    
    if api_client:
        user_exists = await _ensure_user_exists_quietly(message.from_user, api_client)
        if user_exists:
            logger.debug(f"User {user_id} ensured in database for hint info")
            
            # Try to get user's individual hint settings
            try:
                user_hint_settings = await get_individual_hint_settings(message, state)
                logger.debug(f"Retrieved hint settings for user {user_id}")
            except Exception as e:
                logger.warning(f"Could not retrieve hint settings for user {user_id}: {e}")
        else:
            logger.warning(f"Could not ensure user {user_id} exists for hint info")
    else:
        logger.warning("API client not available for hint info")

    # Get and format hint information
    hint_info = _get_hint_info_content()
    hint_text = _format_hint_info_text(hint_info, user_hint_settings)
    
    # Add personalized footer if we have user settings
    if user_hint_settings:
        enabled_count = sum(1 for enabled in user_hint_settings.values() if enabled)
        total_count = len(user_hint_settings)
        
        hint_text += f"\n\n📊 <b>Ваши настройки:</b> {enabled_count}/{total_count} типов подсказок включено"
        
        if enabled_count < total_count:
            hint_text += f"\n💡 Используйте /settings для настройки отдельных типов подсказок"
    
    # Send hint information
    await message.answer(hint_text, parse_mode="HTML")

# НОВОЕ: Дополнительные обработчики для расширенной функциональности
@hint_router.callback_query(F.data == "hint_detailed_info")
async def process_hint_detailed_info(callback: CallbackQuery, state: FSMContext):
    """
    Handle request for detailed hint information.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"Detailed hint info requested by {callback.from_user.full_name}")
    
    await callback.answer("📖 Подробная информация...")
    
    detailed_info = _get_detailed_hint_examples()
    await callback.message.answer(detailed_info, parse_mode="HTML")

def _get_detailed_hint_examples() -> str:
    """
    Get detailed examples for each hint type.
    НОВОЕ: Детальные примеры использования подсказок.
    
    Returns:
        str: Formatted examples text
    """
    return (
        "📖 <b>Подробные примеры подсказок</b>\n\n"
        
        "🎵 <b>Звучание по слогам (Фонетика):</b>\n"
        "Слово: beautiful\n"
        "Подсказка: beau-ti-ful (бью-ти-фул)\n"
        "Помогает разбить сложное слово на части\n\n"
        
        "💡 <b>Ассоциация для фонетики:</b>\n"
        "Слово: cat\n"
        "Подсказка: звучит как 'кэт' - похоже на 'кот'\n"
        "Связывает звучание с знакомыми звуками\n\n"
        
        "🧠 <b>Ассоциация для значения:</b>\n"
        "Слово: dog\n"
        "Подсказка: собака = верный друг = лучший друг человека\n"
        "Создает смысловые связи и образы\n\n"
        
        "✍️ <b>Ассоциация для написания:</b>\n"
        "Слово: friend\n"
        "Подсказка: F-R-I-E-N-D = Forever Reliable, Intelligent, Encouraging, Nice, Dear\n"
        "Помогает запомнить порядок букв\n\n"
        
        "💭 <b>Советы по созданию подсказок:</b>\n"
        "• Используйте яркие, запоминающиеся образы\n"
        "• Связывайте с личным опытом\n"
        "• Не делайте подсказки слишком длинными\n"
        "• Записывайте голосовые заметки для произношения\n"
        "• Регулярно пересматривайте и улучшайте подсказки"
    )

@hint_router.callback_query(F.data == "hint_settings_info")
async def process_hint_settings_info(callback: CallbackQuery, state: FSMContext):
    """
    Handle request for hint settings information.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"Hint settings info requested by {callback.from_user.full_name}")
    
    await callback.answer("⚙️ Настройки подсказок...")
    
    settings_info = _get_hint_settings_info()
    await callback.message.answer(settings_info, parse_mode="HTML")

def _get_hint_settings_info() -> str:
    """
    Get information about hint settings.
    НОВОЕ: Информация о настройках подсказок.
    
    Returns:
        str: Formatted settings information
    """
    settings_text = (
        "⚙️ <b>Настройки подсказок</b>\n\n"
        
        "В разделе настроек (/settings) вы можете индивидуально управлять каждым типом подсказок:\n\n"
    )
    
    # Add information about each setting
    for setting_key in HINT_SETTING_KEYS:
        setting_name = get_hint_setting_name(setting_key)
        if setting_name:
            settings_text += f"• <b>{setting_name}</b>\n"
    
    settings_text += (
        "\n<b>Возможности настроек:</b>\n"
        "✅ Включить - подсказки этого типа будут показываться\n"
        "❌ Отключить - подсказки этого типа будут скрыты\n"
        "🔄 Групповые операции - включить/отключить все сразу\n\n"
        
        "<b>Зачем отключать подсказки?</b>\n"
        "• Если определенный тип подсказок вам не помогает\n"
        "• Для фокусировки на конкретных аспектах изучения\n"
        "• Для упрощения интерфейса во время изучения\n"
        "• Для создания собственной системы изучения\n\n"
        
        "Используйте команду /settings для доступа к настройкам подсказок."
    )
    
    return settings_text

# НОВОЕ: Utility functions for other modules  
async def get_user_hint_preferences(message_or_callback, state: FSMContext) -> dict:
    """
    Get user's hint preferences with fallback.
    НОВОЕ: Утилита для получения предпочтений пользователя по подсказкам.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM context
        
    Returns:
        dict: User's hint preferences or default values
    """
    try:
        return await get_individual_hint_settings(message_or_callback, state)
    except Exception as e:
        logger.warning(f"Could not get hint preferences: {e}")
        # Return default settings if we can't get user preferences
        return {key: True for key in HINT_SETTING_KEYS}

def format_hint_status_summary(hint_settings: dict) -> str:
    """
    Format a brief summary of hint settings status.
    НОВОЕ: Краткая сводка статуса настроек подсказок.
    
    Args:
        hint_settings: User's hint settings
        
    Returns:
        str: Brief status summary
    """
    if not hint_settings:
        return "Настройки подсказок недоступны"
    
    enabled_count = sum(1 for enabled in hint_settings.values() if enabled)
    total_count = len(hint_settings)
    
    if enabled_count == total_count:
        return f"Все подсказки включены ({total_count}/{total_count})"
    elif enabled_count == 0:
        return f"Все подсказки отключены (0/{total_count})"
    else:
        return f"Подсказки: {enabled_count}/{total_count} включено"

# Export router and utilities
__all__ = [
    'hint_router',
    'get_user_hint_preferences',
    'format_hint_status_summary'
]
