#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Базовый класс сервиса транскрипции и утилиты
"""

import logging
from typing import Optional

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
        