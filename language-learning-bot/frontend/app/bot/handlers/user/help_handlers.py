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
from app.bot.states.centralized_states import UserStates
from app.bot.keyboards.user_keyboards import create_help_keyboard
from app.utils.user_utils import get_or_create_user

# Создаем роутер для справочных обработчиков
help_router = Router()

# Set up logging
logger = setup_logger(__name__)

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
        "use_hint": "Более подробно узнать про подсказки - команда /hint",
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
    text += "\n"
    text += "\n"

    text += help_content['use_hint']    
    
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
        db_user_id, user_data = await get_or_create_user(message_or_callback.from_user, api_client)
        user_exists = db_user_id is not None
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

# Export router and utilities
__all__ = [
    'help_router',
]
