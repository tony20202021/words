"""
Handlers for language selection and management in the Language Learning Bot.
These handlers allow users to select languages for learning and administrators to manage languages.
"""

from aiogram import Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.settings_utils import get_user_language_settings
from app.utils.formatting_utils import format_settings_text
from app.utils.settings_utils import get_user_language_settings

# Создаем роутер для обработчиков языков
language_router = Router()

logger = setup_logger(__name__)


async def get_available_languages(api_client):
    """
    Get list of available languages.
    
    Args:
        api_client: API client instance
    
    Returns:
        API response with languages list in result field
    """
    # Получаем список языков через API клиент
    response = await api_client.get_languages()
    return response


async def get_language_by_id(api_client, language_id):
    """
    Get language by ID.
    
    Args:
        api_client: API client instance
        language_id: Language ID to retrieve
    
    Returns:
        API response with language data in result field
    """
    # Получаем язык по ID через API клиент
    response = await api_client.get_language(language_id)
    return response


@language_router.message(Command("language"))
async def cmd_language(message: Message, state: FSMContext):
    """
    Handle the /language command which shows available languages.
    
    Args:
        message: The message object from Telegram
    """
    # Сначала очищаем состояние для предотвращения конфликтов
    # Но в данном случае мы хотим сохранить данные пользователя
    current_data = await state.get_data()
    await state.set_state(None)
    await state.update_data(**current_data)

    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    logger.info(f"'/language' command from {full_name} ({username})")
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(message.bot)
    
    # Получение данных состояния
    user_data = await state.get_data()
    logger.debug("User data: %s", user_data)
    
    # Получаем список языков используя выделенную функцию
    api_response = await get_available_languages(api_client)

    if not api_response['success']:
        await message.answer(
            f"Ошибка при получении списка языков: (status={api_response['status']}) error={api_response['error']}"
        )
        return

    languages = api_response['result']
    
    if not languages:
        await message.answer(
            "В системе пока нет доступных языков. "
            "Обратитесь к администратору бота."
        )
        return
    
    # Получаем данные о текущем выбранном языке пользователя
    current_language = user_data.get("current_language")
    current_language_id = current_language.get("id") if current_language else None
    
    # Получаем прогресс пользователя по языкам
    db_user_id = user_data.get("db_user_id")
    
    # Если нет ID пользователя в состоянии, получим его из API
    if not db_user_id:
        user_response = await api_client.get_user_by_telegram_id(user_id)
        if user_response['success'] and user_response['result']:
            users = user_response['result']
            user = users[0] if users else None
            if user:
                db_user_id = user.get("id")
                await state.update_data(db_user_id=db_user_id)
    
    # Собираем информацию о прогрессе по языкам
    languages_with_progress = []
    
    # Если есть ID пользователя, получаем прогресс
    if db_user_id:
        for language in languages:
            lang_id = language.get("id")
            word_count_response = await api_client.get_word_count_by_language(lang_id)
            total_words = word_count_response.get("result", {}).get("count", 0) if word_count_response.get("success") else 0
            
            progress_response = await api_client.get_user_progress(db_user_id, lang_id)
            progress = None
            if progress_response.get("success") and progress_response.get("result"):
                progress = progress_response.get("result")
            
            # Формируем данные о языке
            lang_data = {
                "id": lang_id,
                "name_ru": language.get("name_ru"),
                "name_foreign": language.get("name_foreign"),
                "total_words": total_words,
                "progress": progress,
                "is_current": lang_id == current_language_id
            }
            languages_with_progress.append(lang_data)

            if (lang_id == current_language_id):
                current_language.update(lang_data)
    else:
        # Если нет ID пользователя, просто добавляем базовую информацию
        for language in languages:
            lang_id = language.get("id")
            word_count_response = await api_client.get_word_count_by_language(lang_id)
            total_words = word_count_response.get("result", {}).get("count", 0) if word_count_response.get("success") else 0
            
            lang_data = {
                "id": lang_id,
                "name_ru": language.get("name_ru"),
                "name_foreign": language.get("name_foreign"),
                "total_words": total_words,
                "progress": None,
                "is_current": lang_id == current_language_id
            }
            languages_with_progress.append(lang_data)
    
    # Формируем сообщение о текущем языке
    languages_text = ""
    if current_language:
        total_words = current_language.get("total_words", 0)
        progress = current_language.get("progress")
        languages_text += f"🔹 Текущий язык: {current_language.get('name_ru')} ({current_language.get('name_foreign')})"
        if progress:
            progress_percentage = progress.get("progress_percentage", 0)
            words_studied = progress.get("words_studied", 0)
            languages_text += f" - Прогресс: {progress_percentage:.1f}% ({words_studied} изучено)"
    
    languages_text += "\n\n"
    languages_text += "🌍 Доступные языки для изучения:\n\n"
    
    # Добавляем информацию о языках и прогрессе
    for lang in languages_with_progress:
        if not lang.get("is_current"):
            lang_name = lang.get("name_ru")
            lang_name_foreign = lang.get("name_foreign")
            total_words = lang.get("total_words", 0)
            progress = lang.get("progress")
            
            languages_text += f"• {lang_name} ({lang_name_foreign}) - {total_words} слов"
            
            # Если есть прогресс, добавляем его
            if progress:
                progress_percentage = progress.get("progress_percentage", 0)
                words_studied = progress.get("words_studied", 0)
                if words_studied > 0:
                    languages_text += f" - Прогресс: {progress_percentage:.1f}% ({words_studied} изучено)"
            
            languages_text += "\n"
    
    languages_text += "\nВыберите язык с помощью кнопок ниже:"
    
    # Добавляем информацию о доступных командах
    languages_text += "\n\nДругие доступные команды:\n"
    languages_text += "/help - Получить справку\n"
    languages_text += "/study - Начать изучение слов\n"
    languages_text += "/settings - Настройки процесса обучения\n"
    languages_text += "/stats - Показать статистику\n"
    languages_text += "/start - Вернуться на начальный экран"
    
    # Создаем клавиатуру с кнопками для выбора языка
    keyboard_builder = InlineKeyboardBuilder()
    for lang in languages_with_progress:
        # Формируем текст кнопки с информацией о прогрессе
        button_text = f"{lang['name_ru']} ({lang['name_foreign']})"
        
        # Добавляем информацию о количестве слов
        button_text += f" - {lang['total_words']} сл."
        
        # Если есть прогресс, добавляем процент
        if lang.get("progress"):
            if lang['progress'].get('words_studied', 0) > 0:
                button_text += f" - {lang['progress'].get('progress_percentage', 0):.1f}%"
        
        keyboard_builder.button(
            text=button_text,
            callback_data=f"lang_select_{lang['id']}"
        )
    keyboard_builder.adjust(1)  # Размещаем кнопки по одной в ряд
    
    await message.answer(languages_text, reply_markup=keyboard_builder.as_markup())

