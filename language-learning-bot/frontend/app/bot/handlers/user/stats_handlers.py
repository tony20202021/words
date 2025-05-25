"""
Statistics command handlers for Language Learning Bot.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.bot.states.centralized_states import UserStates

# Создаем роутер для обработчиков статистики
stats_router = Router()

# Set up logging
logger = setup_logger(__name__)

@stats_router.message(Command("stats"))
async def cmd_stats(message: Message, state: FSMContext):
    """
    Handle the /stats command which shows user statistics.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # ИСПРАВЛЕНО: Устанавливаем состояние просмотра статистики и НЕ сбрасываем его
    await state.set_state(UserStates.viewing_stats)
    
    # Сохраняем данные пользователя
    current_data = await state.get_data()
    await state.update_data(**current_data)
    
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    logger.info(f"'/stats' command from {full_name} ({username})")
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(message.bot)
    
    # Получение данных состояния
    user_data = await state.get_data()
    logger.debug("User data: %s", user_data)
    
    # Проверяем, зарегистрирован ли пользователь
    user_response = await api_client.get_user_by_telegram_id(user_id)
    
    if not user_response["success"]:
        logger.error(f"Failed to get user with Telegram ID {user_id}: {user_response['error']}")
        await message.answer("Ошибка при получении данных пользователя. Попробуйте позже.")
        return
        
    users = user_response["result"]
    user = users[0] if users and len(users) > 0 else None
    
    db_user_id = None
    if not user:
        # Пользователь не найден, создаем его
        new_user_data = {
            "telegram_id": user_id,
            "username": username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name
        }
        create_response = await api_client.create_user(new_user_data)
        if not create_response["success"]:
            logger.error(f"Failed to create user with Telegram ID {user_id}: {create_response['error']}")
            await message.answer("Ошибка при регистрации пользователя. Попробуйте позже.")
            return
        db_user_id = create_response["result"].get("id") if create_response["result"] else None
    else:
        db_user_id = user.get("id")
    
    # Получаем список языков из API
    languages_response = await api_client.get_languages()
    
    if not languages_response["success"]:
        logger.error(f"Failed to get languages: {languages_response['error']}")
        await message.answer("Ошибка при получении списка языков. Попробуйте позже.")
        return
        
    languages = languages_response["result"] or []
    
    if not languages:
        await message.answer(
            "📊 Статистика\n\n"
            "В системе пока нет доступных языков. Обратитесь к администратору.\n\n"
            "Доступные команды:\n"
            "/language - Выбор языка\n"
            "/help - Справка\n"
            "/start - Главное меню\n"
            "/cancel - Выйти из просмотра статистики"
        )
        return
    
    # Собираем статистику по всем языкам
    user_progress_by_language = []
    languages_without_progress = []
    
    for language in languages:
        language_id = language.get("id")
        language_name_ru = language.get("name_ru")
        language_name_foreign = language.get("name_foreign")
        
        # Получаем количество слов в языке
        word_count_response = await api_client.get_word_count_by_language(language_id)
        total_words = word_count_response.get("result", {}).get("count", 0) if word_count_response.get("success") else 0
        
        # Сохраняем информацию о количестве слов в языке
        language["total_words"] = total_words
        
        # Получаем прогресс пользователя для конкретного языка
        try:
            progress_response = await api_client.get_user_progress(db_user_id, language_id)
            
            if progress_response["success"] and progress_response["result"]:
                # Добавляем только если есть статистика и изучено слов больше 0
                progress = progress_response["result"]
                if progress.get("words_studied", 0) > 0:
                    # Добавляем информацию о количестве слов в языке
                    progress["total_words"] = total_words
                    user_progress_by_language.append(progress)
                else:
                    languages_without_progress.append(language)
            else:
                languages_without_progress.append(language)
        except Exception as e:
            logger.error(f"Error getting progress for language {language_id}: {e}")
            languages_without_progress.append(language)
    
    if not user_progress_by_language and not languages_without_progress:
        await message.answer(
            "📊 Статистика\n\n"
            "У вас пока нет статистики по изучению языков.\n"
            "Начните с выбора языка с помощью команды /language\n\n"
            "Доступные команды:\n"
            "/language - Выбор языка\n"
            "/help - Справка\n"
            "/start - Главное меню\n"
            "/cancel - Выйти из просмотра статистики"
        )
        return
    
    # Формируем сообщение со статистикой
    stats_text = "📊 Статистика по изучению языков\n\n"
    
    if user_progress_by_language:
        for progress in user_progress_by_language:
            lang_name = progress.get("language_name_ru")
            lang_name_foreign = progress.get("language_name_foreign")
            total_words = progress.get("total_words", 0)
            words_studied = progress.get("words_studied", 0)
            words_known = progress.get("words_known", 0)
            words_skipped = progress.get("words_skipped", 0)
            progress_percentage = progress.get("progress_percentage", 0)
            last_study_date = progress.get("last_study_date")
            
            stats_text += f"🔹 {lang_name} ({lang_name_foreign}):\n"
            stats_text += f"  - Всего слов в языке: {total_words}\n"
            stats_text += f"  - Изучено слов: {words_studied}\n"
            stats_text += f"  - Известно слов: {words_known}\n"
            stats_text += f"  - Пропущено слов: {words_skipped}\n"
            stats_text += f"  - Прогресс: {progress_percentage:.1f}%\n"
            
            if last_study_date:
                stats_text += f"  - Последняя дата изучения: {last_study_date.split('T')[0]}\n"
            
            stats_text += "\n"
    
    # Добавляем информацию о языках без статистики
    if languages_without_progress:
        stats_text += "Доступные языки без статистики:\n"
        for language in languages_without_progress:
            lang_name = language.get("name_ru")
            lang_name_foreign = language.get("name_foreign")
            total_words = language.get("total_words", 0)
            
            stats_text += f"- {lang_name} ({lang_name_foreign}) - {total_words} слов\n"
    
    # ИСПРАВЛЕНО: Добавляем информацию о доступных командах
    stats_text += "\nДоступные команды:\n"
    stats_text += "/language - Выбор языка для изучения\n"
    stats_text += "/study - Начать изучение слов\n"
    stats_text += "/settings - Настройки обучения\n"
    stats_text += "/help - Справка\n"
    stats_text += "/start - Главное меню\n"
    stats_text += "/cancel - Выйти из просмотра статистики"
    
    await message.answer(stats_text)
    
    # ИСПРАВЛЕНО: НЕ очищаем состояние после показа статистики
    # Состояние будет очищено только при переходе в другую команду или /cancel
    