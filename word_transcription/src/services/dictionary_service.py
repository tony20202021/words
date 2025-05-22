#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сервис транскрипции на основе локальных словарей
"""

import os
import json
import logging
from typing import Dict, Optional

from .base import TranscriptionService

logger = logging.getLogger(__name__)

class DictionaryService(TranscriptionService):
    """Сервис транскрипции на основе локальных словарей"""
    
    def __init__(self, dict_dir: Optional[str] = None):
        # Путь к директории с локальными словарями
        if dict_dir is None:
            # Получаем текущую директорию
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            # Ищем словари в стандартных местах
            possible_dirs = [
                os.path.join(current_dir, 'data', 'dictionaries'),  # В каталоге data/dictionaries проекта
                'data/dictionaries'  # Относительный путь
            ]
            
            for path in possible_dirs:
                if os.path.exists(path) and os.path.isdir(path):
                    self.dict_dir = path
                    break
            else:
                # Если директория не найдена, используем путь по умолчанию (будет выдано предупреждение)
                self.dict_dir = os.path.join(current_dir, 'data', 'dictionaries')
                logger.warning(f"Директория словарей не найдена. Будет использоваться путь по умолчанию: {self.dict_dir}")
        else:
            self.dict_dir = dict_dir
        
        self.dictionaries = {}  # Словари для разных языков
        self.load_dictionaries()
        
    def load_dictionaries(self) -> None:
        """Загружает словари из файлов"""
        try:
            # Создаем директорию для словарей, если она не существует
            os.makedirs(self.dict_dir, exist_ok=True)
            
            # Словари для основных языков
            dict_files = {
                'de': 'de_dict.json',  # Немецкий
                'fr': 'fr_dict.json',  # Французский
                'es': 'es_dict.json',  # Испанский
                'en': 'en_dict.json'   # Английский
            }
            
            for lang_code, filename in dict_files.items():
                dict_path = os.path.join(self.dict_dir, filename)
                
                if os.path.exists(dict_path):
                    with open(dict_path, 'r', encoding='utf-8') as f:
                        self.dictionaries[lang_code] = json.load(f)
                    logger.info(f"Загружен словарь {filename} с {len(self.dictionaries[lang_code])} словами")
                else:
                    # Создаем пустой словарь, если файл не существует
                    self.dictionaries[lang_code] = {}
                    logger.warning(f"Словарь {filename} не найден, создан пустой словарь")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки словарей: {e}")
            
    def get_transcription(self, word: str, lang_code: str) -> Optional[str]:
        """
        Получает транскрипцию из локального словаря.
        
        Args:
            word: Слово для транскрибирования
            lang_code: Код языка
            
        Returns:
            Строка с транскрипцией или None, если слово не найдено
        """
        if lang_code not in self.dictionaries:
            logger.warning(f"Словарь для языка {lang_code} не загружен")
            return None
            
        # Приводим слово к нижнему регистру для поиска в словаре
        word_lower = word.lower()
        
        # Ищем слово в словаре
        if word_lower in self.dictionaries[lang_code]:
            transcription = self.dictionaries[lang_code][word_lower]
            logger.debug(f"Найдена транскрипция в словаре для '{word}': {transcription}")
            return transcription
            
        logger.debug(f"Слово '{word}' не найдено в словаре для языка {lang_code}")
        return None
        
    def add_to_dictionary(self, word: str, transcription: str, lang_code: str) -> None:
        """
        Добавляет слово и его транскрипцию в словарь.
        
        Args:
            word: Слово
            transcription: Транскрипция
            lang_code: Код языка
        """
        if lang_code not in self.dictionaries:
            self.dictionaries[lang_code] = {}
            
        word_lower = word.lower()
        self.dictionaries[lang_code][word_lower] = transcription
        
        # Сохраняем обновленный словарь
        try:
            dict_path = os.path.join(self.dict_dir, f"{lang_code}_dict.json")
            with open(dict_path, 'w', encoding='utf-8') as f:
                json.dump(self.dictionaries[lang_code], f, ensure_ascii=False, indent=4)
            logger.debug(f"Словарь {lang_code} обновлен и сохранен")
        except Exception as e:
            logger.error(f"Ошибка сохранения словаря {lang_code}: {e}")
            