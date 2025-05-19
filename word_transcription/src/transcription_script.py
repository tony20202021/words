#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import argparse
import time
import os
import requests
from typing import Dict, List, Optional, Tuple, Any
import sys

# Добавляем текущую директорию в путь для импорта модулей
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Импортируем модуль для работы с Excel
try:
    # Сначала пробуем импортировать из того же каталога
    import excel_processor
    process_excel_to_json = excel_processor.process_excel_to_json
except ImportError as e:
    print("Ошибка импорта модуля excel_processor. ")
    print(e)
    try:
        # Потом пробуем импортировать как часть пакета
        from src.excel_processor import process_excel_to_json
    except ImportError as e:
        print("Ошибка импорта модуля excel_processor. ")
        print(e)
        print("Убедитесь, что он находится в том же каталоге или в src/")
        sys.exit(1)

# Настройка логирования
log_dir = os.path.join(parent_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'transcription.log')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TranscriptionService:
    """Базовый класс для сервисов транскрипции"""
    
    def get_transcription(self, word: str, lang_code: str) -> Optional[str]:
        """
        Получает транскрипцию для слова.
        
        Args:
            word: Слово для транскрибирования
            lang_code: Код языка (например, 'de', 'fr', 'es', 'en')
            
        Returns:
            Строка с транскрипцией или None в случае ошибки
        """
        raise NotImplementedError("Подклассы должны реализовать этот метод")


class DictionaryService(TranscriptionService):
    """Сервис транскрипции на основе локальных словарей"""
    
    def __init__(self, dict_dir: Optional[str] = None):
        # Путь к директории с локальными словарями
        if dict_dir is None:
            # Ищем словари в стандартных местах
            possible_dirs = [
                os.path.join(parent_dir, 'data', 'dictionaries'),  # В каталоге data/dictionaries проекта
                os.path.join(current_dir, 'data', 'dictionaries'),  # В каталоге data/dictionaries рядом со скриптом
                'data/dictionaries'  # Относительный путь
            ]
            
            for path in possible_dirs:
                if os.path.exists(path) and os.path.isdir(path):
                    self.dict_dir = path
                    break
            else:
                # Если директория не найдена, используем путь по умолчанию (будет выдано предупреждение)
                self.dict_dir = os.path.join(parent_dir, 'data', 'dictionaries')
                logger.warning(f"Директория словарей не найдена. Будет использоваться путь по умолчанию: {self.dict_dir}")
        else:
            self.dict_dir = dict_dir
        
        self.dictionaries = {}  # Словари для разных языков
        self.load_dictionaries()
        
    def load_dictionaries(self) -> None:
        """Загружает словари из файлов"""
        try:
            # Создаем директорию для словарей, если она не существует
            os.makedirs(self.dict_dir, exist_ok=True)
            
            # Словари для основных языков
            dict_files = {
                'de': 'de_dict.json',  # Немецкий
                'fr': 'fr_dict.json',  # Французский
                'es': 'es_dict.json',  # Испанский
                'en': 'en_dict.json'   # Английский
            }
            
            for lang_code, filename in dict_files.items():
                dict_path = os.path.join(self.dict_dir, filename)
                
                if os.path.exists(dict_path):
                    with open(dict_path, 'r', encoding='utf-8') as f:
                        self.dictionaries[lang_code] = json.load(f)
                    logger.info(f"Загружен словарь {filename} с {len(self.dictionaries[lang_code])} словами")
                else:
                    # Создаем пустой словарь, если файл не существует
                    self.dictionaries[lang_code] = {}
                    logger.warning(f"Словарь {filename} не найден, создан пустой словарь")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки словарей: {e}")
            
    def get_transcription(self, word: str, lang_code: str) -> Optional[str]:
        """
        Получает транскрипцию из локального словаря.
        
        Args:
            word: Слово для транскрибирования
            lang_code: Код языка
            
        Returns:
            Строка с транскрипцией или None, если слово не найдено
        """
        if lang_code not in self.dictionaries:
            logger.warning(f"Словарь для языка {lang_code} не загружен")
            return None
            
        # Приводим слово к нижнему регистру для поиска в словаре
        word_lower = word.lower()
        
        # Ищем слово в словаре
        if word_lower in self.dictionaries[lang_code]:
            transcription = self.dictionaries[lang_code][word_lower]
            logger.debug(f"Найдена транскрипция в словаре для '{word}': {transcription}")
            return transcription
            
        logger.debug(f"Слово '{word}' не найдено в словаре для языка {lang_code}")
        return None
        
    def add_to_dictionary(self, word: str, transcription: str, lang_code: str) -> None:
        """
        Добавляет слово и его транскрипцию в словарь.
        
        Args:
            word: Слово
            transcription: Транскрипция
            lang_code: Код языка
        """
        if lang_code not in self.dictionaries:
            self.dictionaries[lang_code] = {}
            
        word_lower = word.lower()
        self.dictionaries[lang_code][word_lower] = transcription
        
        # Сохраняем обновленный словарь
        try:
            dict_path = os.path.join(self.dict_dir, f"{lang_code}_dict.json")
            with open(dict_path, 'w', encoding='utf-8') as f:
                json.dump(self.dictionaries[lang_code], f, ensure_ascii=False, indent=4)
            logger.debug(f"Словарь {lang_code} обновлен и сохранен")
        except Exception as e:
            logger.error(f"Ошибка сохранения словаря {lang_code}: {e}")


