"""
Handlers for study commands in the Language Learning Bot.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import handle_api_error, validate_state_data
from app.utils.state_models import UserWordState

from app.bot.handlers.study.study_states import StudyStates
from app.bot.handlers.study.study_words import get_words_for_study
from app.utils.formatting_utils import format_settings_text

# Создаем роутер для обработчиков команд изучения
study_router = Router()

logger = setup_logger(__name__)

@study_router.message(Command("study"))
async def cmd_study(message: Message, state: FSMContext):
    """
    Handle the /study command which starts the learning process.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Сначала очищаем состояние для предотвращения конфликтов
    # Но в данном случае мы хотим сохранить данные пользователя
    current_data = await state.get_data()
    await state.set_state(None)
    await state.update_data(**current_data)
    
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    logger.info(f"'/study' command from {full_name} ({username}, ID={user_id})")
    
    # Get API client
    api_client = get_api_client_from_bot(message.bot)

    if not api_client:
        logger.error(f"Ошибка: (API client not found in bot or dispatcher)")
        await message.answer(
            f"Ошибка: (API client not found in bot or dispatcher)"
        )
        return

    state_data = await state.get_data()
    is_valid = ("current_language" in state_data)
    
    if not is_valid:
        await message.answer(
            "⚠️ Вы еще не выбрали язык для изучения!\n"
            "Сейчас я помогу вам выбрать язык."
        )
        
        # автоматически вызываем команду выбора языка
        # Импортируем функцию для обработки команды выбора языка
        from app.bot.handlers.language_handlers import cmd_language
        
        # Вызываем функцию выбора языка
        try:
            await cmd_language(message, state)
            return  # Завершаем текущую функцию, так как cmd_language уже отправит ответ
        except Exception as e:
            logger.error(f"Error calling cmd_language: {e}", exc_info=True)
            # Если произошла ошибка, продолжаем с базовым сообщением
            await message.answer(
                "Произошла ошибка при автоматическом вызове команды выбора языка.\n"
                "Пожалуйста, используйте команду /language, чтобы выбрать язык вручную."
            )
            return
    
    # Get language data
    current_language = state_data["current_language"]
    current_language_id = current_language.get("id")
    
    if not current_language_id:
        await message.answer(
            "⚠️ Неверные данные о выбранном языке!\n"
            "Используйте команду /language, чтобы выбрать язык заново."
        )
        return
    
    # Get user data
    user_response = await api_client.get_user_by_telegram_id(user_id)
    
    # Initialize db_user_id
    db_user_id = None
    
    # Handle API error
    if not user_response["success"]:
        await handle_api_error(
            user_response,
            message,
            "Error getting user data",
            "Ошибка при получении данных пользователя"
        )
        return
    
    # Check if user exists
    users = user_response["result"]
    user = users[0] if users and len(users) > 0 else None
    
    if not user:
        # Create new user
        user_info = {
            "telegram_id": user_id,
            "username": username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name
        }
        
        create_user_response = await api_client.create_user(user_info)
        
        # Handle API error
        if not create_user_response["success"]:
            await handle_api_error(
                create_user_response,
                message,
                "Error creating user",
                "Ошибка при регистрации пользователя"
            )
            return
        
        # Get user ID from response
        db_user_id = create_user_response["result"].get("id") or create_user_response["result"].get("_id")
    else:
        # Get user ID from existing user
        db_user_id = user.get("id") or user.get("_id")
    
    # Verify we have user ID
    if not db_user_id:
        await message.answer(
            "❌ Не удалось получить ID пользователя. Пожалуйста, попробуйте позже."
        )
        return
    
    # Double-check language exists
    language_response = await api_client.get_language(current_language_id)
    
    if not language_response["success"] or not language_response["result"]:
        await message.answer(
            "⚠️ Выбранный язык не найден!\n"
            "Используйте команду /language, чтобы выбрать язык."
        )
        return
    
    language = language_response["result"]
    
    # Получаем настройки пользователя для выбранного языка
    from app.utils.settings_utils import get_user_language_settings
    
    settings = await get_user_language_settings(message, state)
    
    # Извлекаем настройки
    start_word = settings.get("start_word", 1)
    skip_marked = settings.get("skip_marked", False)
    use_check_date = settings.get("use_check_date", True)
    show_hints = settings.get("show_hints", True)
    show_debug = settings.get("show_debug", True)
    
    # Обновляем состояние FSM для совместимости со старым кодом
    await state.update_data(
        start_word=start_word,
        skip_marked=skip_marked,
        use_check_date=use_check_date,
        show_hints=show_hints,
        show_debug=show_debug,
    )
    
    # Show start message с информацией о настройке
    settings_text = format_settings_text(
        start_word=start_word, 
        skip_marked=skip_marked, 
        use_check_date=use_check_date,
        show_hints=show_hints,
        show_debug=show_debug,
        prefix=f"📚 Начинаем изучение слов языка: {language.get('name_ru')} ({language.get('name_foreign')})\n\n",
        suffix="\n\n🔄 Получаю список слов..."
    )
    
    await message.answer(
        settings_text,
        parse_mode="HTML",
    )
    
    # Save user ID to state
    await state.update_data(db_user_id=db_user_id)
    
    # Set study state
    await state.set_state(StudyStates.studying)
    
    # Create study settings
    study_settings = {
        "start_word": start_word,
        "skip_marked": skip_marked,
        "use_check_date": use_check_date,
        "show_hints": show_hints,
        "show_debug": show_debug,
    }
    
    # Get words for study
    await get_words_for_study(message, state, db_user_id, current_language_id, study_settings)
