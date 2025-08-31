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
from app.bot.states.centralized_states import UserStates
from app.bot.keyboards.user_keyboards import create_language_selected_keyboard
from app.bot.handlers.study.word_actions.word_navigation_actions import update_daily_statistics
from app.utils.statistics_utils import show_monthly_statistics, show_today_statistics

# Создаем роутер для обработчиков языков
language_router = Router()

logger = setup_logger(__name__)


@language_router.message(Command("language"))
async def cmd_language(message: Message, state: FSMContext):
    await process_language(message, state)

@language_router.callback_query(F.data == "select_language")
async def process_select_language_callback(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to select language.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info(f"'select_language' callback from {callback.from_user.full_name}")
    
    await callback.answer()

    await process_language(callback, state)

async def process_language(message_or_callback: Message, state: FSMContext):
    """
    Handle the /language command which shows available languages.
    
    Args:
        message: The message object from Telegram
    """
    # Устанавливаем состояние выбора языка и НЕ сбрасываем его
    await state.set_state(UserStates.selecting_language)
    
    # Сохраняем данные пользователя, но очищаем другие состояния
    current_data = await state.get_data()
    await state.update_data(**current_data)

    user_id = message_or_callback.from_user.id
    username = message_or_callback.from_user.username
    full_name = message_or_callback.from_user.full_name

    logger.info(f"'/language' command from {full_name} ({username})")
    
    if isinstance(message_or_callback, CallbackQuery):
        message = message_or_callback.message
    else:
        message = message_or_callback

    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(message_or_callback.bot)

    if not api_client:
        logger.error(f"Ошибка при получении списка языков: (API client not found in bot or dispatcher)")
        await message.answer(
            f"Ошибка при получении списка языков: (API client not found in bot or dispatcher)"
        )
        return

    # Получение данных состояния
    user_data = await state.get_data()
    logger.debug("User data: %s", user_data)
    
    # Получаем список языков используя выделенную функцию
    api_response = await api_client.get_languages()

    if not api_response['success']:
        logger.error(f"Ошибка при получении списка языков: (status={api_response['status']}) error={api_response['error']}")
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
        languages_progress = user_data.get("languages_progress", {})        

        for language in languages:
            lang_id = language.get("id")

            word_count_response = await api_client.get_word_count_by_language(lang_id)
            total_words = word_count_response.get("result", {}).get("count", 0) if word_count_response.get("success") else 0
            
            if lang_id in languages_progress:
                progress = languages_progress.get(lang_id)
            else:
                progress_response = await api_client.get_user_progress(db_user_id, lang_id)
                progress = None
                if progress_response.get("success") and progress_response.get("result"):
                    progress = progress_response.get("result")
                
                await message.answer(f"Получен прогресс по языку {language.get('name_ru')}")

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
    languages_text += "/start - Вернуться на начальный экран\n"
    languages_text += "/help - Получить справку\n"
    languages_text += "/hint - Информация о подсказках\n"
    languages_text += "/stats - Показать статистику\n"
    
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
    
    await callback.answer("Язык выбран.")

    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(callback.bot)
    
    # Получение данных состояния
    user_data = await state.get_data()
    logger.debug("User data: %s", user_data)
    
    # Извлекаем ID языка из callback_data
    language_id = callback.data.split("_")[2]
    
    # Получаем информацию о выбранном языке используя выделенную функцию
    language_response = await api_client.get_language(language_id)
    
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
    languages_progress = user_data.get("languages_progress", {})        

    if language_id in languages_progress:
        progress = languages_progress.get(language_id)
    else:
        api_response = await api_client.get_user_progress(user["id"], language_id)

        if not api_response['success'] and api_response['status'] == 404:
            # Если получаем 404, это значит, что прогресс еще не создан для этого пользователя и языка
            # Используем пустые значения прогресса
            progress = {
                "words_studied": 0,
                "words_known": 0,
                "words_skipped": 0,
                "total_words": 0,
                "words_for_today": 0,
                "progress_percentage": 0
            }
        else:
            progress = api_response['result']

        await callback.message.answer(f"Получен прогресс по языку {language.get('name_ru')}")

    await state.update_data(
        progress=progress,
    )

    # обновляем дневную статистику
    await update_daily_statistics(callback, state)

    # Загружаем настройки пользователя для выбранного языка
    settings = await get_user_language_settings(callback, state)
    
    # Обновляем настройки в состоянии FSM
    await state.update_data(
        settings=settings,
    )

    # Очищаем состояние выбора языка после успешного выбора
    await state.set_state(None)

    # Форматируем текст настроек
    settings_prefix = "⚙️ Ваши настройки для этого языка:\n"
    settings_text = format_settings_text(
        start_word=settings.get("start_word", 1),
        skip_marked=settings.get("skip_marked", False),
        use_check_date=settings.get("use_check_date", True),
        show_check_date=settings.get("show_check_date", True),
        show_big=settings.get("show_big", False),
        show_writing_images=settings.get("show_writing_images", False),
        show_radicals=settings.get("show_radicals", True),
        show_references=settings.get("show_references", True),
        show_tones=settings.get("show_tones", True),
        show_short_captions=settings.get("show_short_captions", True),
        hint_settings={
            "show_hint_phoneticsound": settings.get("show_hint_phoneticsound", True),
            "show_hint_phoneticassociation": settings.get("show_hint_phoneticassociation", True),
            "show_hint_meaning": settings.get("show_hint_meaning", True),
            "show_hint_writing": settings.get("show_hint_writing", True),
        },
        show_debug=settings.get("show_debug", True),
        show_charts=settings.get("show_charts", False),
        receive_messages=settings.get("receive_messages", True),
        reset_session_days=settings.get("reset_session_days", 1),
        reset_session_hours=settings.get("reset_session_hours", 6),
        unknown_limit_new_words=settings.get("unknown_limit_new_words", 10),
        prefix=settings_prefix,
    )
    keyboard = create_language_selected_keyboard()

    progress_studied_total = 100 * (progress.get('words_studied', 0) / progress.get('total_words', 0)) if progress.get('total_words', 0) > 0 else 0
    progress_known_studied = 100 * (progress.get('words_known', 0) / progress.get('words_studied', 0)) if progress.get('words_studied', 0) > 0 else 0

    # Показываем информацию о выбранном языке и статистику
    await callback.message.answer(
        f"✅ Вы выбрали язык: <b>{language['name_ru']} ({language['name_foreign']})</b>\n\n",
        parse_mode="HTML",
    )    
    await callback.message.answer(
        f"{settings_text}\n\n",
        parse_mode="HTML",
    )    
    await callback.message.answer(
        f"📊 Ваша статистика по этому языку:\n"
        f"- Изучено слов: {progress.get('words_studied', 0)}\n"
        f"- Пропущено слов: {progress.get('words_skipped', 0)}\n"
        f"- Известно слов: {progress.get('words_known', 0)}\n"
        f"- Неизвестно слов: {progress.get('words_studied', 0) - progress.get('words_known', 0) - progress.get('words_skipped', 0)}\n"
        f"- Слов на текущую сессию: {progress.get('words_for_today', 0)}\n"
        f"- Всего слов: {progress.get('total_words', 0)}\n"
        f"Прогресс изучено/всего: {progress_studied_total:.1f}%\n"
        f"Прогресс известно/изучено: {progress_known_studied:.1f}%\n\n",
        parse_mode="HTML",
    )    

    show_charts = settings.get("show_charts", False)
    if show_charts:
        await show_monthly_statistics(callback, state)
        await show_today_statistics(callback, state)

    await callback.message.answer(
        f"Теперь вы можете:\n"
        f"- Начать изучение: /study\n"
        f"- Настроить процесс обучения: /settings\n",
        parse_mode="HTML",
        reply_markup=keyboard,
    )    


def register_handlers(dp: Dispatcher):
    """
    Register all language handlers.
    
    Args:
        dp: The dispatcher instance
    """
    # Для aiogram 3.x используем include_router
    dp.include_router(language_router)
    