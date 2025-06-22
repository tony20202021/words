"""
Basic user command handlers for Language Learning Bot.
Handles start, help, and other basic commands.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import safe_api_call
from app.bot.keyboards.user_keyboards import create_welcome_keyboard
from app.utils.user_utils import get_or_create_user
from app.bot.handlers.user.stats_handlers import get_user_progress_data

# Создаем роутер для базовых обработчиков
basic_router = Router()

# Set up logging
logger = setup_logger(__name__)

@basic_router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """
    Handle the /start command for new users.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    logger.info(f"'/start' message from {full_name} ({username})")

    await handle_start_command(message, state, is_callback=False)

def _format_welcome_message(
    full_name: str, 
    languages: list, 
    user_progress: list, 
    has_error: bool = False, 
    error_msg: str = ""
) -> str:
    """
    Format welcome message based on user data and system state.
    
    Args:
        full_name: User's full name
        languages: List of available languages
        user_progress: User's progress data
        has_error: Whether there was an error
        error_msg: Error message if any
        
    Returns:
        str: Formatted welcome message
    """
    message = ""
    
    # Handle error state
    if has_error:
        message += (
            f"⚠️ Не удалось получить полные данные с сервера.\n"
            f"Причина: {error_msg}\n\n"
            f"Функциональность может быть ограничена. Попробуйте позже или обратитесь к администратору.\n\n"
            f"Используйте кнопки ниже для навигации или команду /help для справки."
        )
        return message
    
    # Add languages information
    if languages:
        message += f"🌍 В системе доступно для изучения:\n"
        message += f"{len(languages)} языков.\n\n"
    else:
        message += "🌍 В системе пока нет доступных языков. Обратитесь к администратору.\n\n"
    
    # Add progress information
    if user_progress:
        message += "📊 Ваш прогресс по языкам:\n"
        for progress in user_progress:
            lang_name = progress.get("language_name_ru", "Неизвестный язык")
            progress_percentage = progress.get("progress_percentage", 0)
            words_studied = progress.get("words_studied", 0)
            message += f"• {lang_name}: {progress_percentage:.1f}% ({words_studied} слов)\n"
        message += "\n"
    else:
        message += (
            "У вас пока нет прогресса по изучению языков.\n"
            "Начните с выбора языка для изучения.\n\n"
        )
    
    # Add call to action using buttons
    message += "📋 Используйте кнопки ниже для навигации:"
    
    return message

async def handle_start_command(
    message_or_callback, 
    state: FSMContext, 
    is_callback: bool = False
):
    """
    Common handler logic for start command.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: The FSM state context
        is_callback: Whether this is called from a callback handler
    """
    # Clear state to prevent conflicts
    await state.clear()

    # Extract user info and message object
    if is_callback:
        user_info = message_or_callback.from_user
        message = message_or_callback.message
        bot = message_or_callback.bot
    else:
        user_info = message_or_callback.from_user
        message = message_or_callback
        bot = message_or_callback.bot
    
    full_name = user_info.full_name or user_info.first_name or "Пользователь"
    
    logger.info(f"Start command handler for {full_name} ({user_info.username})")

    welcome_message = f"👋 Здравствуйте, {full_name}!\n\n"
    welcome_message += "Добро пожаловать в бот для изучения иностранных слов!\n\n"
    await message.answer(welcome_message)

    # Get API client
    api_client = get_api_client_from_bot(bot)
    if not api_client:
        error_msg = (
            "⚠️ Не удалось установить соединение с сервером. "
            "Бот может работать некорректно. Пожалуйста, попробуйте позже или "
            "обратитесь к администратору."
        )
        # Send error message with limited keyboard
        keyboard = create_welcome_keyboard(has_error=True)
        await message.answer(error_msg, reply_markup=keyboard)
        logger.error(f"API client not available during start command from {full_name}")
        return

    # Get or create user
    db_user_id, user_data = await get_or_create_user(message_or_callback.from_user, api_client)
    
    # Get languages list
    success, languages = await safe_api_call(
        lambda: api_client.get_languages(),
        message,
        "получение списка языков",
        handle_errors=False
    )
    
    if not success:
        # Show welcome with error state
        welcome_message = _format_welcome_message(
            full_name, [], [], 
            has_error=True, 
            error_msg="Не удалось получить список языков"
        )
        keyboard = create_welcome_keyboard(has_error=True)
        await message.answer(welcome_message, reply_markup=keyboard)
        return
    
    languages = languages or []
    
    # Get user progress if user exists
    languages_with_progress = []
    if db_user_id:
        # Save user ID to state
        await state.update_data(db_user_id=db_user_id)
        
        # Get progress summary
        languages_with_progress, languages_without_progress = await get_user_progress_data(message, state, db_user_id, languages, api_client)

    # Handle user creation errors
    if not db_user_id and "error" in user_data:
        welcome_message = _format_welcome_message(
            full_name, languages, [],
            has_error=True,
            error_msg=user_data["error"]
        )
        keyboard = create_welcome_keyboard(has_error=True)
        await message.answer(welcome_message, reply_markup=keyboard)
        return
    
    # Format and send welcome message with keyboard
    welcome_message = _format_welcome_message(full_name, languages, languages_with_progress)
    keyboard = create_welcome_keyboard(has_error=False)
    await message.answer(welcome_message, reply_markup=keyboard)

@basic_router.callback_query(F.data == "retry_start")
async def process_retry_start(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to retry start command after error.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info(f"'retry_start' callback from {callback.from_user.full_name}")
    
    await callback.answer("🔄 Повторная попытка...")
    
    # Use common handler logic
    await handle_start_command(callback, state, is_callback=True)

@basic_router.callback_query(F.data == "show_settings")
async def process_show_settings_callback(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to show settings.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info(f"'show_settings' callback from {callback.from_user.full_name}")
    
    await callback.answer("⚙️ Настройки...")
    await callback.message.answer(
        "⚙️ Для просмотра настроек используйте команду /settings\n\n"
        "В настройках вы можете изменить параметры обучения."
    )

# Export router and utilities
__all__ = [
    'basic_router',
    'handle_start_command',
]
