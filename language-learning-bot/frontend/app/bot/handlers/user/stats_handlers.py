"""
Statistics command handlers for Language Learning Bot.
FIXED: Removed code duplication, improved architecture, better data presentation.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import safe_api_call, handle_api_error
from app.bot.states.centralized_states import UserStates
from app.bot.keyboards.user_keyboards import create_stats_keyboard

# Создаем роутер для обработчиков статистики
stats_router = Router()

# Set up logging
logger = setup_logger(__name__)

# НОВОЕ: Централизованная функция для получения или создания пользователя
async def _get_or_create_user_for_stats(user_info, api_client) -> Tuple[Optional[str], Optional[str]]:
    """
    Get existing user or create new one for statistics context.
    НОВОЕ: Специализированная версия для контекста статистики.
    
    Args:
        user_info: User information from Telegram
        api_client: API client instance
        
    Returns:
        tuple: (db_user_id, error_message) - one will be None
    """
    user_id = user_info.id
    username = user_info.username
    
    # Try to get existing user
    success, users = await safe_api_call(
        lambda: api_client.get_user_by_telegram_id(user_id),
        None,
        "получение данных пользователя для статистики",
        handle_errors=False
    )
    
    if not success:
        return None, "Не удалось получить данные пользователя"
    
    existing_user = users[0] if users and len(users) > 0 else None
    
    if existing_user:
        return existing_user.get("id"), None
    
    # Create new user if doesn't exist
    new_user_data = {
        "telegram_id": user_id,
        "username": username,
        "first_name": user_info.first_name,
        "last_name": user_info.last_name
    }
    
    success, created_user = await safe_api_call(
        lambda: api_client.create_user(new_user_data),
        None,
        "создание пользователя для статистики",
        handle_errors=False
    )
    
    if not success:
        return None, "Не удалось создать пользователя"
    
    return created_user.get("id") if created_user else None, None

async def _get_languages_with_word_counts(api_client) -> Tuple[List[Dict], Optional[str]]:
    """
    Get all languages with their word counts.
    НОВОЕ: Получение языков с информацией о количестве слов.
    
    Args:
        api_client: API client instance
        
    Returns:
        tuple: (languages_list, error_message) - error_message is None if successful
    """
    # Get languages list
    success, languages = await safe_api_call(
        lambda: api_client.get_languages(),
        None,
        "получение списка языков для статистики",
        handle_errors=False
    )
    
    if not success:
        return [], "Не удалось получить список языков"
    
    languages = languages or []
    
    # Add word counts to each language
    for language in languages:
        language_id = language.get("id")
        
        # Get word count for this language
        success, count_result = await safe_api_call(
            lambda: api_client.get_word_count_by_language(language_id),
            None,
            f"получение количества слов для языка {language_id}",
            handle_errors=False
        )
        
        if success and count_result:
            language["total_words"] = count_result.get("count", 0)
        else:
            language["total_words"] = 0
    
    return languages, None

async def _get_user_progress_data(db_user_id: str, languages: List[Dict], api_client) -> Tuple[List[Dict], List[Dict]]:
    """
    Get user progress data for all languages.
    НОВОЕ: Разделение языков на те, где есть прогресс, и те, где его нет.
    
    Args:
        db_user_id: Database user ID
        languages: List of available languages
        api_client: API client instance
        
    Returns:
        tuple: (languages_with_progress, languages_without_progress)
    """
    languages_with_progress = []
    languages_without_progress = []
    
    for language in languages:
        language_id = language.get("id")
        
        try:
            success, progress_data = await safe_api_call(
                lambda: api_client.get_user_progress(db_user_id, language_id),
                None,
                f"получение прогресса для языка {language_id}",
                handle_errors=False
            )
            
            if success and progress_data and progress_data.get("words_studied", 0) > 0:
                # Add total words info to progress data
                progress_data["total_words"] = language.get("total_words", 0)
                languages_with_progress.append(progress_data)
            else:
                languages_without_progress.append(language)
                
        except Exception as e:
            logger.error(f"Error getting progress for language {language_id}: {e}")
            languages_without_progress.append(language)
    
    return languages_with_progress, languages_without_progress

def _format_progress_stats(progress_data: List[Dict]) -> str:
    """
    Format progress statistics into readable text.
    НОВОЕ: Форматирование статистики прогресса.
    
    Args:
        progress_data: List of progress data for languages
        
    Returns:
        str: Formatted progress statistics
    """
    if not progress_data:
        return ""
    
    stats_text = "📊 <b>Ваш прогресс по языкам:</b>\n\n"
    
    # Sort by progress percentage for better presentation
    sorted_progress = sorted(progress_data, key=lambda x: x.get("progress_percentage", 0), reverse=True)
    
    for progress in sorted_progress:
        lang_name = progress.get("language_name_ru", "Неизвестный язык")
        lang_name_foreign = progress.get("language_name_foreign", "")
        total_words = progress.get("total_words", 0)
        words_studied = progress.get("words_studied", 0)
        words_known = progress.get("words_known", 0)
        words_skipped = progress.get("words_skipped", 0)
        progress_percentage = progress.get("progress_percentage", 0)
        last_study_date = progress.get("last_study_date")
        
        # Format language name
        if lang_name_foreign:
            language_display = f"{lang_name} ({lang_name_foreign})"
        else:
            language_display = lang_name
        
        stats_text += f"🔹 <b>{language_display}</b>\n"
        
        # Progress bar visualization
        progress_bar = _create_progress_bar(progress_percentage)
        stats_text += f"   {progress_bar} {progress_percentage:.1f}%\n"
        
        # Detailed statistics
        stats_text += f"   📚 Всего слов: <b>{total_words}</b>\n"
        stats_text += f"   📖 Изучено: <b>{words_studied}</b>\n"
        stats_text += f"   ✅ Известно: <b>{words_known}</b>\n"
        
        if words_skipped > 0:
            stats_text += f"   ⏩ Пропущено: <b>{words_skipped}</b>\n"
        
        # Last study date
        if last_study_date:
            formatted_date = _format_date_friendly(last_study_date)
            stats_text += f"   🕒 Последнее изучение: {formatted_date}\n"
        
        stats_text += "\n"
    
    return stats_text

def _format_available_languages(languages: List[Dict]) -> str:
    """
    Format available languages without progress.
    НОВОЕ: Форматирование доступных языков без прогресса.
    
    Args:
        languages: List of languages without progress
        
    Returns:
        str: Formatted available languages text
    """
    if not languages:
        return ""
    
    stats_text = "🌍 <b>Доступные языки для изучения:</b>\n"
    
    # Sort by total words count for better presentation
    sorted_languages = sorted(languages, key=lambda x: x.get("total_words", 0), reverse=True)
    
    for language in sorted_languages:
        lang_name = language.get("name_ru", "Неизвестный язык")
        lang_name_foreign = language.get("name_foreign", "")
        total_words = language.get("total_words", 0)
        
        # Format language name
        if lang_name_foreign:
            language_display = f"{lang_name} ({lang_name_foreign})"
        else:
            language_display = lang_name
        
        stats_text += f"• {language_display} — {total_words} слов\n"
    
    return stats_text

def _create_progress_bar(progress_percentage: float, length: int = 10) -> str:
    """
    Create a visual progress bar.
    НОВОЕ: Визуальная полоса прогресса.
    
    Args:
        progress_percentage: Progress percentage (0-100)
        length: Length of the progress bar
        
    Returns:
        str: Visual progress bar
    """
    filled_length = int(length * progress_percentage / 100)
    bar = '█' * filled_length + '░' * (length - filled_length)
    return f"[{bar}]"

def _format_date_friendly(date_str: str) -> str:
    """
    Format date in a user-friendly way.
    НОВОЕ: Дружественное форматирование даты.
    
    Args:
        date_str: ISO date string
        
    Returns:
        str: User-friendly date string
    """
    try:
        if 'T' in date_str:
            date_part = date_str.split('T')[0]
        else:
            date_part = date_str
            
        date_obj = datetime.strptime(date_part, '%Y-%m-%d')
        
        # Calculate days difference
        today = datetime.now().date()
        study_date = date_obj.date()
        days_diff = (today - study_date).days
        
        if days_diff == 0:
            return "сегодня"
        elif days_diff == 1:
            return "вчера"
        elif days_diff < 7:
            return f"{days_diff} дн. назад"
        elif days_diff < 30:
            weeks = days_diff // 7
            return f"{weeks} нед. назад"
        else:
            return date_obj.strftime('%d.%m.%Y')
            
    except Exception as e:
        logger.warning(f"Error formatting date {date_str}: {e}")
        return date_str.split('T')[0] if 'T' in date_str else date_str

def _get_stats_summary(progress_data: List[Dict], available_languages: List[Dict]) -> str:
    """
    Get overall statistics summary.
    НОВОЕ: Общая сводка статистики.
    
    Args:
        progress_data: List of progress data
        available_languages: List of available languages
        
    Returns:
        str: Summary statistics text
    """
    total_languages = len(progress_data) + len(available_languages)
    active_languages = len(progress_data)
    
    if not progress_data:
        return f"📈 <b>Общая статистика:</b> {total_languages} языков доступно, изучение не начато\n\n"
    
    total_words_studied = sum(p.get("words_studied", 0) for p in progress_data)
    total_words_known = sum(p.get("words_known", 0) for p in progress_data)
    avg_progress = sum(p.get("progress_percentage", 0) for p in progress_data) / len(progress_data)
    
    summary = f"📈 <b>Общая статистика:</b>\n"
    summary += f"🎯 Активных языков: {active_languages} из {total_languages}\n"
    summary += f"📚 Всего изучено слов: {total_words_studied}\n"
    summary += f"✅ Всего известных слов: {total_words_known}\n" 
    summary += f"📊 Средний прогресс: {avg_progress:.1f}%\n\n"
    
    return summary

@stats_router.message(Command("stats"))
async def cmd_stats(message: Message, state: FSMContext):
    """
    Handle the /stats command which shows user statistics.
    ОБНОВЛЕНО: Упрощена архитектура, улучшено представление данных.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    logger.info(f"'/stats' command from {full_name} ({username})")
    
    # Set state for viewing statistics
    await state.set_state(UserStates.viewing_stats)
    
    # Preserve existing state data
    current_data = await state.get_data()
    await state.update_data(**current_data)

    # Get API client
    api_client = get_api_client_from_bot(message.bot)
    if not api_client:
        await message.answer("❌ Ошибка подключения к серверу. Попробуйте позже.")
        return

    # Get or create user
    db_user_id, user_error = await _get_or_create_user_for_stats(message.from_user, api_client)
    if not db_user_id:
        await message.answer(f"❌ {user_error}. Попробуйте позже.")
        return

    # Update state with user ID
    await state.update_data(db_user_id=db_user_id)

    # Get languages with word counts
    languages, lang_error = await _get_languages_with_word_counts(api_client)
    if lang_error:
        await message.answer(f"❌ {lang_error}. Попробуйте позже.")
        return

    if not languages:
        await message.answer(
            "📊 <b>Статистика</b>\n\n"
            "В системе пока нет доступных языков. Обратитесь к администратору.\n\n"
            "Доступные команды:\n"
            "/language - Выбор языка\n"
            "/help - Справка\n"
            "/start - Главное меню"
        )
        return

    # Get user progress data
    progress_data, available_languages = await _get_user_progress_data(db_user_id, languages, api_client)

    # Check if user has any activity
    if not progress_data and not available_languages:
        await message.answer(
            "📊 <b>Статистика</b>\n\n"
            "У вас пока нет статистики по изучению языков.\n"
            "Начните с выбора языка с помощью команды /language\n\n"
            "Доступные команды:\n"
            "/language - Выбор языка\n"
            "/help - Справка\n"
            "/start - Главное меню"
        )
        return

    # Format complete statistics message
    stats_text = "📊 <b>Статистика по изучению языков</b>\n\n"
    
    # Add summary
    stats_text += _get_stats_summary(progress_data, available_languages)
    
    # Add progress statistics
    if progress_data:
        stats_text += _format_progress_stats(progress_data)
    
    # Add available languages
    if available_languages:
        stats_text += _format_available_languages(available_languages)
        stats_text += "\n"
    
    # Add command menu
    stats_text += (
        "📋 <b>Доступные команды:</b>\n"
        "/language - Выбор языка для изучения\n"
        "/study - Начать изучение слов\n"
        "/settings - Настройки обучения\n"
        "/help - Справка\n"
        "/start - Главное меню"
    )

    # Create interactive keyboard
    keyboard = create_stats_keyboard()
    
    # Send statistics
    await message.answer(stats_text, reply_markup=keyboard, parse_mode="HTML")

