"""
Utility functions for formatting.
UPDATED: Support for individual hint settings display.
"""

from datetime import datetime
import locale
from typing import Dict, Any, List, Optional

from app.utils.logger import setup_logger
from app.utils.hint_constants import HINT_SETTING_KEYS, get_hint_setting_name

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
    show_debug, 
    hint_settings,
    prefix="", 
    suffix=""
):
    """
    Форматирует текст настроек обучения.
    
    Args:
        start_word: Номер слова для начала обучения
        skip_marked: Пропускать ли помеченные слова
        use_check_date: Учитывать ли дату проверки
        show_debug: Показывать ли отладочную информацию
        hint_settings: Словарь с индивидуальными настройками подсказок (НОВОЕ)
        prefix: Текст перед настройками
        suffix: Текст после настроек
        
    Returns:
        str: Отформатированный текст настроек
    """
    settings_text = f"{prefix}"
    
    # Форматируем настройки
    settings_text += f"Начальное слово: <b>{start_word}</b>\n"
    
    # Статус пропуска помеченных слов
    skip_status = "Пропускать ❌" if skip_marked else "Показывать ✅"
    settings_text += f"Исключенные слова: <b>{skip_status}</b>\n"
    
    # Статус учета даты проверки
    date_status = "Учитывать ✅ (показывать слово только после даты проверки)" if use_check_date else "Не учитывать ❌ (показывать слова каждый день)"
    settings_text += f"Период повторения: <b>{date_status}</b>\n"
    
    # Отображение настроек подсказок
    settings_text += f"💡 <b>Настройки подсказок:</b>\n"
    
    for setting_key in HINT_SETTING_KEYS:
        setting_name = get_hint_setting_name(setting_key)
        setting_value = hint_settings.get(setting_key, True)
        status = "Включено ✅" if setting_value else "Отключено ❌"
        settings_text += f"   • {setting_name}: <b>{status}</b>\n"
    
    # Статус отображения отладочной информации
    debug_status = "Показывать ✅" if show_debug else "Скрывать ❌"
    settings_text += f"🔍 Отладочные данные: <b>{debug_status}</b>"
    
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
        f"📝 Язык: \"{language_name_ru} ({language_name_foreign})\":\n\n"
        f"Слово номер: <b>{word_number}</b>\n\n" 
    )
    
    # Добавляем информацию о статусе пропуска - исправлено условие
    if is_skipped:
        message += "⏩ <b>Статус: это слово помечено для пропуска.</b>\n\n"
    
    # Добавляем информацию о периоде повторения
    if (score == 1):
        if score_changed:
            if check_interval and check_interval > 0:
                message += f"Следующий интервал: {check_interval} (дней)\n"
            if next_check_date:
                formatted_date = format_date(next_check_date)
                message += f"Следующее повторение: {formatted_date} \n\n" 
        else:
            if (check_interval > 0) or (next_check_date):
                message += f"⏱ Вы знали это слово:\n"
            if check_interval and check_interval > 0:
                message += f"Предыдущий интервал: {check_interval} (дней)\n"
            if next_check_date:
                formatted_date = format_date(next_check_date)
                message += f"Запланированное повторение: {formatted_date} \n\n" 
    
    message += f"🔍 Перевод:\n<b>{translation}</b>\n"
    
    # Если нужно показать слово, добавляем его
    if show_word and word_foreign:
        message += f"\n📝 Слово: <code>{word_foreign}</code>\n"
        if transcription:
            message += f"🔊 Транскрипция: <b>[{transcription}]</b>\n"

    return message

from typing import List, Dict, Any, Optional
from aiogram.client.bot import Bot

from app.utils.hint_constants import HINT_ORDER, get_hint_key, get_hint_short
from app.utils.word_data_utils import get_hint_text

