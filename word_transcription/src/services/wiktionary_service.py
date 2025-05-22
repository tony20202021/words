#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сервис транскрипции на основе Wiktionary API
"""

import requests
import logging
import re
from typing import Dict, Optional

from .base import TranscriptionService

logger = logging.getLogger(__name__)

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
            # Проверяем доступность wikitextparser
            try:
                import wikitextparser as wtp
            except ImportError:
                logger.warning("Библиотека wikitextparser не установлена. Установите её с помощью: pip install wikitextparser")
                return None
            
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
            parsed = wtp.parse(wikitext)
            
            # Поиск секции для указанного языка
            language_section = self.language_sections[lang_code]
            sections = parsed.get_sections(level=2)
            
            target_section = None
            for section in sections:
                if section.title and section.title.strip() == language_section:
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
            
            # # Если транскрипция не найдена в шаблонах, поиск в тексте
            # if not transcription:
            #     # Паттерны для поиска транскрипций
            #     ipa_patterns = [
            #         r'/[^/]+/',        # Формат /ˈsʌmθɪŋ/
            #         r'\[([^\]]+)\]',   # Формат [ˈsʌmθɪŋ]
            #         r'{{IPA\|([^}]+)}}' # Формат {{IPA|/ˈsʌmθɪŋ/}}
            #     ]
                
            #     for pattern in ipa_patterns:
            #         matches = re.findall(pattern, target_section.string)
            #         if matches:
            #             transcription = matches[0]
            #             break
            
            if transcription:
                logger.debug(f"Получена транскрипция из Wiktionary для '{word}': {transcription}")
                return transcription
            else:
                logger.warning(f"Транскрипция для слова '{word}' не найдена в Wiktionary")
                return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении транскрипции из Wiktionary для '{word}': {e}")
            return None
            