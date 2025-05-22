#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сервис транскрипции на основе EasyPronunciation.com API
"""

import requests
import logging
from typing import Dict, Optional

from .base import TranscriptionService

logger = logging.getLogger(__name__)

class EasyPronunciationService(TranscriptionService):
    """Сервис транскрипции на основе EasyPronunciation.com API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://easypronunciation.com/api/v1"
        self.api_key = api_key
        self.session = requests.Session()
        
        # Языки, поддерживаемые API EasyPronunciation
        self.supported_languages = {
            'en': 'english',   # Английский
            'fr': 'french',    # Французский
            'de': 'german',    # Немецкий
            'es': 'spanish',   # Испанский
            'it': 'italian',   # Итальянский
            'pt': 'portuguese', # Португальский
            'ru': 'russian',   # Русский
            'ja': 'japanese'   # Японский
        }
    
    def get_transcription(self, word: str, lang_code: str) -> Optional[str]:
        """
        Получает транскрипцию через EasyPronunciation.com API.
        
        Args:
            word: Слово для транскрибирования
            lang_code: Код языка
            
        Returns:
            Строка с транскрипцией или None, если язык не поддерживается или возникла ошибка
        """
        if not self.api_key:
            logger.warning("API ключ EasyPronunciation не установлен")
            return None
        
        if lang_code not in self.supported_languages:
            logger.warning(f"Язык {lang_code} не поддерживается EasyPronunciation API")
            return None
        
        language = self.supported_languages[lang_code]
        
        try:
            # Формируем URL для запроса
            url = f"{self.base_url}/ipa-phonetic-transcription/{language}"
            
            # Параметры запроса
            data = {
                'text': word,
                'output_type': 'json',
                'api_key': self.api_key
            }
            
            logger.debug(f"Отправка запроса к EasyPronunciation API: {url}")
            
            response = self.session.post(url, data=data, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"EasyPronunciation API вернуло код состояния {response.status_code} для '{word}'")
                return None
            
            # Парсинг ответа
            result = response.json()
            
            if 'success' in result and result['success'] and 'transcription' in result:
                transcription = result['transcription']
                # Проверяем формат транскрипции
                if not transcription.startswith('/'):
                    transcription = f"/{transcription}/"
                
                logger.debug(f"Получена транскрипция через EasyPronunciation для '{word}': {transcription}")
                return transcription
            else:
                logger.warning(f"Транскрипция не найдена в ответе EasyPronunciation API для '{word}'")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при получении транскрипции через EasyPronunciation API для '{word}': {e}")
            return None
            