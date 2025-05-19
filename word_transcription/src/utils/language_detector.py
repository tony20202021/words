import logging
import string
import re
from typing import Optional

# Настройка логирования
logger = logging.getLogger(__name__)

# Символы, характерные для разных языков
GERMAN_CHARS = set("äöüßÄÖÜ")
FRENCH_CHARS = set("éèêëàâçùûüÿæœÉÈÊËÀÂÇÙÛÜŸÆŒ")
SPANISH_CHARS = set("áéíóúñüÁÉÍÓÚÑÜ¿¡")

# Типичные окончания слов для разных языков
GERMAN_ENDINGS = {"en", "er", "ung", "heit", "keit", "lich", "isch"}
FRENCH_ENDINGS = {"eau", "aux", "eux", "oir", "tion", "ment", "ance", "esse"}
SPANISH_ENDINGS = {"ar", "er", "ir", "ción", "dad", "idad", "mente", "ismo"}
ENGLISH_ENDINGS = {"ing", "ed", "ly", "ness", "tion", "ity", "ment", "able"}

# Маркеры определения - примечание: добавлены артикли и предлоги для улучшения определения языка
GERMAN_MARKERS = {"der", "die", "das", "ein", "eine", "mit", "und", "für", "von"}
FRENCH_MARKERS = {"le", "la", "les", "un", "une", "et", "avec", "pour", "de", "du"}
SPANISH_MARKERS = {"el", "la", "los", "las", "un", "una", "y", "con", "por", "de"}
ENGLISH_MARKERS = {"the", "a", "an", "and", "with", "for", "of", "to", "in"}

def detect_language(word: str, context: Optional[str] = None) -> str:
    """
    Определяет язык слова по характерным признакам.
    
    Args:
        word: Слово для определения языка
        context: Контекстное предложение или фраза (если есть)
        
    Returns:
        Код языка ('de' для немецкого, 'fr' для французского, 'es' для испанского, 'en' для английского)
    """
    if not word:
        logger.warning("Передана пустая строка для определения языка")
        return 'en'  # По умолчанию считаем английским
    
    # Преобразуем в нижний регистр для более точного сравнения
    word_lower = word.lower()
    
    # 1. Проверка по специфическим символам
    for char in word:
        if char in GERMAN_CHARS:
            return 'de'  # Немецкий
        if char in FRENCH_CHARS:
            return 'fr'  # Французский
        if char in SPANISH_CHARS:
            return 'es'  # Испанский
    
    # 2. Проверка по окончаниям слов
    for ending in GERMAN_ENDINGS:
        if word_lower.endswith(ending):
            return 'de'
    
    for ending in FRENCH_ENDINGS:
        if word_lower.endswith(ending):
            return 'fr'
    
    for ending in SPANISH_ENDINGS:
        if word_lower.endswith(ending):
            return 'es'
    
    for ending in ENGLISH_ENDINGS:
        if word_lower.endswith(ending):
            return 'en'
    
    # 3. Если есть контекст, анализируем его для определения языка
    if context:
        # Очищаем контекст от знаков препинания и разбиваем на слова
        context_lower = context.lower()
        for char in string.punctuation:
            context_lower = context_lower.replace(char, ' ')
        words = context_lower.split()
        
        # Подсчитываем количество маркеров для каждого языка
        german_count = sum(1 for w in words if w in GERMAN_MARKERS)
        french_count = sum(1 for w in words if w in FRENCH_MARKERS)
        spanish_count = sum(1 for w in words if w in SPANISH_MARKERS)
        english_count = sum(1 for w in words if w in ENGLISH_MARKERS)
        
        # Определяем язык по наибольшему количеству маркеров
        counts = {
            'de': german_count,
            'fr': french_count,
            'es': spanish_count,
            'en': english_count
        }
        
        max_lang = max(counts, key=counts.get)
        if counts[max_lang] > 0:
            return max_lang
    
    # 4. Если не удалось определить по предыдущим методам, используем эвристики
    # Проверка на наличие характерных комбинаций букв
    
    # Немецкие комбинации
    if 'sch' in word_lower or 'tsch' in word_lower or 'tz' in word_lower:
        return 'de'
    
    # Французские комбинации
    if 'eau' in word_lower or 'ou' in word_lower or 'ph' in word_lower:
        return 'fr'
    
    # Испанские комбинации
    if 'll' in word_lower or 'rr' in word_lower or 'ñ' in word_lower:
        return 'es'
    
    # По умолчанию считаем английским
    return 'en'

def clean_text(text: str) -> str:
    """
    Очищает текст от лишних символов и форматирования.
    
    Args:
        text: Исходный текст
        
    Returns:
        Очищенный текст
    """
    # Удаление HTML-тегов
    text = re.sub(r'<[^>]+>', '', text)
    
    # Замена множественных пробелов на одиночные
    text = re.sub(r'\s+', ' ', text)
    
    # Удаление пробелов в начале и конце строки
    text = text.strip()
    
    return text

def is_cyrillic(text: str) -> bool:
    """
    Проверяет, содержит ли текст кириллические символы.
    
    Args:
        text: Текст для проверки
        
    Returns:
        True, если текст содержит кириллические символы, иначе False
    """
    return bool(re.search('[а-яА-Я]', text))

def is_latin(text: str) -> bool:
    """
    Проверяет, содержит ли текст латинские символы.
    
    Args:
        text: Текст для проверки
        
    Returns:
        True, если текст содержит латинские символы, иначе False
    """
    return bool(re.search('[a-zA-Z]', text))

def is_chinese(text: str) -> bool:
    """
    Проверяет, содержит ли текст китайские символы.
    
    Args:
        text: Текст для проверки
        
    Returns:
        True, если текст содержит китайские символы, иначе False
    """
    # Диапазон Unicode для китайских символов
    return bool(re.search('[\u4e00-\u9fff]', text))

def is_word(text: str) -> bool:
    """
    Проверяет, является ли текст словом (содержит только буквы).
    
    Args:
        text: Текст для проверки
        
    Returns:
        True, если текст является словом, иначе False
    """
    # Удаление диакритических знаков и проверка наличия только букв
    return bool(re.match(r'^[A-Za-zÀ-ÿÄäÖöÜüẞßÑñÇç]+$', text))

def get_language_name(lang_code: str) -> str:
    """
    Возвращает название языка по его коду.
    
    Args:
        lang_code: Код языка
        
    Returns:
        Название языка
    """
    languages = {
        'de': 'Немецкий',
        'fr': 'Французский',
        'es': 'Испанский',
        'en': 'Английский',
        'ru': 'Русский',
        'zh': 'Китайский',
        'ja': 'Японский',
        'ko': 'Корейский'
    }
    
    return languages.get(lang_code, 'Неизвестный')

# Тестирование функций, если файл запущен напрямую
if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    
    # Примеры слов на разных языках
    test_words = {
        'de': ['Freiheit', 'Schule', 'Mädchen', 'Bücher'],
        'fr': ['bonjour', 'maison', 'voiture', 'français'],
        'es': ['gracias', 'cerveza', 'mañana', 'español'],
        'en': ['freedom', 'school', 'computer', 'english']
    }
    
    # Тестирование функции определения языка
    for lang, words in test_words.items():
        for word in words:
            detected = detect_language(word)
            if detected == lang:
                logger.info(f"Успешно определен язык для '{word}': {get_language_name(detected)}")
            else:
                logger.warning(f"Ошибка определения языка для '{word}': ожидался {get_language_name(lang)}, получен {get_language_name(detected)}")
                