"""
Help command handlers for Language Learning Bot.
FIXED: Removed code duplication, improved architecture, better user experience.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import safe_api_call
from app.bot.states.centralized_states import UserStates
from app.bot.keyboards.user_keyboards import create_help_keyboard

# Создаем роутер для справочных обработчиков
help_router = Router()

# Set up logging
logger = setup_logger(__name__)

# Централизованная функция для обеспечения существования пользователя
async def _ensure_user_exists(user_info, api_client) -> bool:
    """
    Ensure user exists in database (simplified version for help context).
    
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
        None,  # No message object for error handling
        "проверка существования пользователя",
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
        "создание пользователя",
        handle_errors=False
    )
    
    return success

def _get_help_content() -> dict:
    """
    Get structured help content.
    
    Returns:
        dict: Structured help content with sections
    """
    return {
        "title": "📚 Справка по использованию бота",
        "description": (
            "Этот бот поможет вам эффективно изучать иностранные слова "
            "с использованием системы интервального повторения."
        ),
        "sections": {
            "commands": {
                "title": "🔹 Основные команды:",
                "items": [
                    "/start - Начать работу с ботом",
                    "/language - Выбрать язык для изучения", 
                    "/study - Начать изучение слов",
                    "/settings - Настройки процесса обучения",
                    "/stats - Показать статистику",
                    "/hint - Информация о подсказках",
                    "/cancel - Отмена текущего действия"
                ]
            },
            "process": {
                "title": "🔹 Процесс изучения:",
                "items": [
                    "1. Выберите язык командой /language",
                    "2. Настройте процесс обучения командой /settings",
                    "3. Начните изучение командой /study",
                    "4. Для каждого слова вы можете:",
                    "   • Придумывать и использовать свои собственные подсказки",
                    "   • Отметить слово как запомненое/неизвестное",
                    "   • Пропустить слово"
                ]
            },
            "repetition": {
                "title": "🔹 Система интервального повторения:",
                "items": [
                    "• Если вы отметили слово как запомненое, его интервал повторения увеличивается в 2 раза",
                    "• Интервалы повторения: 1, 2, 4, 8, 16, 32 дня",
                    "• Если вы не знаете слово, интервал сбрасывается до 1 дня",
                    "• При просмотре подсказки интервал также сбрасывается"
                ]
            },
            "hints": {
                "title": "🔹 Система подсказок:",
                "items": [
                    "Подсказки придумываются самостоятельно самим пользователем.",
                    "• Значение - ассоциация для слова на русском",
                    "• Фонетическая ассоциация - связь с похожими по звучанию словами",
                    "• Фонетика - разбиение слова на слоги",
                    "• Написание - мнемонические приемы для запоминания",
                    "• В настройках можно индивидуально включать/отключать типы подсказок"
                ]
            }
        },
        "footer": "Если у вас остались вопросы, обратитесь к администратору бота (@Anton_Mikhalev).",
        "use_start": "Вызвать главное меню и начать обучение - можно по команде /start",
    }

def _format_help_text(help_content: dict) -> str:
    """
    Format help content into readable text.
    
    Args:
        help_content: Structured help content
        
    Returns:
        str: Formatted help text
    """
    text = f"{help_content['title']}\n\n"
    text += f"{help_content['description']}\n\n"
    
    for section_key, section in help_content['sections'].items():
        text += f"{section['title']}\n"
        for item in section['items']:
            text += f"{item}\n"
        text += "\n"
    
    text += help_content['footer']
    text += "\n"
    text += "\n"

    text += help_content['use_start']    
    
    return text

@help_router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    await process_help(message, state)