# НОВОЕ: Обработчики callback'ов для интерактивности
@stats_router.callback_query(F.data == "refresh_stats")
async def process_refresh_stats(callback: CallbackQuery, state: FSMContext):
    """
    Handle statistics refresh request.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"Stats refresh by {callback.from_user.full_name}")
    
    await callback.answer("🔄 Обновление статистики...")
    
    # Re-run the stats command logic
    await cmd_stats(callback.message, state)

@stats_router.callback_query(F.data == "start_study_from_stats")
async def process_start_study_from_stats(callback: CallbackQuery, state: FSMContext):
    """
    Handle study start from stats.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"Start study from stats by {callback.from_user.full_name}")
    
    # Check if language is selected
    state_data = await state.get_data()
    current_language = state_data.get("current_language")
    
    if not current_language or not current_language.get("id"):
        await callback.answer("Сначала выберите язык!", show_alert=True)
        await callback.message.answer(
            "⚠️ Для начала изучения сначала выберите язык командой /language"
        )
        return
    
    await callback.answer("🎓 Переход к изучению...")
    await callback.message.answer(
        "🎓 Используйте команду /study для начала изучения слов."
    )

@stats_router.callback_query(F.data == "settings_from_stats")
async def process_settings_from_stats(callback: CallbackQuery, state: FSMContext):
    """
    Handle settings access from stats.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"Settings from stats by {callback.from_user.full_name}")
    
    # Check if language is selected
    state_data = await state.get_data()
    current_language = state_data.get("current_language")
    
    if not current_language or not current_language.get("id"):
        await callback.answer("Сначала выберите язык!", show_alert=True)
        await callback.message.answer(
            "⚠️ Для доступа к настройкам сначала выберите язык командой /language"
        )
        return
    
    await callback.answer("⚙️ Настройки...")
    await callback.message.answer(
        "⚙️ Используйте команду /settings для просмотра и изменения настроек обучения."
    )

# НОВОЕ: Utility functions for other modules
def format_progress_percentage(words_studied: int, total_words: int) -> float:
    """
    Calculate progress percentage.
    НОВОЕ: Утилита для расчета процента прогресса.
    
    Args:
        words_studied: Number of words studied
        total_words: Total number of words
        
    Returns:
        float: Progress percentage
    """
    if total_words == 0:
        return 0.0
    return (words_studied / total_words) * 100

def get_study_streak_info(last_study_date: str) -> dict:
    """
    Get information about study streak.
    НОВОЕ: Информация о серии изучения.
    
    Args:
        last_study_date: Last study date string
        
    Returns:
        dict: Streak information
    """
    try:
        if not last_study_date:
            return {"streak": 0, "status": "never_studied"}
        
        if 'T' in last_study_date:
            date_part = last_study_date.split('T')[0]
        else:
            date_part = last_study_date
            
        last_date = datetime.strptime(date_part, '%Y-%m-%d').date()
        today = datetime.now().date()
        days_diff = (today - last_date).days
        
        if days_diff == 0:
            return {"streak": 1, "status": "active_today"}
        elif days_diff == 1:
            return {"streak": 1, "status": "yesterday"}
        elif days_diff < 7:
            return {"streak": 0, "status": "recent", "days_ago": days_diff}
        else:
            return {"streak": 0, "status": "inactive", "days_ago": days_diff}
            
    except Exception as e:
        logger.warning(f"Error calculating streak for {last_study_date}: {e}")
        return {"streak": 0, "status": "unknown"}

# Export router and utilities
__all__ = [
    'stats_router',
    'format_progress_percentage',
    'get_study_streak_info'
]
