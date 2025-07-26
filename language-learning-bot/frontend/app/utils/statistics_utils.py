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

async def _update_progress(callback: CallbackQuery, state: FSMContext):
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


async def _send_today_charts(callback: CallbackQuery, progress: Dict):
    """
    Отправляет реальные графики прогресса в виде изображений.
    Создает настоящие PNG-графики с помощью matplotlib.
    """
    try:
        generator = ProgressChartGenerator()
        
        # 2. Гистограмма слов для повторения и неизвестных слов
        word_numbers_for_today = progress.get("word_numbers_for_today", [])
        word_numbers_unknown = progress.get("word_numbers_unknown", [])
        words_studied = progress.get("words_studied", 0)
        
        if word_numbers_for_today:
            histogram_chart = generator.create_words_for_today_histogram(
                word_numbers_for_today, 
                words_studied
            )
            histogram_file = BufferedInputFile(
                histogram_chart.getvalue(),
                filename="words_histogram.png"
            )
            
            await callback.message.answer_photo(
                histogram_file,
                caption="📈 **Анализ слов по номерам**"
            )
                
        if word_numbers_unknown:
            histogram_chart = generator.create_unknown_words_histogram(
                word_numbers_unknown, 
                words_studied
            )
            histogram_file = BufferedInputFile(
                histogram_chart.getvalue(),
                filename="words_histogram.png"
            )
            
            await callback.message.answer_photo(
                histogram_file,
                caption="📈 **Анализ слов по номерам**"
            )
                
        logger.info(f"Successfully sent progress charts to user {callback.from_user.username}")
        
    except Exception as e:
        logger.error(f"Error generating progress charts: {e}", exc_info=True)
        await callback.message.answer(
            "❌ Ошибка при создании графиков. Используется текстовая статистика."
        )


async def show_today_statistics(callback: CallbackQuery, state: FSMContext):
    """
    Show daily statistics with real chart visualization.
    Использует реальные PNG-графики
    """
    logger.info(f"show_today_statistics from {callback.from_user.full_name}")

    state_data = await state.get_data()
    progress = state_data.get("progress", {})

    word_numbers_for_today = progress.get("word_numbers_for_today", [])
    word_numbers_unknown = progress.get("word_numbers_unknown", [])
    
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

    await callback.message.answer(stats_message, parse_mode="Markdown")
    
    # 🆕 Отправляем реальные графики
    await _send_today_charts(callback, progress)


async def _update_daily_statistics(callback: CallbackQuery, state: FSMContext):
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


async def _send_monthly_charts(callback: CallbackQuery, daily_stats: List[Dict]):
    logger.info(f"Sending monthly charts for user {callback.from_user.full_name}")
    logger.info(f"daily_stats: {daily_stats}")

    try:
        generator = ProgressChartGenerator()
        
        if not daily_stats:
            await callback.message.answer(
                "Нет статистики по датам"
            )
            logger.info(f"monthly_statistics is empty")
            return
        else:
            histogram_chart = generator.create_counts_plot(
                daily_stats, 
                "words_studied",
                title="Всего изучено"
            )
            histogram_file = BufferedInputFile(
                histogram_chart.getvalue(),
                filename="words_histogram.png"
            )
            
            await callback.message.answer_photo(
                histogram_file,
                caption="Всего изучено"
            )
                
            histogram_chart = generator.create_counts_plot(
                daily_stats,
                "words_known",
                title="Известные слова"
            )
            histogram_file = BufferedInputFile(
                histogram_chart.getvalue(),
                filename="words_histogram.png"
            )
            
            await callback.message.answer_photo(
                histogram_file,
                caption="Известные слова"
            )
                
            histogram_chart = generator.create_counts_plot(
                daily_stats,
                "words_unknown",
                title="Неизвестные слова"
            )
            histogram_file = BufferedInputFile(
                histogram_chart.getvalue(),
                filename="words_histogram.png"
            )
            
            await callback.message.answer_photo(
                histogram_file,
                caption="Неизвестные слова"
            )
                
            histogram_chart = generator.create_counts_plot(
                daily_stats, 
                "words_for_today",
                title="Слова для ежедневного повторения"
            )
            histogram_file = BufferedInputFile(
                histogram_chart.getvalue(),
                filename="words_histogram.png"
            )
            
            await callback.message.answer_photo(
                histogram_file,
                caption="Слова для ежедневного повторения"
            )
                
        logger.info(f"Successfully sent progress charts to user {callback.from_user.username}")
        
    except Exception as e:
        logger.error(f"Error generating progress charts: {e}", exc_info=True)
        await callback.message.answer(
            "❌ Ошибка при создании графиков. Используется текстовая статистика."
        )


async def show_monthly_statistics(callback: CallbackQuery, state: FSMContext):
    logger.info(f"show_monthly_statistics from {callback.from_user.full_name}")
    
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
    last_action_date = datetime.fromisoformat(last_action_date_time).date()
    logger.info(f"last_action_date: {last_action_date} for monthly statistics")

    api_response = await api_client.get_monthly_statistics(db_user_id, language_id, last_action_date)

    if (not api_response['success']) or (api_response['status'] == 404) or (api_response['result'] == None):
        logger.error(f"No progress data found for user {db_user_id} and language {language_id} for date {last_action_date}. Creating new daily statistics.")
        return
    
    monthly_statistics = api_response['result']
    logger.info(f"monthly_statistics: {monthly_statistics}")

    daily_stats = []
    for s in monthly_statistics["daily_stats"]:
        s["words_unknown"] = s["words_studied"] - s["words_known"] - s["words_skipped"]
        daily_stats.append(s)

    await _send_monthly_charts(callback, daily_stats)

