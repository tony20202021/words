#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сервис транскрипции на основе IBM Watson Text-to-Speech API
"""

import os
import logging
from typing import Optional
import requests

from .base import TranscriptionService

logger = logging.getLogger(__name__)

class IBMWatsonService(TranscriptionService):
    """Сервис транскрипции на основе IBM Watson Text-to-Speech API"""
    
    def __init__(self, api_key: Optional[str] = None, url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("IBM_WATSON_API_KEY", "")
        # URL для IBM Watson TTS API, если не указан, используется URL по умолчанию
        self.url = url or os.environ.get("IBM_WATSON_URL", "https://api.us-south.text-to-speech.watson.cloud.ibm.com/instances/")
        self.session = requests.Session()
        
        # Проверяем, указан ли API ключ
        if not self.api_key:
            logger.warning("API ключ для IBM Watson Text-to-Speech не установлен")
        
        # Языки, поддерживаемые IBM Watson
        self.supported_languages = {
            'en': 'en-US',  # Английский (США)
            'fr': 'fr-FR',  # Французский
            'de': 'de-DE',  # Немецкий
            'es': 'es-ES',  # Испанский
            'it': 'it-IT',  # Итальянский
            'ja': 'ja-JP',  # Японский
            'ko': 'ko-KR',  # Корейский
            'pt': 'pt-BR',  # Португальский (Бразилия)
            'nl': 'nl-NL',  # Нидерландский
        }
    
    def get_transcription(self, word: str, lang_code: str) -> Optional[str]:
        """
        Получает транскрипцию через IBM Watson Text-to-Speech API.
        
        Args:
            word: Слово для транскрибирования
            lang_code: Код языка
            
        Returns:
            Строка с транскрипцией или None, если язык не поддерживается или возникла ошибка
        """
        if not self.api_key:
            logger.warning("API ключ для IBM Watson Text-to-Speech не установлен")
            return None
        
        if lang_code not in self.supported_languages:
            logger.warning(f"Язык {lang_code} не поддерживается IBM Watson API")
            return None
        
        # Получаем код языка в формате IBM Watson
        ibm_lang_code = self.supported_languages[lang_code]
        
        try:
            # Формируем URL для запроса
            url = f"{self.url}/v1/pronunciation"
            
            # Заголовки авторизации
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Параметры запроса
            params = {
                'text': word,
                'voice': ibm_lang_code,
                'format': 'ipa'
            }
            
            # Авторизация HTTP Basic
            auth = ('apikey', self.api_key)
            
            logger.debug(f"Отправка запроса к IBM Watson API: {url}")
            
            response = self.session.get(url, headers=headers, params=params, auth=auth, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"IBM Watson API вернуло код состояния {response.status_code} для '{word}'")
                return None
            
            # Парсинг ответа
            result = response.json()
            
            if 'pronunciation' in result:
                transcription = result['pronunciation']
                # Проверяем формат транскрипции
                if not transcription.startswith('/'):
                    transcription = f"/{transcription}/"
                
                logger.debug(f"Получена транскрипция через IBM Watson для '{word}': {transcription}")
                return transcription
            else:
                logger.warning(f"Транскрипция не найдена в ответе IBM Watson API для '{word}'")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при получении транскрипции через IBM Watson API для '{word}': {e}")
            return None
            