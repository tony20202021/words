#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сервис транскрипции на основе библиотеки phonemizer
"""

import logging
from typing import Optional

from .base import TranscriptionService

logger = logging.getLogger(__name__)

class PhonemizeService(TranscriptionService):
    """Сервис транскрипции на основе библиотеки phonemizer"""
    
    def __init__(self):
        self.phonemizer_available = False
        
        # Попытка импорта phonemizer библиотеки
        try:
            from phonemizer.phonemize import phonemize
            self.phonemize = phonemize
            self.phonemizer_available = True
            logger.info("phonemizer успешно импортирован")
        except ImportError as e:
            logger.warning(f"Библиотека phonemizer не установлена: {e}. Установите её с помощью: pip install phonemizer")
        except Exception as e:
            logger.error(f"Ошибка при импорте phonemizer: {e}")
    
    def get_transcription(self, word: str, lang_code: str) -> Optional[str]:
        """
        Получает транскрипцию с помощью phonemizer.
        
        Args:
            word: Слово для транскрибирования
            lang_code: Код языка
            
        Returns:
            Строка с транскрипцией или None, если язык не поддерживается
        """
        if not self.phonemizer_available:
            logger.warning("phonemizer не доступен")
            return None
        
        # Соответствие кодов языков ISO 639-1 к формату phonemizer
        lang_map = {
            'de': 'de',  # Немецкий
            'fr': 'fr-fr',  # Французский
            'es': 'es',  # Испанский
            'en': 'en-us',  # Английский (US)
            'it': 'it',  # Итальянский
            'nl': 'nl',  # Нидерландский
            'pl': 'pl',  # Польский
            'ru': 'ru',  # Русский
            'tr': 'tr',  # Турецкий
            'pt': 'pt-br',  # Португальский (Бразилия)
            'ja': 'ja',  # Японский
        }
        
        if lang_code not in lang_map:
            logger.warning(f"Язык {lang_code} не поддерживается phonemizer")
            return None
        
        try:
            phonemizer_lang = lang_map[lang_code]
            
            # Используем espeak-ng в качестве бэкенда
            transcription = self.phonemize(
                word, 
                language=phonemizer_lang,
                backend='espeak',
                strip=True,
                preserve_punctuation=False,
                with_stress=True
            )
            
            # Форматирование транскрипции между слешами, если её ещё нет
            transcription = transcription.strip()
            if not transcription.startswith('/'):
                transcription = f"/{transcription}/"
            
            logger.debug(f"Получена транскрипция через phonemizer для '{word}': {transcription}")
            return transcription
            
        except Exception as e:
            logger.error(f"Ошибка при получении транскрипции через phonemizer для '{word}': {e}")
            return None
            