async def format_used_hints(
    bot: Bot,
    user_id: str,
    word_id: str,
    current_word: Dict[str, Any],
    used_hints: List[str],
    include_header: bool = True
) -> str:
    """
    Форматирует текст для активных подсказок в соответствии с порядком HINT_ORDER.
    
    Args:
        bot: Экземпляр бота Telegram для работы с API
        user_id: ID пользователя
        word_id: ID слова
        current_word: Данные текущего слова
        used_hints: Список подсказок
        include_header: Добавлять ли заголовок "Активные подсказки"
        
    Returns:
        str: Отформатированный текст с активными подсказками
    """
    if not used_hints:
        return ""
    
    result = "\n📌 Подсказки:\n" if include_header else ""
    
    # Сортируем активные подсказки в соответствии с порядком HINT_ORDER
    sorted_hints = [hint_type for hint_type in HINT_ORDER if hint_type in used_hints]
    
    # Добавляем оставшиеся активные подсказки, если они не включены в HINT_ORDER
    for hint_type in used_hints:
        if hint_type not in sorted_hints:
            sorted_hints.append(hint_type)
    
    # Теперь перебираем отсортированный список активных подсказок
    for active_hint_type in sorted_hints:
        active_hint_key = get_hint_key(active_hint_type)
        active_hint_short = get_hint_short(active_hint_type)        
        
        active_hint_text = await get_hint_text(
            bot, 
            user_id, 
            word_id, 
            active_hint_key, 
            current_word
        )
        
        if active_hint_text:
            result += f"<b>{active_hint_short}:</b>\t{active_hint_text}\n"
    
    return result


# НОВОЕ: Функции для форматирования настроек подсказок
def format_hint_settings_summary(hint_settings: Dict[str, bool]) -> str:
    """
    Форматирует краткую сводку настроек подсказок.
    
    Args:
        hint_settings: Словарь с настройками подсказок
        
    Returns:
        str: Краткая сводка настроек
    """
    enabled_count = sum(1 for enabled in hint_settings.values() if enabled)
    total_count = len(hint_settings)
    
    if enabled_count == total_count:
        return "Все включены ✅"
    elif enabled_count == 0:
        return "Все отключены ❌"
    else:
        return f"{enabled_count} из {total_count} включено 🔄"

def format_hint_settings_detailed(hint_settings: Dict[str, bool]) -> str:
    """
    Форматирует подробное описание настроек подсказок.
    
    Args:
        hint_settings: Словарь с настройками подсказок
        
    Returns:
        str: Подробное описание настроек
    """
    result = "💡 <b>Подробные настройки подсказок:</b>\n"
    
    for setting_key in HINT_SETTING_KEYS:
        setting_name = get_hint_setting_name(setting_key)
        setting_value = hint_settings.get(setting_key, True)
        status = "✅" if setting_value else "❌"
        result += f"   {status} {setting_name}\n"
    
    return result

def get_hint_settings_status_text(hint_settings: Dict[str, bool]) -> str:
    """
    Получить текст статуса настроек подсказок для кнопок.
    
    Args:
        hint_settings: Словарь с настройками подсказок
        
    Returns:
        str: Текст статуса для отображения в кнопках
    """
    enabled_count = sum(1 for enabled in hint_settings.values() if enabled)
    total_count = len(hint_settings)
    
    return f"({enabled_count}/{total_count})"

# НОВОЕ: Функция для валидации настроек подсказок
def validate_hint_settings(hint_settings: Dict[str, Any]) -> Dict[str, bool]:
    """
    Валидирует и нормализует настройки подсказок.
    
    Args:
        hint_settings: Словарь с настройками подсказок (могут быть любого типа)
        
    Returns:
        Dict[str, bool]: Нормализованный словарь с булевыми значениями
    """
    validated_settings = {}
    
    for setting_key in HINT_SETTING_KEYS:
        value = hint_settings.get(setting_key, True)
        
        # Нормализуем значение к булевому типу
        if isinstance(value, bool):
            validated_settings[setting_key] = value
        elif isinstance(value, str):
            validated_settings[setting_key] = value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(value, (int, float)):
            validated_settings[setting_key] = bool(value)
        else:
            # По умолчанию включаем
            validated_settings[setting_key] = True
            logger.warning(f"Invalid hint setting value for {setting_key}: {value}, defaulting to True")
    
    return validated_settings
