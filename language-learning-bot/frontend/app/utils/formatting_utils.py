"""
Utility functions for formatting.
UPDATED: Added support for writing images settings in formatting.
UPDATED: Removed hieroglyphic language restrictions - writing images are controlled by user settings only.
"""

from datetime import datetime
import locale
from typing import Dict, Any, List, Optional

from app.utils.logger import setup_logger
from app.utils.hint_constants import (
    HINT_SETTING_KEYS, 
    get_hint_setting_name
)

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

def format_settings_text(
    start_word, 
    skip_marked, 
    use_check_date, 
    show_check_date,
    show_debug, 
    show_charts,
    hint_settings,
    show_writing_images=False,
    show_short_captions=True,
    show_big=False,
    receive_messages=True,
    reset_session_days=1,
    reset_session_hours=6,
    unknown_limit_new_words=10,
    prefix="", 
    suffix=""
):
    """
    Форматирует текст настроек обучения.
    
    Args:
        start_word: Номер слова для начала обучения
        skip_marked: Пропускать ли помеченные слова
        use_check_date: Учитывать ли дату проверки
        show_date: Показывать ли дату проверки
        show_debug: Показывать ли отладочную информацию
        show_charts: Показывать ли графики
        hint_settings: Словарь с индивидуальными настройками подсказок
        show_writing_images: Показывать ли картинки написания
        show_short_captions: Показывать ли короткие подписи
        show_big: Показывать ли крупное написание
        receive_messages: Получать ли сообщения
        prefix: Текст перед настройками
        suffix: Текст после настроек
        
    Returns:
        str: Отформатированный текст настроек
    """
    settings_text = f"{prefix}"
    
    short_captions_status = "Показывать ✅" if show_short_captions else "Скрывать ❌"
    settings_text += f"   • Короткие подписи: <b>{short_captions_status}</b>\n"
    
    settings_text += f"   • Начальное слово: <b>{start_word}</b>\n"
    
    skip_status = "Пропускать ❌" if skip_marked else "Показывать ✅"
    settings_text += f"   • Исключенные слова: <b>{skip_status}</b>\n"
    
    settings_text += f"🖼️ <b>Настройки даты проверки:</b>\n"
    
    date_status = "Учитывать ✅" if use_check_date else "Не учитывать ❌"
    settings_text += f"   • Период повторения: <b>{date_status}</b>\n"
    
    date_status = "показывать ✅" if show_check_date else "скрывать ❌"
    settings_text += f"   • Дата проверки: <b>{date_status}</b>\n"
    
    # Отображение настроек подсказок
    settings_text += f"💡 <b>Настройки подсказок:</b>\n"
    
    for setting_key in HINT_SETTING_KEYS:
        setting_name = get_hint_setting_name(setting_key)
        setting_value = hint_settings.get(setting_key, True)
        status = "Включено ✅" if setting_value else "Отключено ❌"
        settings_text += f"   • {setting_name}: <b>{status}</b>\n"
    
    settings_text += f"🖼️ <b>Настройки написания:</b>\n"
    
    big_word_status = "Показывать ✅" if show_big else "Скрывать ❌"
    settings_text += f"   • Крупное написание: <b>{big_word_status}</b>\n"

    show_writing_images = "Показывать ✅" if show_writing_images else "Скрывать ❌"
    settings_text += f"   • Картинки написания: <b>{show_writing_images}</b>\n"
    
    # Статус отображения отладочной информации
    debug_status = "Показывать ✅" if show_debug else "Скрывать ❌"
    settings_text += f"🔍 Отладочные данные: <b>{debug_status}</b>\n"
    
    # Статус отображения графиков
    charts_status = "Показывать ✅" if show_charts else "Скрывать ❌"
    settings_text += f"📊 Графики: <b>{charts_status}</b>\n"
    
    # Статус получения сообщений
    receive_messages_status = "Получать ✅" if receive_messages else "Не получать ❌"
    settings_text += f"📤 Получать сообщения: <b>{receive_messages_status}</b>\n"
    
    # Статус сброса сессии
    settings_text += f"🔄 <b>Сброс сессии:</b>\n"
    settings_text += f"   • дни: <b>{reset_session_days}</b>\n"
    settings_text += f"   • часы: <b>{reset_session_hours}</b>\n"

    # Статус лимита новых слов
    settings_text += f"🔄 Лимит неизвестных слов: <b>{unknown_limit_new_words}</b>\n"

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
    score_changed=False,
    show_word=False,
    word_foreign=None,
    transcription=None,
    radicals=None,
    references=None,
    tones=None,
    show_big=False,
    show_check_date=True,
    words_studied=0,
    words_for_today=0,
    session_processed=0,
):
    """
    Форматирует сообщение для отображения слова в процессе изучения.
    
    Args:
        language_name_ru: Название языка на русском
        language_name_foreign: Название языка на иностранном
        word_number: Номер слова
        translation: Перевод слова
        is_skipped: Флаг пропуска слова
        score: Оценка слова
        check_interval: Интервал проверки
        next_check_date: Дата следующей проверки
        score_changed: Была ли изменена оценка
        show_word: Показывать ли само слово и транскрипцию
        word_foreign: Слово на иностранном языке
        transcription: Транскрипция слова
        radicals: Радикалы слова
        references: Ссылки на слово
        tones: Тоны слова
        show_big: Показывать ли большое слово
        show_check_date: Показывать ли дату проверки
        words_studied: Количество слов, изученных в сессии
        words_for_today: Количество слов на текущую сессию
        session_processed: Количество слов, обработанных в сессии
    Returns:
        str: Отформатированное сообщение
    """
    message = f"📝 Язык: \"{language_name_ru} ({language_name_foreign})\":\n\n"
    message += f"Слово номер: <b>{word_number}</b>\n" 
    
    if word_number == words_studied:
        message += f"(завершающее из изученых: {words_studied})\n"
    elif word_number > words_studied:
        message += f"(новое слово, изучается первый раз)\n"

    if word_number <= words_studied:
        if show_word:
            message += f"(закончено в текущей сессии: <b>{session_processed}</b> из <b>{words_for_today}</b>)\n"
        else:
            message += f"(изучается в текущей сессии: <b>{session_processed + 1}</b> из <b>{words_for_today}</b>)\n"
    

    # Добавляем информацию о статусе пропуска
    if is_skipped:
        message += "\n"
        message += "⏩ <b>Статус: это слово помечено для пропуска.</b>\n"
    
    # Добавляем информацию о периоде повторения
    if (score == 1) and show_check_date:
        if score_changed:
            if check_interval and check_interval > 0:
                message += "\n"
                message += f"Следующий интервал: {check_interval} (дней)\n"
        else:
            if (check_interval > 0) or (next_check_date):
                message += "\n"
                message += f"⏱ Вы знали это слово:\n"
            if check_interval and check_interval > 0:
                message += f"Предыдущий интервал: {check_interval} (дней)\n"
    
    message += "\n"    
    message += f"🔍 Слово на русском:\n<b>{translation}</b>\n"
    
    # Если нужно показать слово, добавляем его с кликабельной ссылкой
    if show_word and word_foreign:
        # Создаем кликабельную ссылку на команду /show_big
        if show_big:
            message += f"\n📝 Слово на иностранном:\n<b>{word_foreign}</b>(/show_big) 🔍\n\n"
        else:
            message += f"\n📝 Слово на иностранном:\n<b>{word_foreign}</b>\n\n"
        if transcription:
            escaped_transcription = transcription.replace('\n', ',')
            message += f"🔊 Транскрипция:\n<b>[{escaped_transcription}]</b>\n\n"
        if radicals:
            message += f"🔍 Радикалы:\n{radicals}\n\n"
        if references:
            message += f"🔍 Ссылки:\n{references}\n\n"
        if tones:
            message += f"🔍 Тоны:\n{tones}\n\n"
            
    return message


def format_date_friendly(date_str: str) -> str:
    """
    Format date in a user-friendly way.
    Дружественное форматирование даты.
    
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
    