class ForvoService(TranscriptionService):
    """Сервис транскрипции на основе Forvo API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://apifree.forvo.com/key"
        self.api_key = api_key or os.environ.get("FORVO_API_KEY", "")
        self.session = requests.Session()
        
    def get_transcription(self, word: str, lang_code: str) -> Optional[str]:
        """
        Получает транскрипцию через Forvo API.
        
        Args:
            word: Слово для транскрибирования
            lang_code: Код языка
            
        Returns:
            Строка с транскрипцией или None, если слово не найдено
        """
        if not self.api_key:
            logger.warning("API ключ Forvo не установлен. Установите его через аргумент api_key или переменную окружения FORVO_API_KEY")
            return None
            
        try:
            url = f"{self.base_url}/{self.api_key}/format/json/action/word-pronunciations/word/{word}/language/{lang_code}"
            logger.debug(f"Отправка запроса к Forvo API: {url}")
            
            response = self.session.get(url, timeout=5)
            
            if response.status_code != 200:
                logger.warning(f"Forvo API вернуло код состояния {response.status_code} для '{word}'")
                return None
                
            data = response.json()
            
            # Извлечение транскрипции из ответа
            if 'items' in data and len(data['items']) > 0:
                for item in data['items']:
                    if 'standard_pronunciation' in item:
                        transcription = item['standard_pronunciation']
                        logger.debug(f"Получена транскрипция: {transcription}")
                        return transcription
                        
            logger.warning(f"Транскрипция не найдена в Forvo API для '{word}'")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения транскрипции из Forvo API для '{word}': {e}")
            return None


class GoogleTranslateService(TranscriptionService):
    """Сервис транскрипции на основе Google Translate API (неофициальный)"""
    
    def __init__(self):
        self.base_url = "https://translate.googleapis.com/translate_a/single"
        self.session = requests.Session()
        
    def get_transcription(self, word: str, lang_code: str) -> Optional[str]:
        try:
            params = {
                'client': 'gtx',
                'dt': 't',
                'dt': 'rm',  # Запрос транскрипции
                'dj': '1',   # Возврат в формате JSON
                'sl': lang_code,
                'tl': 'en',  # Перевод на английский
                'q': word
            }
            
            logger.debug(f"Отправка запроса к Google Translate API: {self.base_url} с параметрами {params}")
            
            response = self.session.get(self.base_url, params=params, timeout=5)
            
            if response.status_code != 200:
                logger.warning(f"Google Translate API вернуло код состояния {response.status_code} для '{word}'")
                return None
                
            data = response.json()
            
            # Извлечение транскрипции из ответа Google
            if 'sentences' in data and len(data['sentences']) > 0 and 'translit' in data['sentences'][0]:
                transcription = data['sentences'][0]['translit']
                logger.debug(f"Получена транскрипция: {transcription}")
                return transcription
                
            logger.warning(f"Транскрипция не найдена в Google Translate для '{word}'")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения транскрипции из Google Translate для '{word}': {e}")
            return None


class EpitranService(TranscriptionService):
    """Сервис транскрипции на основе библиотеки Epitran"""
    
    def __init__(self):
        self.epitran_available = False
        
        # Словарь соответствий кодов языков и эпитран-кодов
        self.language_map = {
            'de': 'deu-Latn',  # Немецкий
            'fr': 'fra-Latn',  # Французский
            'es': 'spa-Latn',  # Испанский
            'en': 'eng-Latn',  # Английский
            'it': 'ita-Latn',  # Итальянский
            'nl': 'nld-Latn',  # Нидерландский
            'pl': 'pol-Latn',  # Польский
            'ru': 'rus-Cyrl',  # Русский
            'tr': 'tur-Latn'   # Турецкий
        }
        
        # Словарь с инстансами Epitran для каждого языка
        self.epitran_instances = {}
        
        # Проверка доступности Epitran
        try:
            import epitran
            self.epitran_available = True
            logger.info("Epitran успешно импортирован")
        except ImportError as e:
            logger.warning(f"Библиотека Epitran не установлена: {e}. Установите ее с помощью: pip install epitran==1.1.0 panphon==0.19")
        except Exception as e:
            logger.error(f"Ошибка при импорте Epitran: {e}")
    
    def get_transcription(self, word: str, lang_code: str) -> Optional[str]:
        """
        Получает транскрипцию с помощью Epitran.
        
        Args:
            word: Слово для транскрибирования
            lang_code: Код языка
            
        Returns:
            Строка с транскрипцией в формате IPA или None, если язык не поддерживается
        """
        if not self.epitran_available:
            logger.warning("Epitran не доступен")
            return None
            
        # Проверка поддержки языка
        if lang_code not in self.language_map:
            logger.warning(f"Язык {lang_code} не поддерживается Epitran")
            return None
            
        try:
            # Ленивая инициализация Epitran для нужного языка
            if lang_code not in self.epitran_instances:
                try:
                    import epitran
                    epitran_code = self.language_map[lang_code]
                    self.epitran_instances[lang_code] = epitran.Epitran(epitran_code)
                    logger.debug(f"Создан экземпляр Epitran для языка {lang_code} ({epitran_code})")
                except Exception as e:
                    logger.error(f"Ошибка при создании экземпляра Epitran для языка {lang_code}: {e}")
                    return None
                
            # Получение транскрипции
            transcription = self.epitran_instances[lang_code].transliterate(word)
            
            # Форматирование транскрипции между слешами
            formatted_transcription = f"/{transcription}/"
            
            logger.debug(f"Получена транскрипция через Epitran для '{word}': {formatted_transcription}")
            return formatted_transcription
            
        except Exception as e:
            logger.error(f"Ошибка при получении транскрипции через Epitran для '{word}': {e}")
            return None

class WiktionaryService(TranscriptionService):
    """Сервис транскрипции на основе Wiktionary API"""
    
    def __init__(self):
        self.base_url = "https://en.wiktionary.org/w/api.php"
        self.session = requests.Session()
        
        # Словарь языковых секций на Wiktionary
        self.language_sections = {
            'de': 'German',
            'fr': 'French',
            'es': 'Spanish',
            'en': 'English',
            'it': 'Italian',
            'nl': 'Dutch',
            'pl': 'Polish',
            'ru': 'Russian',
            'tr': 'Turkish'
        }
    
    def get_transcription(self, word: str, lang_code: str) -> Optional[str]:
        """
        Получает транскрипцию из Wiktionary.
        
        Args:
            word: Слово для транскрибирования
            lang_code: Код языка
            
        Returns:
            Строка с транскрипцией или None, если слово не найдено
        """
        # Проверка поддержки языка
        if lang_code not in self.language_sections:
            logger.warning(f"Язык {lang_code} не имеет соответствующей секции на Wiktionary")
            return None
            
        try:
            # Параметры запроса к API
            params = {
                'action': 'parse',
                'page': word,
                'prop': 'wikitext',
                'format': 'json'
            }
            
            logger.debug(f"Отправка запроса к Wiktionary API: {self.base_url} с параметрами {params}")
            
            response = self.session.get(self.base_url, params=params, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Wiktionary API вернуло код состояния {response.status_code} для '{word}'")
                return None
                
            data = response.json()
            
            # Проверка наличия статьи
            if 'error' in data or 'parse' not in data:
                logger.warning(f"Статья для слова '{word}' не найдена в Wiktionary")
                return None
                
            # Извлечение wikitext
            wikitext = data['parse']['wikitext']['*']
            
            # Парсинг wikitext
            import wikitextparser as wtp
            parsed = wtp.parse(wikitext)
            
            # Поиск секции для указанного языка
            language_section = self.language_sections[lang_code]
            sections = parsed.get_sections(level=2)
            
            target_section = None
            for section in sections:
                if section.title.strip() == language_section:
                    target_section = section
                    break
            
            if not target_section:
                logger.warning(f"Секция {language_section} для слова '{word}' не найдена в Wiktionary")
                return None
            
            # Поиск транскрипции в секции
            transcription = None
            
            # Поиск шаблона IPA
            ipa_templates = target_section.templates
            for template in ipa_templates:
                if 'IPA' in template.name:
                    # Извлечение параметров шаблона
                    for param in template.arguments:
                        value = param.value.strip()
                        if '//' in value or '[]' in value or value.startswith('/') or value.startswith('['):
                            # Найдена транскрипция
                            transcription = value
                            break
                
                if transcription:
                    break
            
            # Если транскрипция не найдена в шаблонах, поиск в тексте
            if not transcription:
                # Паттерны для поиска транскрипций
                import re
                ipa_patterns = [
                    r'/[^/]+/',        # Формат /ˈsʌmθɪŋ/
                    r'\[([^\]]+)\]',   # Формат [ˈsʌmθɪŋ]
                    r'{{IPA\|([^}]+)}}' # Формат {{IPA|/ˈsʌmθɪŋ/}}
                ]
                
                for pattern in ipa_patterns:
                    matches = re.findall(pattern, target_section.string)
                    if matches:
                        transcription = matches[0]
                        break
            
            if transcription:
                logger.debug(f"Получена транскрипция из Wiktionary для '{word}': {transcription}")
                return transcription
            else:
                logger.warning(f"Транскрипция для слова '{word}' не найдена в Wiktionary")
                return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении транскрипции из Wiktionary для '{word}': {e}")
            return None

class TranscriptionManager:
    """Менеджер транскрипций, координирующий работу различных сервисов"""
    
    def __init__(self, dict_dir: Optional[str] = None, forvo_api_key: Optional[str] = None):
        self.services = [
            DictionaryService(dict_dir),    # Сначала пробуем локальный словарь
            EpitranService(),               # Затем Epitran (местное решение)
            ForvoService(forvo_api_key),    # Затем Forvo API
            WiktionaryService(),            # Затем Wiktionary API
            GoogleTranslateService()        # И наконец Google Translate
        ]
        self.cache = {}  # Кэш для уже полученных транскрипций
        
    def get_transcription(self, word: str, lang_code: str) -> Optional[str]:
        """
        Пытается получить транскрипцию, используя доступные сервисы по порядку.
        
        Args:
            word: Слово для транскрибирования
            lang_code: Код языка
            
        Returns:
            Строка с транскрипцией или None, если ни один сервис не смог предоставить транскрипцию
        """
        # Проверяем кэш
        cache_key = f"{word}_{lang_code}"
        if cache_key in self.cache:
            logger.debug(f"Транскрипция для '{word}' найдена в кэше: {self.cache[cache_key]}")
            return self.cache[cache_key]
            
        # Пробуем все сервисы по очереди
        for service in self.services:
            transcription = service.get_transcription(word, lang_code)
            if transcription:
                logger.info(f"Получена транскрипция для '{word}': {transcription}")
                
                # Добавляем в словарь, если получили через API
                if isinstance(service, (ForvoService, GoogleTranslateService)) and isinstance(self.services[0], DictionaryService):
                    self.services[0].add_to_dictionary(word, transcription, lang_code)
                
                # Сохраняем в кэш
                self.cache[cache_key] = transcription
                return transcription
                
        logger.warning(f"Не удалось получить транскрипцию для '{word}' с использованием всех доступных сервисов")
        return None


def detect_language(word: str) -> str:
    """
    Определяет язык слова по характерным признакам.
    
    Args:
        word: Слово для определения языка
        
    Returns:
        Код языка ('de' для немецкого, 'fr' для французского, 'es' для испанского, 'en' для английского)
    """
    if not word:
        logger.warning("Передана пустая строка для определения языка")
        return 'en'  # По умолчанию считаем английским
    
    # Символы, характерные для разных языков
    german_chars = "äöüßÄÖÜ"
    french_chars = "éèêëàâçùûüÿæœÉÈÊËÀÂÇÙÛÜŸÆŒ"
    spanish_chars = "áéíóúñüÁÉÍÓÚÑÜ¿¡"
    
    # Проверяем наличие характерных символов
    for char in word:
        if char in german_chars:
            return 'de'  # Немецкий
        if char in french_chars:
            return 'fr'  # Французский
        if char in spanish_chars:
            return 'es'  # Испанский
    
    # Если нет характерных символов, используем эвристики
    
    # Немецкие признаки
    if word.endswith('en') or word.endswith('er') or word.endswith('ung'):
        return 'de'
    
    # Французские признаки
    if word.endswith('eau') or word.endswith('aux') or word.endswith('eux') or word.endswith('oir'):
        return 'fr'
    
    # Испанские признаки
    if word.endswith('ar') or word.endswith('er') or word.endswith('ir') or word.endswith('ción'):
        return 'es'
    
    # По умолчанию считаем английским
    return 'en'


def process_words(data: Dict[str, Dict[str, Any]], 
                 transcription_manager: TranscriptionManager,
                 language_field: str = 'language',
                 word_field: str = 'word',
                 transcription_field: str = 'transcription') -> Tuple[int, int]:
    """
    Обрабатывает все слова, добавляя транскрипцию.
    
    Args:
        data: Словарь словарей со словами
        transcription_manager: Менеджер транскрипций
        language_field: Имя поля с кодом языка
        word_field: Имя поля со словом
        transcription_field: Имя поля для сохранения транскрипции
        
    Returns:
        Кортеж (успешно_обработано, всего_слов)
    """
    success_count = 0
    
    for word_id, word_data in data.items():
        # Проверяем наличие поля со словом
        if word_field not in word_data:
            logger.warning(f"Запись {word_id} не содержит поля '{word_field}', пропускаем")
            continue
            
        word = word_data[word_field]
        
        # Пропускаем слова, у которых уже есть транскрипция, если она не пустая
        if transcription_field in word_data and word_data[transcription_field]:
            logger.debug(f"Пропускаем '{word}': уже есть транскрипция '{word_data[transcription_field]}'")
            success_count += 1
            continue
            
        # Получаем код языка или определяем его
        # Проверяем наличие кода языка в правильном поле
        if language_field in word_data:
            lang_code = word_data[language_field]
        else:
            # Если поля нет, определяем язык
            lang_code = detect_language(word)
        
        # Получаем транскрипцию
        transcription = transcription_manager.get_transcription(word, lang_code)
        
        # Добавляем транскрипцию в данные
        if transcription:
            word_data[transcription_field] = transcription
            success_count += 1
            
            # Если код языка был определен автоматически, сохраняем его в правильное поле
            if language_field not in word_data:
                word_data[language_field] = lang_code
                
        # Добавляем паузу, чтобы не перегружать API
        time.sleep(0.5)
        
    return success_count, len(data)

def load_json_file(file_path: str) -> Dict[str, Dict[str, Any]]:
    """Загружает данные из JSON-файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Успешно загружено {len(data)} записей из файла {file_path}")
        return data
    except Exception as e:
        logger.error(f"Ошибка загрузки JSON из файла {file_path}: {e}")
        raise


