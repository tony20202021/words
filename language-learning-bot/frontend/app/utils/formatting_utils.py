"""
Utility functions for formatting.
UPDATED: Added support for writing images settings in formatting.
UPDATED: Removed hieroglyphic language restrictions - writing images are controlled by user settings only.
"""

from datetime import datetime
import locale
import random
from typing import Dict, Any, List, Optional
from aiogram.types import BufferedInputFile
from app.utils.big_word_generator import generate_big_word

from app.utils.logger import setup_logger
from app.utils.hint_constants import (
    HINT_SETTING_KEYS, 
    get_hint_setting_name
)

logger = setup_logger(__name__)

MAX_MESSAGE_LENGTH = 2048

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
    show_radicals=False,
    show_references=False,
    show_tones=False,
    show_sounds=False,
    random_foreign=True,
    random_transcription=True,
    random_sound=True,    
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
        show_radicals: Показывать ли радикалы
        show_references: Показывать ли ссылки
        show_tones: Показывать ли тоны
        show_sounds: Показывать ли звуки
        random_foreign: Начинать ли с иностранных слов
        random_transcription: Начинать ли с транскрипций
        random_sound: Начинать ли со звуков
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
    
    show_radicals = "Показывать ✅" if show_radicals else "Скрывать ❌"
    settings_text += f"   • Радикалы: <b>{show_radicals}</b>\n"
    
    show_references = "Показывать ✅" if show_references else "Скрывать ❌"
    settings_text += f"   • Ссылки: <b>{show_references}</b>\n"
    
    show_tones = "Показывать ✅" if show_tones else "Скрывать ❌"
    settings_text += f"   • Тоны: <b>{show_tones}</b>\n"
    
    show_sounds = "Показывать ✅" if show_sounds else "Скрывать ❌"
    settings_text += f"   • Звуки: <b>{show_sounds}</b>\n"

    random_foreign_status = "Да ✅" if random_foreign else "Нет ❌"
    settings_text += f"   • Рандомно начинать с иностранных слов: <b>{random_foreign_status}</b>\n"
    random_transcription_status = "Да ✅" if random_transcription else "Нет ❌"
    settings_text += f"   • Рандомно начинать с транскрипций: <b>{random_transcription_status}</b>\n"
    random_sound_status = "Да ✅" if random_sound else "Нет ❌"
    settings_text += f"   • Рандомно начинать со звуков: <b>{random_sound_status}</b>\n"
    
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

