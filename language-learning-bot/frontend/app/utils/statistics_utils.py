"""
statistics actions.
"""

from aiogram.types import CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from datetime import datetime
from typing import Dict, List

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.chart_generator import ProgressChartGenerator

logger = setup_logger(__name__)

async def load_progress(callback: CallbackQuery, state: FSMContext):
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(callback.bot)
    
    # Получение данных состояния
    state_data = await state.get_data()
    db_user_id = state_data.get("db_user_id", None)
    logger.info(f"db_user_id: {db_user_id}")
    
    current_language = state_data.get("current_language", {})
    language_id = current_language.get("id")
    logger.info(f"language_id: {language_id}")

    api_response = await api_client.get_user_progress(db_user_id, language_id)

    if not api_response['success'] and api_response['status'] == 404:
        # Если получаем 404, это значит, что прогресс еще не создан для этого пользователя и языка
        # Используем пустые значения прогресса
        progress = {
            "words_studied": 0,
            "words_known": 0,
            "words_skipped": 0,
            "total_words": 0,
            "words_for_today": 0,
            "progress_percentage": 0,
            "word_numbers_for_today": [],
            "word_numbers_unknown": []
        }
    else:
        progress = api_response['result']

    await state.update_data(
        progress=progress,
    )

    return progress

async def _send_today_charts(message_or_callback: CallbackQuery, progress: Dict):
    """
    Отправляет реальные графики прогресса в виде изображений.
    Создает настоящие PNG-графики с помощью matplotlib.
    """
    if isinstance(message_or_callback, CallbackQuery):
        message = message_or_callback.message
    else:
        message = message_or_callback

    try:
        generator = ProgressChartGenerator()
        
        # 2. Гистограмма слов для повторения и неизвестных слов
        word_numbers_for_today = progress.get("word_numbers_for_today", [])
        word_numbers_unknown = progress.get("word_numbers_unknown", [])
        words_studied = progress.get("words_studied", 0)
        
        if word_numbers_for_today:
            histogram_chart = generator.create_words_for_today_histogram(
                word_numbers_for_today, 
                words_studied,
                x_axis_limits="one_max",
            )
            histogram_file = BufferedInputFile(
                histogram_chart.getvalue(),
                filename="words_histogram.png"
            )
            
            await message.answer_photo(
                histogram_file,
                caption="Слова для повторения сегодня"
            )
                
        if word_numbers_unknown:
            histogram_chart = generator.create_unknown_words_histogram(
                word_numbers_unknown, 
                words_studied,
                x_axis_limits="one_max",
            )
            histogram_file = BufferedInputFile(
                histogram_chart.getvalue(),
                filename="words_histogram.png"
            )
            
            await message.answer_photo(
                histogram_file,
                caption="Неизвестные слова"
            )
                
        logger.info(f"Successfully sent progress charts to user {message_or_callback.from_user.username}")
        
    except Exception as e:
        logger.error(f"Error generating progress charts: {e}", exc_info=True)
        await message.answer(
            "❌ Ошибка при создании графиков. Используется текстовая статистика."
        )


async def show_today_statistics(message_or_callback: CallbackQuery, state: FSMContext):
    """
    Show daily statistics with real chart visualization.
    Использует реальные PNG-графики
    """
    logger.info(f"show_today_statistics from {message_or_callback.from_user.full_name}")

    if isinstance(message_or_callback, CallbackQuery):
        message = message_or_callback.message
    else:
        message = message_or_callback

    state_data = await state.get_data()
    progress = state_data.get("progress", {})

    # Основная статистика (текст)
    words_studied = progress.get('words_studied', 0)
    words_known = progress.get('words_known', 0)
    words_skipped = progress.get('words_skipped', 0)
    words_for_today = progress.get('words_for_today', 0)
    total_words = progress.get('total_words', 0)
    progress_percentage = progress.get('progress_percentage', 0.0)

    unknown_count = words_studied - words_known - words_skipped
    
    # Краткий текстовый отчет
    stats_message = (
        f"📊 **Дневная статистика**\n\n" +
        f"🎯 **Общий прогресс:** {progress_percentage:.1f}%\n" +
        f"📚 **Всего слов в языке:** {total_words}\n" +
        f"📖 **Изучено слов:** {words_studied}\n" +
        f"**Состояние изученных слов:**\n" +
        f"✅ **Выучено:** {words_known}\n" +
        f"❓ **Неизвестно:** {unknown_count}\n" +
        f"⏭️ **Пропущено:** {words_skipped}\n" +
        f"🔄 **К повторению сегодня:** {words_for_today}\n" +
        f"📈 **Детальные графики отправляются ниже...**"
    )

    await message.answer(stats_message, parse_mode="Markdown")
    
    # 🆕 Отправляем реальные графики
    await _send_today_charts(message_or_callback, progress)


