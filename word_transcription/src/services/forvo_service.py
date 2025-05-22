#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сервис транскрипции на основе Forvo API
"""

import os
import requests
import logging
from typing import Optional

from .base import TranscriptionService

logger = logging.getLogger(__name__)

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
            