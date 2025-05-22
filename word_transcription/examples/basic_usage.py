#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Пример использования системы транскрипции
"""

import os
import sys
import json
import logging

# Добавляем родительский каталог в путь поиска модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем нужные модули
from src.transcription_manager import TranscriptionManager
from src.utils.language_detector import detect_language_advanced

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """
    Пример использования системы транскрипции с различными сервисами
    """
    # Создаем менеджер транскрипций со всеми доступными локальными сервисами
    transcription_manager = TranscriptionManager(
        # Используем только локальные сервисы, не требующие API ключей
        enabled_services=['dictionary', 'epitran', 'g2p', 'phonemize']
    )
    
    # Примеры слов на разных языках
    words = {
        'en': ['hello', 'world', 'computer', 'language', 'transcription'],
        'de': ['schön', 'gut', 'sprechen', 'deutsch', 'wunderbar'],
        'fr': ['bonjour', 'merci', 'parler', 'français', 'bien'],
        'es': ['hola', 'gracias', 'hablar', 'español', 'bien'],
        'it': ['ciao', 'grazie', 'parlare', 'italiano', 'bene'],
        'nl': ['hallo', 'dank', 'spreken', 'nederlands', 'goed'],
    }
    
    # Результаты транскрипции
    results = {}
    
    # Обрабатываем каждое слово
    for lang_code, word_list in words.items():
        logger.info(f"Обработка слов на языке: {lang_code}")
        
        results[lang_code] = {}
        for word in word_list:
            # Получаем транскрипцию
            transcription = transcription_manager.get_transcription(word, lang_code)
            
            # Сохраняем результат
            results[lang_code][word] = transcription
            
            if transcription:
                logger.info(f"Слово: {word}, язык: {lang_code}, транскрипция: {transcription}")
            else:
                logger.warning(f"Не удалось найти транскрипцию для слова '{word}' ({lang_code})")
    
    # Сохраняем результаты в JSON-файл
    output_file = 'output/example_results.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    logger.info(f"Результаты сохранены в файл: {output_file}")
    
    # Пример автоматического определения языка
    unknown_words = ['hello', 'bonjour', 'hola', 'ciao', 'hallo', 'guten tag', 'merci beaucoup']
    logger.info("Пример автоматического определения языка:")
    
    for word in unknown_words:
        # Определяем язык
        detected_lang = detect_language_advanced(word)
        
        # Получаем транскрипцию с определенным языком
        transcription = transcription_manager.get_transcription(word, detected_lang)
        
        logger.info(f"Слово: {word}, определенный язык: {detected_lang}, транскрипция: {transcription}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
    