@help_router.callback_query(F.data == "show_help")
async def process_show_help_callback(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to show help.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info(f"'show_help' callback from {callback.from_user.full_name}")
    
    await callback.answer("📚 Справка...")
    
    await process_help(callback, state)

async def process_help(message_or_callback, state: FSMContext):
    """
    Handle the /help command which shows bot instructions.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    user_id = message_or_callback.from_user.id
    username = message_or_callback.from_user.username
    full_name = message_or_callback.from_user.full_name

    logger.info(f"'/help' command from {full_name} ({username})")

    # Set state for viewing help
    await state.set_state(UserStates.viewing_help)
    
    # Preserve existing state data
    current_data = await state.get_data()
    await state.update_data(**current_data)

    # Get API client and ensure user exists (best effort, non-blocking)
    api_client = get_api_client_from_bot(message_or_callback.bot)
    if api_client:
        user_exists = await _ensure_user_exists(message_or_callback.from_user, api_client)
        if user_exists:
            logger.debug(f"User {user_id} ensured in database")
        else:
            logger.warning(f"Could not ensure user {user_id} exists in database")
    else:
        logger.warning("API client not available for user creation")

    # Get and format help content
    help_content = _get_help_content()
    help_text = _format_help_text(help_content)
    
    # Create interactive keyboard for better UX
    keyboard = create_help_keyboard()
    
    if isinstance(message_or_callback, CallbackQuery):
        message = message_or_callback.message
    else:
        message = message_or_callback

    # Send help message
    await message.answer(
        help_text,
        reply_markup=keyboard,
        parse_mode="HTML" if "<" in help_text else None
    )
# НОВОЕ: Дополнительные утилитарные обработчики
@help_router.callback_query(F.data == "help_about_hints")
async def process_help_about_hints(callback: CallbackQuery, state: FSMContext):
    """
    Handle detailed hints information request.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"Help about hints by {callback.from_user.full_name}")
    
    await callback.answer("💡 Подробно о подсказках...")
    
    hints_help = (
        "💡 <b>Подробная информация о подсказках</b>\n\n"
        
        "🎵 <b>Фонетика (звучание по слогам):</b>\n"
        "Разбиение слова на части для лучшего произношения\n"
        "Пример: hello → hel-lo\n\n"
        
        "💡 <b>Ассоциация для фонетики:</b>\n"
        "Связь звучания с знакомыми словами\n"
        "Пример: cat звучит как 'кэт'\n\n"
        
        "🧠 <b>Ассоциация для значения:</b>\n"
        "Связь значения с русскими словами или образами\n"
        "Пример: dog → собака → верный друг\n\n"
        
        "✍️ <b>Ассоциация для написания:</b>\n"
        "Мнемонические приемы для запоминания написания\n"
        "Пример: друг на английском friend — F-R-I-E-N-D\n\n"
        
        "⚙️ В настройках (/settings) вы можете индивидуально включать и отключать каждый тип подсказок.\n\n"
        
        "❗️ <b>Важно:</b> Использование любой подсказки автоматически сбрасывает интервал повторения слова к 1 дню."
    )
    
    await callback.message.answer(hints_help, parse_mode="HTML")

@help_router.callback_query(F.data == "help_contact_admin")
async def process_help_contact_admin(callback: CallbackQuery, state: FSMContext):
    """
    Handle admin contact information request.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"Help contact admin by {callback.from_user.full_name}")
    
    await callback.answer("👨‍💼 Контакты администратора...")
    
    admin_contact = (
        "👨‍💼 <b>Связь с администратором</b>\n\n"
        
        "Если у вас возникли вопросы, проблемы или предложения по улучшению бота, "
        "вы можете обратиться к администратору:\n\n"
        
        "📱 Telegram: @Anton_Mikhalev\n"
        "📧 Email: anton.v.mikhalev@gmail.com\n\n"
        
        "🔧 <b>При обращении укажите:</b>\n"
        "• Описание проблемы или вопроса\n"
        "• Что вы делали, когда возникла проблема\n"
        "• Скриншот (если применимо)\n\n"
        
        "⏰ <b>Время ответа:</b> обычно в течение 24 часов"
    )
    
    await callback.message.answer(admin_contact, parse_mode="HTML")

# НОВОЕ: Функция для получения контекстной справки
async def get_contextual_help(current_state: str) -> str:
    """
    Get contextual help based on current user state.
    НОВОЕ: Контекстная справка в зависимости от текущего состояния.
    
    Args:
        current_state: Current FSM state
        
    Returns:
        str: Contextual help message
    """
    context_help = {
        "UserStates:selecting_language": (
            "🌍 Вы выбираете язык для изучения.\n"
            "Используйте кнопки выше для выбора языка или /cancel для отмены."
        ),
        "SettingsStates:viewing_settings": (
            "⚙️ Вы в меню настроек.\n"
            "Используйте кнопки для изменения параметров или /cancel для выхода."
        ),
        "StudyStates:studying": (
            "📚 Вы изучаете слова.\n"
            "Используйте кнопки для оценки знания слов или /cancel для завершения."
        ),
        "StudyStates:study_completed": (
            "🎉 Изучение завершено!\n"
            "Используйте /study для повтора или /language для выбора другого языка."
        )
    }
    
    return context_help.get(
        current_state,
        "Используйте доступные команды для навигации по боту."
    )

# Export router and utilities
__all__ = [
    'help_router',
    'get_contextual_help'
]