@language_router.callback_query(F.data.startswith("lang_select_"))
async def process_language_selection(callback: CallbackQuery, state: FSMContext):
    """
    Process language selection callback.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'=lang_select_' command from {full_name} ({username})")
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(callback.bot)
    
    # Получение данных состояния
    user_data = await state.get_data()
    logger.debug("User data: %s", user_data)
    
    # Извлекаем ID языка из callback_data
    language_id = callback.data.split("_")[2]
    
    # Получаем информацию о выбранном языке используя выделенную функцию
    language_response = await get_language_by_id(api_client, language_id)
    
    if not language_response['success'] or not language_response['result']:
        await callback.answer("Ошибка: язык не найден")
        return
    
    language = language_response['result']
    
    # Сохраняем выбранный язык в состоянии пользователя
    await state.update_data(current_language=language)
    
    # Проверяем наличие пользователя в системе
    api_response = await api_client.get_user_by_telegram_id(user_id)
    if not api_response['success']:
        await callback.answer(
            f"Ошибка при обращении к сервису: (status={api_response['status']}) error={api_response['error']}" +
            "/n" +
            "api_response={api_response}"
        )
        return
    
    users = api_response['result']
    user = users[0] if users and len(users) > 0 else None
    
    # Если пользователь не найден, создаем его
    if not user:
        user_data = {
            "telegram_id": user_id,
            "username": username,
            "first_name": callback.from_user.first_name,
            "last_name": callback.from_user.last_name
        }
        create_response = await api_client.create_user(user_data)
        if not create_response['success']:
            logger.error(f"Failed to create user with Telegram ID {user_id}")
            await callback.answer("Ошибка при регистрации пользователя")
            return
        user = create_response['result']
    
    # Сохраняем ID пользователя в состоянии
    db_user_id = user.get("id")
    await state.update_data(db_user_id=db_user_id)
    
    # Получаем прогресс пользователя по выбранному языку
    api_response = await api_client.get_user_progress(user["id"], language_id)
    if not api_response['success'] and api_response['status'] == 404:
        # Если получаем 404, это значит, что прогресс еще не создан для этого пользователя и языка
        # Используем пустые значения прогресса
        progress = {
            "words_studied": 0,
            "words_known": 0,
            "words_skipped": 0,
            "total_words": 0,
            "progress_percentage": 0
        }
    else:
        progress = api_response['result']
    
    # Загружаем настройки пользователя для выбранного языка
    settings = await get_user_language_settings(callback, state)
    
    # Обновляем настройки в состоянии FSM
    await state.update_data(
        start_word=settings.get("start_word", 1),
        skip_marked=settings.get("skip_marked", False),
        use_check_date=settings.get("use_check_date", True),
        show_hints=settings.get("show_hints", True)  # Добавляем настройку подсказок
    )

    # Форматируем текст настроек
    settings_prefix = "⚙️ Ваши настройки для этого языка:\n"
    settings_text = format_settings_text(
        start_word=settings.get("start_word", 1),
        skip_marked=settings.get("skip_marked", False),
        use_check_date=settings.get("use_check_date", True),
        show_hints=settings.get("show_hints", True),
        prefix=settings_prefix
    )

    # Показываем информацию о выбранном языке и статистику
    await callback.message.answer(
        f"✅ Вы выбрали язык: <b>{language['name_ru']} ({language['name_foreign']})</b>\n\n"
        f"📊 Ваша статистика по этому языку:\n"
        f"- Изучено слов: {progress.get('words_studied', 0)}\n"
        f"- Известно слов: {progress.get('words_known', 0)}\n"
        f"- Пропущено слов: {progress.get('words_skipped', 0)}\n"
        f"- Всего слов: {progress.get('total_words', 0)}\n\n"
        f"Прогресс: {progress.get('progress_percentage', 0):.1f}%\n\n"
        f"{settings_text}\n\n"
        f"Теперь вы можете:\n"
        f"- Начать изучение с помощью команды /study\n"
        f"- Настроить процесс обучения с помощью команды /settings\n"
        f"- Посмотреть подробную статистику с помощью команды /stats",
        parse_mode="HTML",
    )    

    await callback.answer()

def register_handlers(dp: Dispatcher):
    """
    Register all language handlers.
    
    Args:
        dp: The dispatcher instance
    """
    # Для aiogram 3.x используем include_router
    dp.include_router(language_router)