async def update_daily_statistics(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Updating daily statistics for user {callback.from_user.full_name}")
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(callback.bot)
    
    # Получение данных состояния
    state_data = await state.get_data()
    db_user_id = state_data.get("db_user_id", None)
    logger.info(f"db_user_id: {db_user_id}")
    
    current_language = state_data.get("current_language", {})
    language_id = current_language.get("id")
    logger.info(f"language_id: {language_id}")

    last_action_date_time = state_data.get("last_action_date_time", None)
    if last_action_date_time is None:
        last_action_date_time = datetime.now().isoformat()
    last_action_date = datetime.fromisoformat(last_action_date_time).date()
    logger.info(f"last_action_date: {last_action_date}")

    progress = state_data.get("progress", {})
    logger.info(f"progress: {progress}")

    api_response = await api_client.get_daily_statistics(db_user_id, language_id, last_action_date)

    if (not api_response['success']) or (api_response['status'] == 404) or (api_response['result'] == None):
        logger.info(f"No progress data found for user {db_user_id} and language {language_id} for date {last_action_date}. Creating new daily statistics.")
        
        api_response = await api_client.update_daily_statistics(db_user_id, language_id, last_action_date, progress)
        if not api_response['success']:
            logger.error(f"Error updating daily statistics for user {db_user_id} and language {language_id}: {api_response['error']}")
            return


async def update_daily_first_finish_statistics(callback: CallbackQuery, state: FSMContext):
    logger.info(f"update_daily_first_finish_statistics from {callback.from_user.full_name}")

    api_client = get_api_client_from_bot(callback.bot)

    state_data = await state.get_data()
    db_user_id = state_data.get("db_user_id", None)
    logger.info(f"db_user_id: {db_user_id}")

    current_language = state_data.get("current_language", {})
    language_id = current_language.get("id")
    logger.info(f"language_id: {language_id}")

    last_action_date_time = state_data.get("last_action_date_time", None)
    if last_action_date_time is None:
        last_action_date_time = datetime.now().isoformat()
    last_action_date = datetime.fromisoformat(last_action_date_time).date()
    logger.info(f"last_action_date: {last_action_date}")

    progress = state_data.get("progress", {})
    logger.info(f"progress: {progress}")

    api_response = await api_client.get_daily_first_finish_statistics(db_user_id, language_id, last_action_date)

    if (not api_response['success']) or (api_response['status'] == 404) or (api_response['result'] == None):
        logger.info(f"No first finish statistics found for user {db_user_id} and language {language_id} for date {last_action_date}. Creating new first finish statistics.")
        
        api_response = await api_client.update_daily_first_finish_statistics(db_user_id, language_id, last_action_date, progress)
        if not api_response['success']:
            logger.error(f"Error updating daily first finish statistics for user {db_user_id} and language {language_id}: {api_response['error']}")
            return


async def _send_monthly_charts(message_or_callback: CallbackQuery, all_days_stats: List[Dict], first_finish_stats: List[Dict], show_all: bool):
    logger.info(f"Sending monthly charts for user {message_or_callback.from_user.full_name}")
    # logger.info(f"all_days_stats: {all_days_stats}")
    # logger.info(f"first_finish_stats: {first_finish_stats}")
    logger.info(f"show_all: {show_all}")

    if isinstance(message_or_callback, CallbackQuery):
        message = message_or_callback.message
    else:
        message = message_or_callback

    try:
        generator = ProgressChartGenerator()
        
        if not all_days_stats:
            await message.answer(
                "Нет статистики по датам"
            )
            logger.info(f"monthly_statistics is empty")
            return
        else:
            histogram_chart = generator.create_counts_plot(
                all_days_stats, 
                "words_studied",
                title="Всего изучено",
                title_value="last",
                y_axis_limits="zero_max" if show_all else "min_max",
            )
            histogram_file = BufferedInputFile(
                histogram_chart.getvalue(),
                filename="words_histogram.png"
            )
            
            await message.answer_photo(
                histogram_file,
                caption="Всего изучено"
            )
                
            histogram_chart = generator.create_counts_plot(
                all_days_stats, 
                "words_new",
                title="Новые слова",
                title_value="max",
                y_axis_limits="zero_max" if show_all else "min_max",
            )
            histogram_file = BufferedInputFile(
                histogram_chart.getvalue(),
                filename="words_histogram.png"
            )
            
            await message.answer_photo(
                histogram_file,
                caption="Новые слова"
            )
                
            histogram_chart = generator.create_counts_plot(
                all_days_stats,
                "words_known",
                title="Известные слова",
                title_value="last",
                y_axis_limits="zero_max" if show_all else "min_max",
            )
            histogram_file = BufferedInputFile(
                histogram_chart.getvalue(),
                filename="words_histogram.png"
            )
            
            await message.answer_photo(
                histogram_file,
                caption="Известные слова"
            )
                
            histogram_chart = generator.create_counts_plot(
                all_days_stats,
                "words_unknown",
                title="Неизвестные слова \n (до первого завершения)",
                title_value="max",
                y_axis_limits="zero_max" if show_all else "min_max",
            )
            histogram_file = BufferedInputFile(
                histogram_chart.getvalue(),
                filename="words_histogram.png"
            )
            
            await message.answer_photo(
                histogram_file,
                caption="Неизвестные слова \n (до первого завершения)"
            )
                
            histogram_chart = generator.create_counts_plot(
                first_finish_stats,
                "words_unknown",
                title="Неизвестные слова \n (после первого завершения)",
                title_value="max",
                y_axis_limits="zero_max" if show_all else "min_max",
            )
            histogram_file = BufferedInputFile(
                histogram_chart.getvalue(),
                filename="words_histogram.png"
            )
            
            await message.answer_photo(
                histogram_file,
                caption="Неизвестные слова \n (после первого завершения)"
            )
                
            histogram_chart = generator.create_counts_plot(
                all_days_stats, 
                "words_for_today",
                title="Слова для ежедневного повторения",
                title_value="max",
                y_axis_limits="zero_max" if show_all else "min_max",
            )
            histogram_file = BufferedInputFile(
                histogram_chart.getvalue(),
                filename="words_histogram.png"
            )
            
            await message.answer_photo(
                histogram_file,
                caption="Слова для ежедневного повторения"
            )
                
        logger.info(f"Successfully sent progress charts to user {message_or_callback.from_user.username}")
        
    except Exception as e:
        logger.error(f"Error generating progress charts: {e}", exc_info=True)
        await message.answer(
            "❌ Ошибка при создании графиков. Используется текстовая статистика."
        )

async def show_full_statistics(callback: CallbackQuery, state: FSMContext):
    await show_monthly_statistics(callback, state, show_all=True)


async def show_monthly_statistics(message_or_callback: CallbackQuery, state: FSMContext, show_all: bool = False):
    logger.info(f"show_monthly_statistics from {message_or_callback.from_user.full_name}")
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(message_or_callback.bot)
    
    # Получение данных состояния
    state_data = await state.get_data()
    db_user_id = state_data.get("db_user_id", None)
    logger.info(f"db_user_id: {db_user_id}")
    
    current_language = state_data.get("current_language", {})
    language_id = current_language.get("id")
    logger.info(f"language_id: {language_id}")

    last_action_date_time = state_data.get("last_action_date_time", None)
    if last_action_date_time is None:
        last_action_date_time = datetime.now().isoformat()
    last_action_date = datetime.fromisoformat(last_action_date_time).date()
    logger.info(f"last_action_date: {last_action_date} for monthly statistics")

    if show_all:
        api_response = await api_client.get_all_monthly_statistics(db_user_id, language_id, last_action_date)
    else:
        api_response = await api_client.get_monthly_statistics(db_user_id, language_id, last_action_date)

    if (not api_response['success']) or (api_response['status'] == 404) or (api_response['result'] == None):
        logger.error(f"No progress data found for user {db_user_id} and language {language_id} for date {last_action_date}.")
        return

    monthly_statistics = api_response['result']
    logger.info(f"monthly_statistics: {monthly_statistics}")

    all_days_stats = []
    words_studied_previous = None
    for one_day_stats in monthly_statistics["daily_stats"]:
        one_day_stats["words_unknown"] = one_day_stats["words_studied"] - one_day_stats["words_known"] - one_day_stats["words_skipped"]
        
        if words_studied_previous is None:
            one_day_stats["words_new"] = None
        else:
            delta = one_day_stats["words_studied"] - words_studied_previous
            if delta >= 0:
                one_day_stats["words_new"] = delta
            else:
                one_day_stats["words_new"] = None

        words_studied_previous = one_day_stats["words_studied"]
        
        all_days_stats.append(one_day_stats)

    if show_all:
        api_response = await api_client.get_all_monthly_first_finish_statistics(db_user_id, language_id, last_action_date)
    else:
        api_response = await api_client.get_monthly_first_finish_statistics(db_user_id, language_id, last_action_date)

    if (not api_response['success']) or (api_response['status'] == 404) or (api_response['result'] == None):
        logger.error(f"No first finish statistics found for user {db_user_id} and language {language_id} for date {last_action_date}.")
        return

    first_finish_statistics = api_response['result']
    logger.info(f"first_finish_statistics: {first_finish_statistics}")

    first_finish_stats = []
    for one_day_stats in first_finish_statistics["daily_stats"]:
        one_day_stats["words_unknown"] = one_day_stats["words_studied"] - one_day_stats["words_known"] - one_day_stats["words_skipped"]
        first_finish_stats.append(one_day_stats)

    await _send_monthly_charts(message_or_callback, all_days_stats, first_finish_stats, show_all)

