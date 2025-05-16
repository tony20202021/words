"""
Utility functions for formatting.
"""

from datetime import datetime
import locale
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

def format_date(date_str):
    """
    Форматирует дату из ISO формата в читаемый формат на русском языке.
    
    Args:
        date_str: Строка с датой в формате ISO или 'N/A'
    
    Returns:
        str: Отформатированная дата
    """
    if not date_str or date_str == 'N/A':
        return 'N/A'
    
    try:
        # Устанавливаем русскую локаль для форматирования даты
        try:
            locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
        except locale.Error:
            # Если русская локаль недоступна, используем системную
            locale.setlocale(locale.LC_TIME, '')
        
        # Если дата передана в виде строки, парсим ее
        if isinstance(date_str, str):
            # Пытаемся распарсить ISO дату
            if 'T' in date_str:
                date_part = date_str.split('T')[0]
            else:
                date_part = date_str
                
            date_obj = datetime.strptime(date_part, '%Y-%m-%d')
        else:
            # Если передан объект datetime, используем его напрямую
            date_obj = date_str
        
        # Форматируем дату в виде "день месяц год"
        # %d - день месяца, %B - полное название месяца, %Y - год в 4-х значном формате
        formatted_date = date_obj.strftime('%d %B %Y')
        
        return formatted_date
    except Exception as e:
        logger.error(f"Error formatting date: {e}")
        return str(date_str)

# Сохраняем совместимость со старым кодом
format_date_standard = format_date

def format_settings_text(start_word, skip_marked, use_check_date, show_hints, prefix="", suffix=""):
    """
    Форматирует текст настроек обучения.
    
    Args:
        start_word: Номер слова для начала обучения
        skip_marked: Пропускать ли помеченные слова
        use_check_date: Учитывать ли дату проверки
        show_hints: Показывать ли кнопки подсказок
        prefix: Текст перед настройками
        suffix: Текст после настроек
        
    Returns:
        str: Отформатированный текст настроек
    """
    settings_text = f"{prefix}"
    
    # Форматируем настройки
    settings_text += f"🔢 Начальное слово: <b>{start_word}</b>\n"
    
    # Статус пропуска помеченных слов
    skip_status = "Пропускать ❌" if skip_marked else "Показывать ✅"
    settings_text += f"⏩ Слова, помеченные как пропущенные: <b>{skip_status}</b>\n"
    
    # Статус учета даты проверки
    date_status = "Учитывать ✅ (показывать слово только после даты проверки)" if use_check_date else "Не учитывать ❌ (показывать слова каждый день)"
    settings_text += f"📅 Период повторения: <b>{date_status}</b>\n"
    
    # Статус отображения кнопок подсказок
    hints_status = "Придумывать ✅" if show_hints else "Пропускать ❌"
    settings_text += f"💡 Подсказки: <b>{hints_status}</b>"
    
    # Добавляем суффикс
    if suffix:
        settings_text += suffix
    
    return settings_text

def format_study_word_message(
    language_name_ru, 
    language_name_foreign, 
    word_number, 
    translation, 
    is_skipped, 
    score,
    check_interval, 
    next_check_date,
    show_word=False,
    word_foreign=None,
    transcription=None
):
    """
    Форматирует сообщение для отображения слова в процессе изучения.
    
    Args:
        language_name_ru: Название языка на русском
        language_name_foreign: Название языка на иностранном
        word_number: Номер слова
        translation: Перевод слова
        is_skipped: Флаг пропуска слова
        check_interval: Интервал проверки
        next_check_date: Дата следующей проверки
        show_word: Показывать ли само слово и транскрипцию
        word_foreign: Слово на иностранном языке
        transcription: Транскрипция слова
        
    Returns:
        str: Отформатированное сообщение
    """
    message = (
        f"📝 Переведите на \"{language_name_ru} ({language_name_foreign})\":\n\n"
        f"слово номер: {word_number}\n\n" 
    )
    
    message += f"🔍 Перевод:\n <b>{translation}</b>\n\n"
    
    # Добавляем информацию о статусе пропуска - исправлено условие
    if is_skipped:
        message += "⏩ <b>Статус: это слово помечено для пропуска.</b>\n\n"
    
    # Добавляем информацию о периоде повторения
    if (score == 1):
        message += f"⏱ Вы знали это слово:\n"
        if check_interval and check_interval > 0:
            message += f"⏱ Предыдущий интервал: {check_interval} (дней)\n"
        if next_check_date:
            formatted_date = format_date(next_check_date)
            message += f"🔄 Запланированное повторение: {formatted_date} \n\n" 
    else:
        message += f"score: {score}.\n"
        message += f"check_interval: {check_interval}.\n"
        message += f"next_check_date: {next_check_date} \n\n" 
    
    # Если нужно показать слово, добавляем его
    if show_word and word_foreign:
        message += f"📝 Слово: <code>{word_foreign}</code>\n"
        if transcription:
            message += f"🔊 Транскрипция: <b>[{transcription}]</b>\n\n"
        else:
            message += "\n"

    return message

from typing import List, Dict, Any, Optional
from aiogram.client.bot import Bot

from app.utils.hint_constants import HINT_ORDER, get_hint_key, get_hint_name, get_hint_icon
from app.utils.word_data_utils import get_hint_text

async def format_active_hints(
    bot: Bot,
    user_id: str,
    word_id: str,
    current_word: Dict[str, Any],
    active_hints: List[str],
    include_header: bool = True
) -> str:
    """
    Форматирует текст для активных подсказок в соответствии с порядком HINT_ORDER.
    
    Args:
        bot: Экземпляр бота Telegram для работы с API
        user_id: ID пользователя
        word_id: ID слова
        current_word: Данные текущего слова
        active_hints: Список активных подсказок
        include_header: Добавлять ли заголовок "Активные подсказки"
        
    Returns:
        str: Отформатированный текст с активными подсказками
    """
    if not active_hints:
        return ""
    
    result = "\n\n<b>Активные подсказки:</b>\n" if include_header else ""
    
    # Сортируем активные подсказки в соответствии с порядком HINT_ORDER
    sorted_active_hints = [hint_type for hint_type in HINT_ORDER if hint_type in active_hints]
    
    # Добавляем оставшиеся активные подсказки, если они не включены в HINT_ORDER
    for hint_type in active_hints:
        if hint_type not in sorted_active_hints:
            sorted_active_hints.append(hint_type)
    
    # Теперь перебираем отсортированный список активных подсказок
    for active_hint_type in sorted_active_hints:
        active_hint_key = get_hint_key(active_hint_type)
        active_hint_name = get_hint_name(active_hint_type)
        active_hint_icon = get_hint_icon(active_hint_type)
        
        active_hint_text = await get_hint_text(
            bot, 
            user_id, 
            word_id, 
            active_hint_key, 
            current_word
        )
        
        if active_hint_text:
            result += f"\n📌 <b>{active_hint_icon} {active_hint_name}:</b>\n{active_hint_text}\n"
    
    return result