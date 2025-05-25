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

# Импортируем централизованные состояния
from app.bot.states.centralized_states import HintStates, StudyStates

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
    
    # НОВОЕ: Временно устанавливаем состояние изучения
    # (get_words_for_study установит правильное состояние)
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

# НОВОЕ: Обработчик команд из состояния завершения изучения
@study_router.message(Command("study"), StudyStates.study_completed)
async def cmd_study_from_completed(message: Message, state: FSMContext):
    """
    Handle the /study command when user is in study_completed state.
    This allows restarting the study process.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    logger.info(f"'/study' command from completed state from {message.from_user.full_name}")
    
    await message.answer("🔄 Перезапускаем процесс изучения...")
    
    # Вызываем основной обработчик команды /study
    await cmd_study(message, state)

@study_router.message(Command("stats"), StudyStates.study_completed)
async def cmd_stats_from_completed(message: Message, state: FSMContext):
    """
    Handle the /stats command when user is in study_completed state.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    logger.info(f"'/stats' command from completed state from {message.from_user.full_name}")
    
    # Импортируем и вызываем обработчик статистики
    try:
        from app.bot.handlers.user_handlers import cmd_stats
        await cmd_stats(message, state)
    except Exception as e:
        logger.error(f"Error calling cmd_stats from completed state: {e}", exc_info=True)
        await message.answer("❌ Ошибка при получении статистики. Попробуйте позже.")

@study_router.message(Command("settings"), StudyStates.study_completed)
async def cmd_settings_from_completed(message: Message, state: FSMContext):
    """
    Handle the /settings command when user is in study_completed state.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    logger.info(f"'/settings' command from completed state from {message.from_user.full_name}")
    
    # Импортируем и вызываем обработчик настроек
    try:
        from app.bot.handlers.user.settings_handlers import cmd_settings
        await cmd_settings(message, state)
    except Exception as e:
        logger.error(f"Error calling cmd_settings from completed state: {e}", exc_info=True)
        await message.answer("❌ Ошибка при получении настроек. Попробуйте позже.")

# НОВОЕ: Обработчики команд во время изучения
@study_router.message(Command("cancel"), StudyStates.studying)
@study_router.message(Command("cancel"), StudyStates.viewing_word_details)
@study_router.message(Command("cancel"), StudyStates.confirming_word_knowledge)
async def cmd_cancel_study(message: Message, state: FSMContext):
    """
    Handle the /cancel command during study process.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    current_state = await state.get_state()
    logger.info(f"'/cancel' command during study from {message.from_user.full_name}, state: {current_state}")
    
    # Очищаем состояние изучения
    await state.set_state(None)
    
    await message.answer(
        "✅ Изучение слов прервано.\n\n"
        "Чтобы продолжить изучение, используйте команду /study\n"
        "Для просмотра статистики - /stats\n"
        "Для изменения настроек - /settings"
    )

@study_router.message(Command("help"), StudyStates.studying)
@study_router.message(Command("help"), StudyStates.viewing_word_details)
@study_router.message(Command("help"), StudyStates.confirming_word_knowledge)
@study_router.message(Command("help"), StudyStates.study_completed)
async def cmd_help_during_study(message: Message, state: FSMContext):
    """
    Handle the /help command during study process.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    current_state = await state.get_state()
    logger.info(f"'/help' command during study from {message.from_user.full_name}, state: {current_state}")
    
    help_text = "📚 <b>Помощь по изучению слов:</b>\n\n"
    
    if current_state == StudyStates.study_completed.state:
        help_text += (
            "🎉 Вы изучили все доступные слова!\n\n"
            "<b>Доступные команды:</b>\n"
            "/study - начать изучение заново\n"
            "/stats - посмотреть статистику\n"
            "/settings - изменить настройки\n"
            "/language - выбрать другой язык\n"
        )
    elif current_state in [StudyStates.studying.state, StudyStates.viewing_word_details.state, StudyStates.confirming_word_knowledge.state]:
        help_text += (
            "Вы сейчас изучаете слова. Используйте кнопки под сообщениями для взаимодействия.\n\n"
            "<b>Доступные команды:</b>\n"
            "/cancel - прервать изучение\n"
            "/stats - посмотреть статистику (не прерывая изучение)\n"
            "/settings - изменить настройки (не прерывая изучение)\n\n"
            "<b>Подсказки:</b>\n"
            "💡 Используйте кнопки подсказок для лучшего запоминания\n"
            "🎙️ Можете записывать голосовые подсказки\n"
            "⏩ Помечайте сложные слова для пропуска\n"
        )
    else:
        help_text += (
            "Используйте /study для начала изучения слов\n"
            "/language для выбора языка\n"
            "/settings для настройки процесса обучения"
        )
    
    await message.answer(help_text, parse_mode="HTML")

# НОВОЕ: Обработчик неизвестных сообщений во время изучения
@study_router.message(StudyStates.studying)
@study_router.message(StudyStates.viewing_word_details)
@study_router.message(StudyStates.confirming_word_knowledge)
async def handle_unknown_message_during_study(message: Message, state: FSMContext):
    """
    Handle unknown messages during study process.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    current_state = await state.get_state()
    logger.info(f"Unknown message during study from {message.from_user.full_name}, state: {current_state}, text: {message.text[:50] if message.text else 'No text'}")
    
    # Проверяем, не является ли это командой
    from app.utils.error_utils import is_command
    
    if message.text and is_command(message.text):
        # Это команда, но она не обработана - значит недоступна в данном состоянии
        await message.answer(
            f"⚠️ Команда {message.text.split()[0]} недоступна во время изучения слов.\n\n"
            "Используйте кнопки под сообщениями для взаимодействия или:\n"
            "/cancel - прервать изучение\n"
            "/help - получить помощь"
        )
    else:
        # Обычное сообщение
        await message.answer(
            "⚠️ Используйте кнопки под сообщениями для изучения слов.\n\n"
            "Или воспользуйтесь командами:\n"
            "/cancel - прервать изучение\n"
            "/help - получить помощь"
        )

@study_router.message(StudyStates.study_completed)
async def handle_message_in_completed_state(message: Message, state: FSMContext):
    """
    Handle messages when study is completed.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    logger.info(f"Message in completed state from {message.from_user.full_name}, text: {message.text[:50] if message.text else 'No text'}")
    
    # Проверяем, не является ли это командой
    from app.utils.error_utils import is_command
    
    if message.text and is_command(message.text):
        # Это команда, но она не обработана специально
        await message.answer(
            f"⚠️ Команда {message.text.split()[0]} недоступна.\n\n"
            "🎉 Вы завершили изучение всех слов!\n\n"
            "Доступные команды:\n"
            "/study - начать изучение заново\n"
            "/stats - посмотреть статистику\n"
            "/settings - изменить настройки\n"
            "/language - выбрать другой язык"
        )
    else:
        # Обычное сообщение
        await message.answer(
            "🎉 Поздравляем! Вы изучили все доступные слова!\n\n"
            "Что хотите сделать дальше?\n"
            "/study - начать изучение заново\n"
            "/stats - посмотреть статистику\n"
            "/settings - изменить настройки\n"
            "/language - выбрать другой язык"
        )
        