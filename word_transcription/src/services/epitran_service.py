#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сервис транскрипции на основе библиотеки Epitran
"""

import logging
from typing import Dict, Optional

from .base import TranscriptionService

logger = logging.getLogger(__name__)

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
            