def save_json_file(file_path: str, data: Dict[str, Dict[str, Any]]) -> None:
    """Сохраняет данные в JSON-файл"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"Успешно сохранено {len(data)} записей в файл {file_path}")
    except Exception as e:
        logger.error(f"Ошибка сохранения JSON в файл {file_path}: {e}")
        raise


def main():
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description='Добавление транскрипций к иностранным словам')
    parser.add_argument('input_file', help='Путь к входному файлу (Excel или JSON)')
    parser.add_argument('--output-file', help='Путь к выходному JSON-файлу (по умолчанию: перезаписывает входной файл с другим расширением)')
    parser.add_argument('--start-index', type=int, default=0, help='Начальный индекс для обработки Excel-файла (по умолчанию: 0)')
    parser.add_argument('--end-index', type=int, help='Конечный индекс для обработки Excel-файла (по умолчанию: до конца файла)')
    parser.add_argument('--lang-field', default='language', help='Имя поля с кодом языка')
    parser.add_argument('--word-field', default='word', help='Имя поля со словом')
    parser.add_argument('--transcription-field', default='transcription', help='Имя поля для сохранения транскрипции')
    parser.add_argument('--dict-dir', help='Путь к директории со словарями')
    parser.add_argument('--forvo-key', help='API ключ для Forvo')
    parser.add_argument('--language', help='Код языка для всех слов (de, fr, es, en)')  # Добавить эту строку
    parser.add_argument('--use-epitran', action='store_true', help='Использовать Epitran для транскрипции')
    parser.add_argument('--use-wiktionary', action='store_true', help='Использовать Wiktionary API для транскрипции')
    parser.add_argument('--use-forvo', action='store_true', help='Использовать Forvo API для транскрипции')
    parser.add_argument('--use-google', action='store_true', help='Использовать Google Translate API для транскрипции')
    parser.add_argument('--verbose', '-v', action='store_true', help='Подробный вывод')
    args = parser.parse_args()
    
    # Настройка уровня логирования
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Включен подробный режим логирования")
    
    # Определение типа входного файла
    input_file = args.input_file
    input_is_excel = input_file.endswith('.xls') or input_file.endswith('.xlsx')
    
    # Если выходной файл не указан, формируем его имя на основе входного
    if args.output_file:
        output_file = args.output_file
    else:
        # Если входной файл - Excel, формируем имя для JSON
        if input_is_excel:
            output_file = os.path.splitext(input_file)[0] + '.json'
        # Если входной файл - JSON, используем его же
        else:
            output_file = input_file
    
    try:
        # Получение данных - либо из Excel, либо из JSON
        if input_is_excel:
            logger.info(f"Обработка Excel-файла: {input_file}")
            data = process_excel_to_json(input_file, args.start_index, args.end_index, args.language)  # Добавьте args.language
        else:
            logger.info(f"Загрузка JSON-файла: {input_file}")
            data = load_json_file(input_file)
        
        # Создание менеджера транскрипций
        transcription_manager = TranscriptionManager(args.dict_dir, args.forvo_key)
        
        # Конфигурирование активных сервисов
        active_services = []
        service_flags = [args.use_epitran, args.use_wiktionary, args.use_forvo, args.use_google]
        
        if any(service_flags):
            # Всегда добавляем словарный сервис первым
            active_services.append(transcription_manager.services[0])
            
            # Добавляем выбранные сервисы
            if args.use_epitran:
                active_services.append(EpitranService())
            if args.use_wiktionary:
                active_services.append(WiktionaryService())
            if args.use_forvo:
                active_services.append(ForvoService(args.forvo_key))
            if args.use_google:
                active_services.append(GoogleTranslateService())
                
            # Заменяем список сервисов только выбранными
            transcription_manager.services = active_services
            logger.info(f"Используются следующие сервисы: {[service.__class__.__name__ for service in active_services]}")
        
        # Обработка слов
        success_count, total_count = process_words(
            data,
            transcription_manager,
            language_field=args.lang_field,
            word_field=args.word_field,
            transcription_field=args.transcription_field
        )
        
        # Сохранение результатов
        save_json_file(output_file, data)
        
        # Вывод статистики
        logger.info(f"Обработка завершена: {success_count}/{total_count} записей имеют транскрипции")
        
    except Exception as e:
        logger.error(f"Произошла ошибка во время обработки: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())
