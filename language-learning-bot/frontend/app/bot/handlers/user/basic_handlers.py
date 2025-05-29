"""
Basic user command handlers for Language Learning Bot.
Handles start, help, and other basic commands.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import safe_api_call
from app.bot.handlers.user.help_handlers import process_help
from app.bot.handlers.user.hint_handlers import process_hint
from app.bot.handlers.user.stats_handlers import process_stats
from app.bot.keyboards.user_keyboards import create_welcome_keyboard
from app.bot.handlers.language_handlers import process_language
    

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

async def _get_or_create_user(user_info, api_client) -> tuple[str, dict]:
    """
    Централизованная логика создания/получения пользователя.
    
    Args:
        user_info: User information from Telegram
        api_client: API client instance
        
    Returns:
        tuple: (db_user_id, user_data) or (None, None) if failed
    """
    user_id = user_info.id
    username = user_info.username
    
    # Try to get existing user
    user_response = await api_client.get_user_by_telegram_id(user_id)
    
    if not user_response["success"]:
        logger.error(f"Failed to get user with Telegram ID {user_id}: {user_response['error']}")
        return None, {"error": user_response.get("error", "Неизвестная ошибка")}
    
    users = user_response["result"]
    existing_user = users[0] if users and isinstance(users, list) and len(users) > 0 else None
    
    if existing_user:
        return existing_user.get("id"), existing_user
    
    # Create new user if doesn't exist
    new_user_data = {
        "telegram_id": user_id,
        "username": username,
        "first_name": user_info.first_name,
        "last_name": user_info.last_name
    }
    
    create_response = await api_client.create_user(new_user_data)
    
    if not create_response["success"]:
        logger.error(f"Failed to create user with Telegram ID {user_id}: {create_response['error']}")
        return None, {"error": create_response.get("error", "Неizvestnaya ошибка")}
    
    created_user = create_response["result"]
    return created_user.get("id") if created_user else None, created_user

async def _get_user_progress_summary(db_user_id: str, languages: list, api_client) -> list:
    """
    Вынесена логика получения прогресса пользователя.
    
    Args:
        db_user_id: Database user ID
        languages: List of available languages
        api_client: API client instance
        
    Returns:
        list: List of progress data for languages with progress
    """
    user_progress_by_language = []
    
    for language in languages:
        try:
            progress_response = await api_client.get_user_progress(db_user_id, language.get("id"))
            
            if progress_response["success"] and progress_response["result"]:
                progress_data = progress_response["result"]
                # Only include languages with actual progress
                if progress_data.get("words_studied", 0) > 0:
                    user_progress_by_language.append(progress_data)
                    
        except Exception as e:
            logger.error(f"Error getting progress for language {language.get('id')}: {e}")
            continue
    
    return user_progress_by_language

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
    message = f"👋 Здравствуйте, {full_name}!\n\n"
    message += "Добро пожаловать в бот для изучения иностранных слов!\n\n"
    
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
    db_user_id, user_data = await _get_or_create_user(user_info, api_client)
    
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
    user_progress = []
    if db_user_id:
        # Save user ID to state
        await state.update_data(db_user_id=db_user_id)
        
        # Get progress summary
        user_progress = await _get_user_progress_summary(db_user_id, languages, api_client)
    
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
    welcome_message = _format_welcome_message(full_name, languages, user_progress)
    keyboard = create_welcome_keyboard(has_error=False)
    await message.answer(welcome_message, reply_markup=keyboard)

@basic_router.callback_query(F.data == "back_to_start")
async def process_back_to_main(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to return to the main menu.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'back_to_start' callback from {full_name} ({username})")
    
    # Use common handler logic
    await handle_start_command(callback, state, is_callback=True)
    
    await callback.answer("🏠 Возврат в главное меню")

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

# DEPRECATED: Old callback handlers kept for compatibility
@basic_router.callback_query(F.data == "start_study")
async def process_start_study_callback(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to start studying words.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info(f"'start_study' callback from {callback.from_user.full_name}")
    
    # Check if language is selected
    state_data = await state.get_data()
    current_language = state_data.get("current_language")
    
    if not current_language or not current_language.get("id"):
        await callback.answer("Сначала выберите язык", show_alert=True)
        await callback.message.answer(
            "⚠️ Сначала выберите язык для изучения с помощью команды /language"
        )
        return
    
    await callback.answer("🎓 Запуск изучения...")
    await callback.message.answer(
        "🎓 Для начала изучения используйте команду /study\n\n"
        "Если нужно изменить настройки, используйте /settings"
    )

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

# НОВОЕ: Utility functions for other modules
def get_user_display_name(user) -> str:
    """
    Get user display name with fallback options.
    НОВОЕ: Утилита для получения отображаемого имени пользователя.
    
    Args:
        user: User object from Telegram
        
    Returns:
        str: Display name for the user
    """
    return (
        user.full_name or 
        user.first_name or 
        user.username or 
        f"User_{user.id}"
    )

async def ensure_api_client(bot) -> tuple[bool, object]:
    """
    Утилита для проверки доступности API клиента.
    
    Args:
        bot: Bot instance
        
    Returns:
        tuple: (is_available, api_client_or_none)
    """
    api_client = get_api_client_from_bot(bot)
    if not api_client:
        logger.error("API client not available")
        return False, None
    return True, api_client

# Export router and utilities
__all__ = [
    'basic_router',
    'handle_start_command',
    'get_user_display_name', 
    'ensure_api_client'
]
