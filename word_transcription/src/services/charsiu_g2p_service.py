#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сервис транскрипции на основе CharsiuG2P
"""

import logging
from typing import Optional

from .base import TranscriptionService

logger = logging.getLogger(__name__)

class CharsiuG2PService(TranscriptionService):
    """Сервис транскрипции на основе библиотеки CharsiuG2P"""
    
    def __init__(self):
        self.charsiu_available = False
        self.model = None
        
        # Попытка импорта CharsiuG2P
        try:
            # Импортируем библиотеку
            from charsiu.g2p import G2P
            
            # Инициализируем модель
            try:
                self.model = G2P(use_cuda=False)  # По умолчанию без CUDA
                self.charsiu_available = True
                logger.info("CharsiuG2P успешно импортирован и инициализирован")
            except Exception as e:
                logger.error(f"Не удалось инициализировать модель CharsiuG2P: {e}")
                
        except ImportError as e:
            logger.warning(f"Библиотека CharsiuG2P не установлена: {e}. Установите её с помощью: pip install CharsiuG2P")
        except Exception as e:
            logger.error(f"Ошибка при импорте CharsiuG2P: {e}")
    
    def get_transcription(self, word: str, lang_code: str) -> Optional[str]:
        """
        Получает транскрипцию с помощью CharsiuG2P.
        
        Args:
            word: Слово для транскрибирования
            lang_code: Код языка
            
        Returns:
            Строка с транскрипцией в формате IPA или None, если модель не доступна или язык не поддерживается
        """
        if not self.charsiu_available or self.model is None:
            logger.warning("CharsiuG2P не доступен")
            return None
        
        # Список поддерживаемых языков CharsiuG2P
        # CharsiuG2P поддерживает около 100 языков, но здесь указаны только основные
        supported_langs = [
            'en', 'de', 'fr', 'es', 'it', 'nl', 'pt', 'ru', 'zh', 'ja', 'ko',
            'ar', 'cs', 'pl', 'tr', 'sv', 'fi', 'da', 'no', 'hu', 'el', 'hi'
        ]
        
        if lang_code not in supported_langs:
            logger.warning(f"Язык {lang_code} может не поддерживаться CharsiuG2P")
            # Всё равно пытаемся, так как CharsiuG2P поддерживает мультиязычную модель
        
        try:
            # Получаем транскрипцию
            result = self.model.transliterate(word, language=lang_code if lang_code != 'zh' else 'cmn')
            
            # Извлекаем транскрипцию IPA
            if isinstance(result, dict) and 'ipa' in result:
                transcription = result['ipa']
            elif isinstance(result, str):
                transcription = result
            else:
                transcription = str(result)
            
            # Форматируем транскрипцию
            if not transcription.startswith('/'):
                transcription = f"/{transcription}/"
            
            logger.debug(f"Получена транскрипция через CharsiuG2P для '{word}': {transcription}")
            return transcription
            
        except Exception as e:
            logger.error(f"Ошибка при получении транскрипции через CharsiuG2P для '{word}': {e}")
            return None
            