async def format_study_word_message(
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
    show_radicals=False,
    show_references=False,
    show_tones=False,
    show_sounds=False,
    random_foreign=True,
    random_transcription=True,
    random_sound=True,
    word_foreign=None,
    transcription=None,
    radicals=None,
    references=None,
    tones=None,
    sounds=None,
    sounds_files=None,
    show_big=False,
    show_check_date=True,
    words_studied=0,
    words_for_today=0,
    session_processed=0,
    total_words=0,
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
        sounds: Звуки слова
        show_big: Показывать ли большое слово
        show_check_date: Показывать ли дату проверки
        words_studied: Количество слов, изученных в сессии
        words_for_today: Количество слов на текущую сессию
        session_processed: Количество слов, обработанных в сессии
        total_words: Общее количество слов в языке
    Returns:
        str: Отформатированное сообщение
    """
    HIDE_TONES = False
    
    message = ""
    messages_tones_all = None
    message_references = None
    message_sounds = None
    
    message = f"📝 Язык: \"{language_name_ru} ({language_name_foreign})\":\n\n"
    message += f"Слово номер: <b>{word_number}</b> / <b>{words_studied}</b> / <b>{total_words}</b>\n" 
    
    if word_number == words_studied:
        message += f"(завершающее из изученых)\n"
    elif word_number > words_studied:
        message += f"(новое слово, изучается первый раз)\n"

    if word_number <= words_studied:
        if show_word:
            if session_processed == words_for_today:
                message += f"(завершающее в текущей сессии: <b>{session_processed}</b>)\n"
            else:
                message += f"(изучено в текущей сессии: <b>{session_processed}</b> из <b>{words_for_today}</b>)\n"
        else:
            if session_processed == words_for_today:
                message += f"(завершающее в текущей сессии: <b>{session_processed + 1}</b>)\n"
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
    
    if show_word:
        first_translation = True
        first_transcription = False
        first_foreign = False
        first_sound = False        
    else:
        options = ["translation"]
        if random_transcription:
            options.append("transcription")
        if random_foreign:
            options.append("foreign")
        if random_sound:
            options.append("sound")
        first = random.choice(options)
        first_translation = (first == "translation")
        first_transcription = (first == "transcription")
        first_foreign = (first == "foreign")
        first_sound = (first == "sound")

    logger.info(f"show_word: {show_word}, random_foreign: {random_foreign}, random_transcription: {random_transcription}, random_sound: {random_sound}")
    logger.info(f"first_translation: {first_translation}, first_transcription: {first_transcription}, first_foreign: {first_foreign}")
    
    message += "\n"    
    if first_translation:
        message += f"🔍 Слово на русском:\n<b>{translation}</b>\n\n"
    elif first_transcription:
        message += f"🔍 Транскрипция:\n<b>[{transcription}]</b>\n\n"
    elif first_foreign:
        message += f"📝 Слово на иностранном:\n<b>{word_foreign}</b>\n\n"
    
    # Если нужно показать слово, добавляем его с кликабельной ссылкой
    if show_word and word_foreign:
        if translation and (not first_translation):
            message += f"🔍 Слово на русском:\n<b>{translation}</b>\n\n"
        # Создаем кликабельную ссылку на команду /show_big
        if transcription and (not first_transcription):
            escaped_transcription = transcription.replace('\n', ',')
            message += f"🔊 Транскрипция:\n<b>[{escaped_transcription}]</b>\n\n"
        if word_foreign and (not first_foreign):
            if show_big:
                message += f"📝 Слово на иностранном:\n<b>{word_foreign}</b>(/show_big) 🔍\n\n"
            else:
                message += f"📝 Слово на иностранном:\n<b>{word_foreign}</b>\n\n"

        if show_tones and tones:
            star_transcription = [(word[0] + '*') for word in escaped_transcription.split(' ')]
            star_transcription = ' '.join(star_transcription)

        if show_tones and tones:
            tones_filtered = []
            words_number_begin_str_multiple = " - [<i>"
            words_number_end_str_multiple = "</i>]"
            words_number_begin_str_single = ": [<i>"
            words_number_end_str_single = "</i>]"
            words_foreigh_end_str = "</b>: "

            for tone in tones.split('\n'):
                words_number_begin = tone.find(words_number_begin_str_multiple)
                if words_number_begin > -1:
                    words_number_end = tone.find(words_number_end_str_multiple)
                    words_number_found = int(tone[words_number_begin + len(words_number_begin_str_multiple):words_number_end])
                    # logger.info(f"{words_number}: {tone}")
                    
                    words_foreigh_begin = words_number_end + len(words_number_end_str_multiple) + len(" <b>")
                    words_foreigh_end = words_foreigh_begin + tone[words_foreigh_begin:].find(words_foreigh_end_str)
                    words_foreigh_found = tone[words_foreigh_begin:words_foreigh_end]
                    
                    # logger.info(f"words_number_found: {words_number_found}, words_foreigh_found: {words_foreigh_found}, words_foreigh_begin: {words_foreigh_begin}, words_foreigh_end: {words_foreigh_end}, tone: {tone}")

                    if HIDE_TONES and ((len(words_foreigh_found) == 1) and (words_foreigh_found in word_foreign)):
                        tones_filtered.append(tone[ : words_number_end + len(words_number_end_str_multiple)] + ": <b>***</b>")
                    else:
                        if words_number_found <= words_studied:
                            if (not HIDE_TONES) or ((len(words_foreigh_found) == 1)):
                                tones_filtered.append(tone)
                            else:
                                tones_filtered.append(tone[ : words_number_end + len(words_number_end_str_multiple)] + f" <b>{words_foreigh_found}</b>: ***")

                else:
                    words_number_begin = tone.find(words_number_begin_str_single)
                    if words_number_begin > -1:
                        words_number_end = tone.find(words_number_end_str_single)
                        words_number_found = int(tone[words_number_begin + len(words_number_begin_str_single):words_number_end])
                        # logger.info(f"{words_number}: {tone}")
                        if words_number_found <= words_studied:
                            tones_filtered.append(tone)
                        else:
                            tones_filtered.append(tone[:words_number_begin] + " counts: 1")
                    else:
                        tones_filtered.append(tone)

            tones_filtered = "\n".join(tones_filtered)

            messages_tones_all = []
            if len(tones_filtered) <= MAX_MESSAGE_LENGTH:
                messages_tones_all.append(f"🔍 Тоны:\n\n{tones_filtered}\n\n")
            else:
                tones_formatted = ""
                for tone in tones_filtered.split('\n'):
                    if len(tones_formatted) + len(tone) <= MAX_MESSAGE_LENGTH:
                        if tones_formatted != "":
                            tones_formatted += "\n"
                        tones_formatted += tone
                    else:
                        messages_tones_all.append(f"🔍 Тоны:\n\n{tones_formatted}\n\n")
                        tones_formatted = tone
                if tones_formatted != "":
                    messages_tones_all.append(f"🔍 Тоны:\n\n{tones_formatted}\n\n")

        if show_references and references:
            references_filtered = []
            words_number_begin_str = "<i>[#"
            words_number_end_str = "]</i>"
            words_foreigh_end_str = " ["

            for reference in references.split('\n'):
                words_number_begin = reference.find(words_number_begin_str)
                if words_number_begin > -1:
                    words_number_end = reference.find(words_number_end_str)
                    words_number_found = int(reference[words_number_begin + len(words_number_begin_str):words_number_end])

                    words_foreigh_begin = words_number_end + len(words_number_end_str)
                    words_foreigh_end = words_foreigh_begin + reference[words_foreigh_begin:].find(words_foreigh_end_str)
                    words_foreigh_found = reference[words_foreigh_begin:words_foreigh_end]

                    reference_hidden = reference[:words_foreigh_begin] + "<tg-spoiler>" + reference[words_foreigh_begin:] + "</tg-spoiler>"

                    if words_number_found <= words_studied:
                        references_filtered.append(reference)
                    else:
                        # logger.info(f"words_number_found: {words_number_found}, words_foreigh_found: {words_foreigh_found}, words_foreigh_begin: {words_foreigh_begin}, words_foreigh_end: {words_foreigh_end}, reference: {reference}")
                        if len(words_foreigh_found) == 1:
                            references_filtered.append(reference)
                else:
                    references_filtered.append(reference)

            references_filtered = "\n".join(references_filtered)

            message_references = f"🔍 Ссылки:\n{references_filtered}\n\n"

    if show_sounds and sounds_files:
        message_sounds = []
        for sound_file in sounds_files:
            # Add audio file as dict to distinguish from text messages
            # Preserve filename if available
            filename = getattr(sound_file, 'filename', None)
            message_sounds.append({"type": "audio", "file": sound_file, "filename": filename})

    if show_word and show_big:
        big_word_message = await generate_big_word_message(
            word_foreign,
            transcription,
        )

    result = []
    if message_sounds and (first_sound or show_word):
        result.extend(message_sounds)
    if messages_tones_all:
        result.append({"type": "text", "text": f"🔍 Тоны (подсказка):\n<b>[{star_transcription}]</b>"})
        for message_tone in messages_tones_all:
            result.append({"type": "text", "text": message_tone})
    if message_references:
        result.append({"type": "text", "text": message_references})
    if show_word and show_radicals and radicals:
        result.append({"type": "text", "text": f"🔍 Радикалы:\n{radicals}\n\n"})
    if show_word and show_big:
        result.append({"type": "image", "image": big_word_message})

    result.append({"type": "text", "text": message})

    return result
    
async def generate_big_word_message(
    word_foreign,
    transcription,
):
    # Generate word image
    logger.info(f"Generating image for word: '{word_foreign}', transcription: '{transcription}'")
    
    image_buffer = await generate_big_word(
        word=word_foreign,
        transcription=transcription,
    )
    
    # Create BufferedInputFile from BytesIO for Telegram
    image_buffer.seek(0)  # Reset buffer position
    input_file = BufferedInputFile(
        file=image_buffer.read(),
        filename=f"word_{word_foreign}.png"
    )

    return input_file
    

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
    