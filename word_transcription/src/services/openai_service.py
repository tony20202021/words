#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сервис транскрипции на основе OpenAI API
"""

import os
import logging
from typing import Optional

from .base import TranscriptionService

logger = logging.getLogger(__name__)

class OpenAIService(TranscriptionService):
    """Сервис транскрипции на основе OpenAI API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.openai_available = False
        
        # Проверка доступности OpenAI API
        try:
            import openai
            
            # Устанавливаем API ключ
            if self.api_key:
                openai.api_key = self.api_key
                self.openai = openai
                self.openai_available = True
                logger.info("OpenAI API успешно инициализирован")
            else:
                logger.warning("API ключ OpenAI не установлен")
                
        except ImportError as e:
            logger.warning(f"Библиотека OpenAI не установлена: {e}. Установите её с помощью: pip install openai")
        except Exception as e:
            logger.error(f"Ошибка при инициализации OpenAI API: {e}")
    
    def get_transcription(self, word: str, lang_code: str) -> Optional[str]:
        """
        Получает транскрипцию с помощью OpenAI API.
        
        Args:
            word: Слово для транскрибирования
            lang_code: Код языка
            
        Returns:
            Строка с транскрипцией или None, если API не доступен
        """
        if not self.openai_available:
            logger.warning("OpenAI API не доступен")
            return None
        
        # Соответствие кодов языков названиям языков
        lang_names = {
            'en': 'английский',
            'de': 'немецкий',
            'fr': 'французский',
            'es': 'испанский',
            'it': 'итальянский',
            'ru': 'русский',
            'nl': 'нидерландский',
            'pt': 'португальский',
            'ja': 'японский',
            'zh': 'китайский',
            'ko': 'корейский',
            'ar': 'арабский',
            'tr': 'турецкий',
            'pl': 'польский',
            'cs': 'чешский'
        }
        
        # Получаем название языка
        lang_name = lang_names.get(lang_code, lang_code)
        
        try:
            # Формируем запрос к API
            instruction = (
                f"Предоставьте транскрипцию слова '{word}' на {lang_name} языке "
                f"в соответствии с Международным фонетическим алфавитом (IPA). "
                f"Дайте только транскрипцию, без объяснений, примеров или дополнительной информации. "
                f"Используйте формат /транскрипция/."
            )
            
            logger.debug(f"Отправка запроса к OpenAI API для слова '{word}'")
            
            # Выполняем запрос к API
            response = self.openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # или другая модель
                messages=[
                    {"role": "system", "content": "Вы эксперт по фонетике и транскрипции."},
                    {"role": "user", "content": instruction}
                ],
                temperature=0.2,  # Низкая температура для более детерминированных ответов
                max_tokens=50,     # Ограничиваем длину ответа
            )
            
            # Извлекаем транскрипцию из ответа
            transcription = response.choices[0].message.content.strip()
            
            # Удаляем лишний текст, оставляем только транскрипцию между слешами
            import re
            ipa_pattern = r'/[^/]+/'
            match = re.search(ipa_pattern, transcription)
            
            if match:
                transcription = match.group(0)
                logger.debug(f"Получена транскрипция через OpenAI API для '{word}': {transcription}")
                return transcription
            else:
                # Если формат не соответствует /транскрипция/, просто добавляем слеши
                if not transcription.startswith('/'):
                    transcription = f"/{transcription}/"
                logger.debug(f"Получена и преобразована транскрипция через OpenAI API для '{word}': {transcription}")
                return transcription
            
        except Exception as e:
            logger.error(f"Ошибка при получении транскрипции через OpenAI API для '{word}': {e}")
            return None
            