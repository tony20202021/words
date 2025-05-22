#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Менеджер транскрипций, управляющий всеми сервисами
"""

import logging
import time
import re
from typing import Dict, List, Optional, Any, Set, Tuple

from src.services import (
    TranscriptionService,
    DictionaryService,
    EpitranService,
    ForvoService,
    GoogleTranslateService,
    WiktionaryService,
    G2PService,
    PhonemizeService,
    EasyPronunciationService,
    IBMWatsonService,
    CharsiuG2PService,
    OpenAIService
)

logger = logging.getLogger(__name__)

class TranscriptionManager:
    """Менеджер транскрипций, координирующий работу различных сервисов"""

    def __init__(self, dict_dir: Optional[str] = None, 
                forvo_api_key: Optional[str] = None,
                easypronunciation_api_key: Optional[str] = None,
                ibm_watson_api_key: Optional[str] = None,
                openai_api_key: Optional[str] = None,
                enabled_services: Optional[List[str]] = None,
                language: Optional[str] = None):  # Добавляем параметр language
        """
        Инициализирует менеджер транскрипций.
        
        Args:
            dict_dir: Путь к директории с локальными словарями
            forvo_api_key: API ключ для Forvo
            easypronunciation_api_key: API ключ для EasyPronunciation
            ibm_watson_api_key: API ключ для IBM Watson
            openai_api_key: API ключ для OpenAI
            enabled_services: Список названий активных сервисов. Если None, то используются все доступные.
                Возможные значения: 'dictionary', 'epitran', 'forvo', 'google', 'wiktionary',
                'g2p', 'phonemize', 'easypronunciation', 'ibm_watson', 'charsiu', 'openai'
            language: Код языка, для которого будут проверяться сервисы
        """
        # Инициализируем все сервисы с необходимыми параметрами
        all_services = {
            'dictionary': DictionaryService(dict_dir),
            'epitran': EpitranService(),
            'forvo': ForvoService(forvo_api_key),
            # 'google': GoogleTranslateService(),
            'wiktionary': WiktionaryService(),
            # 'g2p': G2PService(),
            'phonemize': PhonemizeService(),
            'easypronunciation': EasyPronunciationService(easypronunciation_api_key),
            'ibm_watson': IBMWatsonService(ibm_watson_api_key),
            'charsiu': CharsiuG2PService(),
            'openai': OpenAIService(openai_api_key)
        }
        
        # Проверяем реальную работоспособность сервисов
        self.available_services = {}
        for name, service in all_services.items():
            try:
                service_name = service.__class__.__name__
                logger.info(f"Проверка доступности сервиса {service_name}...")
                
                # Проверяем атрибуты, которые указывают на доступность сервиса
                service_available = True
                
                # Специфичные проверки для каждого типа сервиса
                if isinstance(service, EpitranService):
                    service_available = service.epitran_available
                    # Проверка поддержки языка при наличии параметра language
                    if service_available and language and language not in service.language_map:
                        service_available = False
                        logger.warning(f"Сервис {name} не поддерживает язык {language}")
                        
                elif isinstance(service, G2PService):
                    # G2P работает только для английского языка
                    service_available = service.g2p_available
                    if service_available and language and language != 'en':
                        service_available = False
                        logger.warning(f"Сервис {name} поддерживает только английский язык (en), а запрошен {language}")
                        
                elif isinstance(service, PhonemizeService):
                    service_available = service.phonemizer_available
                    # Проверка поддержки языка
                    if service_available and language and language not in getattr(service, 'lang_map', {'en': 'en-us'}):
                        service_available = False
                        logger.warning(f"Сервис {name} не поддерживает язык {language}")
                    # Дополнительная проверка espeak
                    if service_available:
                        try:
                            test_lang = 'en-us'
                            if language and language in getattr(service, 'lang_map', {}):
                                test_lang = service.lang_map[language]
                            # Пробуем получить транскрипцию тестового слова
                            test_transcription = service.phonemize("test", language=test_lang, backend='espeak', strip=True)
                            if test_transcription is None:
                                service_available = False
                                logger.warning(f"Сервис {name} не смог выполнить тестовую транскрипцию")
                        except Exception as e:
                            service_available = False
                            logger.warning(f"Сервис {name} не смог выполнить тестовую транскрипцию: {e}")
                            
                elif isinstance(service, CharsiuG2PService):
                    service_available = service.charsiu_available
                    # Проверка поддержки языка
                    if service_available and language:
                        supported_langs = getattr(service, 'supported_langs', [
                            'en', 'de', 'fr', 'es', 'it', 'nl', 'pt', 'ru', 'zh', 'ja', 'ko'
                        ])
                        if language not in supported_langs:
                            logger.warning(f"Язык {language} может не поддерживаться CharsiuG2P")
                            # Но всё равно пытаемся, т.к. CharsiuG2P довольно универсален
                            
                elif isinstance(service, OpenAIService):
                    service_available = service.openai_available
                    
                elif isinstance(service, ForvoService):
                    service_available = service.api_key is not None and service.api_key != ""
                    
                elif isinstance(service, EasyPronunciationService):
                    service_available = service.api_key is not None and service.api_key != ""
                    # Проверка поддержки языка
                    if service_available and language and language not in service.supported_languages:
                        service_available = False
                        logger.warning(f"Сервис {name} не поддерживает язык {language}")
                        
                elif isinstance(service, IBMWatsonService):
                    service_available = service.api_key is not None and service.api_key != ""
                    # Проверка поддержки языка
                    if service_available and language and language not in service.supported_languages:
                        service_available = False
                        logger.warning(f"Сервис {name} не поддерживает язык {language}")
                        
                # Если сервис доступен, добавляем его в список доступных
                if service_available:
                    self.available_services[name] = service
                    logger.info(f"Сервис {name} инициализирован успешно и доступен")
                else:
                    logger.warning(f"Сервис {name} инициализирован, но недоступен для использования (отсутствуют необходимые условия)")
                    
            except Exception as e:
                logger.warning(f"Сервис {name} недоступен из-за ошибки инициализации: {e}")
        
        # Создаем список активных сервисов
        if enabled_services is None:
            # Все сервисы, начиная с самых быстрых и локальных
            preferred_order = [
                'dictionary',      # Сначала пробуем локальный словарь
                'g2p',             # Затем G2P (локальный, быстрый)
                'epitran',         # Затем Epitran (локальный, быстрый)
                'phonemize',       # Затем Phonemizer (локальный, если установлен espeak-ng)
                'charsiu',         # Затем CharsiuG2P (локальный, но требует больше ресурсов)
                'wiktionary',      # Затем Wiktionary API (онлайн, но бесплатный)
                'google',          # Затем Google Translate (онлайн, но бесплатный)
                'forvo',           # Затем Forvo API (требует ключ)
                'easypronunciation', # Затем EasyPronunciation API (требует ключ)
                'ibm_watson',      # Затем IBM Watson (требует ключ)
                'openai'           # И наконец OpenAI (требует ключ, наиболее ресурсоёмкий)
            ]
            
            # Следуем предпочтительному порядку, но только для доступных сервисов
            self.services = []
            for name in preferred_order:
                if name in self.available_services:
                    self.services.append(self.available_services[name])
        else:
            # Только указанные сервисы среди доступных
            self.services = []
            
            # Dictionary сервис всегда должен быть первым для кэширования
            if 'dictionary' in enabled_services and 'dictionary' in self.available_services:
                self.services.append(self.available_services['dictionary'])
                enabled_services = [s for s in enabled_services if s != 'dictionary']  # Создаем новый список без 'dictionary'
            
            # Добавляем остальные сервисы
            for service_name in enabled_services:
                if service_name in self.available_services:
                    self.services.append(self.available_services[service_name])
                else:
                    if service_name in all_services:
                        logger.warning(f"Сервис '{service_name}' недоступен")
                    else:
                        logger.warning(f"Сервис '{service_name}' не найден")
            
            # Если dictionary был удален из списка, добавляем его для кэширования
            if not any(isinstance(service, DictionaryService) for service in self.services):
                if 'dictionary' in self.available_services:
                    self.services.insert(0, self.available_services['dictionary'])
                    logger.info("DictionaryService был добавлен автоматически для кэширования результатов")
        
        # Логируем активные сервисы
        active_services = [service.__class__.__name__ for service in self.services]
        logger.info(f"Активные сервисы: {', '.join(active_services)}")
        
        # Кэш для уже полученных транскрипций
        self.cache = {}
                    
    def _is_valid_transcription(self, transcription: str) -> bool:
        """
        Проверяет, является ли транскрипция валидной
        
        Args:
            transcription: Строка транскрипции для проверки
            
        Returns:
            True, если транскрипция валидна, иначе False
        """
        if not transcription:
            return False
        
        # Проверяем длину транскрипции
        if len(transcription) < 2:  # Минимальная длина валидной транскрипции
            return False
            
        # Проверка на наличие разметки Wiktionary и других нежелательных паттернов
        invalid_patterns = [
            r'<.*?>',               # HTML-теги
            r'\{\{.*?\}\}',         # Шаблоны вики
            r'\[\[.*?\]\]',         # Ссылки вики
            r'http[s]?://',         # URL
            r'===.*?===',           # Заголовки вики
            r'\s{3,}',              # Большое количество пробелов
            r'\n',                  # Переносы строк
            r'\|journal=',          # Паттерны из вики-цитирования
            r'\|passage=',
            r'\|trans-journal=',
            r'\|t='
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, transcription):
                return False
        
        # Проверка на наличие фонетических символов (базовый вариант)
        # Это неидеальная проверка, но поможет отсеять обычный текст
        phone_symbols = 'əɑɒɔæɛɪɨɯɵøʊʉʌθðʃʒʧʤŋɲɫɹɻʁχʀʔːˈˌ͡'
        
        # Если транскрипция содержит фонетические символы, считаем её валидной
        if any(c in transcription for c in phone_symbols):
            return True
        
        # Если транскрипция в /.../ или [...] формате и не содержит подозрительных паттернов,
        # также считаем её потенциально валидной
        if (transcription.startswith('/') and transcription.endswith('/')) or \
           (transcription.startswith('[') and transcription.endswith(']')):
            # Дополнительно проверяем, что между скобками есть содержимое
            content = transcription[1:-1].strip()
            if content and not any(re.search(pattern, content) for pattern in invalid_patterns):
                return True
                
        return False
    
    def _combine_transcriptions(self, transcriptions: List[Tuple[str, str]]) -> str:
        """
        Объединяет несколько транскрипций в одну строку
        
        Args:
            transcriptions: Список кортежей (service_name, transcription)
            
        Returns:
            Строка с объединенными транскрипциями через запятую
        """
        if not transcriptions:
            return ""
        
        # Извлекаем только транскрипции (без названий сервисов)
        trans_list = [t[1] for t in transcriptions]
        
        # Удаляем дубликаты, сохраняя порядок
        unique_trans = []
        for trans in trans_list:
            if trans not in unique_trans:
                unique_trans.append(trans)
        
        # Объединяем через запятую
        return ", ".join(unique_trans)

    def get_transcription(self, word: str, lang_code: str) -> List[Tuple[str, str]]:
        """
        Получает все возможные транскрипции от всех доступных сервисов.
        
        Args:
            word: Слово для транскрибирования
            lang_code: Код языка
            
        Returns:
            Список кортежей (service_name, transcription) со всеми найденными транскрипциями
        """
        # Проверяем кэш
        cache_key = f"{word}_{lang_code}"
        if cache_key in self.cache:
            logger.debug(f"Транскрипции для '{word}' найдены в кэше: {self.cache[cache_key]}")
            return self.cache[cache_key]
        
        # Список для хранения всех уникальных транскрипций
        all_transcriptions = []
        
        # Проходим по всем сервисам и собираем все транскрипции
        for service in self.services:
            try:
                service_name = service.__class__.__name__
                
                # Получаем транскрипцию от текущего сервиса
                start_time = time.time()
                transcription = service.get_transcription(word, lang_code)
                elapsed_time = time.time() - start_time
                
                if transcription and self._is_valid_transcription(transcription):
                    logger.info(f"Получена транскрипция для '{word}' через {service_name}: {transcription} (за {elapsed_time:.2f} сек)")
                    
                    # Добавляем в список, если такой транскрипции еще нет
                    if not any(t[1] == transcription for t in all_transcriptions):
                        all_transcriptions.append((service_name, transcription))
                    
                    # Добавляем в словарь только если это DictionaryService
                    # (Не добавляем транскрипцию от других сервисов для безопасности)
                    if isinstance(service, DictionaryService):
                        # Словарь может работать неправильно для некоторых слов,
                        # поэтому нужна дополнительная проверка
                        if self._is_valid_transcription(transcription):
                            service.add_to_dictionary(word, transcription, lang_code)
                else:
                    if transcription:
                        logger.debug(f"Сервис {service_name} вернул некорректную транскрипцию для '{word}': {transcription} (за {elapsed_time:.2f} сек)")
                    else:
                        logger.debug(f"Сервис {service_name} не смог найти транскрипцию для '{word}' (за {elapsed_time:.2f} сек)")
            
            except Exception as e:
                logger.error(f"Ошибка при получении транскрипции через {service.__class__.__name__}: {e}")
        
        # Сохраняем в кэш
        self.cache[cache_key] = all_transcriptions
        
        if not all_transcriptions:
            logger.warning(f"Не удалось получить ни одной транскрипции для '{word}' с использованием всех доступных сервисов")
        
        return all_transcriptions
    
    def get_transcription_as_string(self, word: str, lang_code: str) -> Optional[str]:
        """
        Получает объединенную строку транскрипций, разделенных запятыми
        
        Args:
            word: Слово для транскрибирования
            lang_code: Код языка
            
        Returns:
            Строка с объединенными транскрипциями или None, если транскрипции не найдены
        """
        transcriptions = self.get_transcription(word, lang_code)
        
        if transcriptions:
            # Объединяем все уникальные транскрипции через запятую
            return self._combine_transcriptions(transcriptions)
        
        return None
    