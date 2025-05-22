#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сервис транскрипции на основе Google Translate API
"""

import requests
import logging
from typing import Optional

from .base import TranscriptionService

logger = logging.getLogger(__name__)

class GoogleTranslateService(TranscriptionService):
    """Сервис транскрипции на основе Google Translate API (неофициальный)"""
    
    def __init__(self):
        self.base_url = "https://translate.googleapis.com/translate_a/single"
        self.session = requests.Session()
        
    def get_transcription(self, word: str, lang_code: str) -> Optional[str]:
        """
        Получает транскрипцию через Google Translate API.
        
        Args:
            word: Слово для транскрибирования
            lang_code: Код языка
            
        Returns:
            Строка с транскрипцией или None, если слово не найдено
        """
        try:
            params = {
                'client': 'gtx',
                # 'dt': 't',
                'dt': 'rm',  # Запрос транскрипции
                'dj': '1',   # Возврат в формате JSON
                'sl': lang_code,
                'tl': 'en',  # Перевод на английский
                'q': word
            }
            
            logger.debug(f"Отправка запроса к Google Translate API: {self.base_url} с параметрами {params}")
            
            response = self.session.get(self.base_url, params=params, timeout=5)
            
            if response.status_code != 200:
                logger.error(f"Google Translate API вернуло код состояния {response.status_code} для '{word}'")
                return None
                
            data = response.json()
            print(data)
            
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
            