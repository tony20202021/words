#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Пример использования обновленной системы транскрипции, которая собирает все варианты транскрипций
"""

import os
import sys
import json
import logging
from pprint import pprint

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
    Пример использования системы транскрипции, собирающей все варианты транскрипций
    """
    # Создаем менеджер транскрипций со всеми доступными локальными сервисами
    transcription_manager = TranscriptionManager(
        # Используем только локальные сервисы, не требующие API ключей
        enabled_services=['dictionary', 'epitran', 'g2p', 'phonemize']
    )
    
    # Примеры слов на разных языках
    test_words = [
        {"word": "hello", "lang": "en"},
        {"word": "computer", "lang": "en"},
        {"word": "schön", "lang": "de"},
        {"word": "sprechen", "lang": "de"},
        {"word": "bonjour", "lang": "fr"},
        {"word": "merci", "lang": "fr"},
        {"word": "hola", "lang": "es"},
        {"word": "gracias", "lang": "es"},
        {"word": "ciao", "lang": "it"},
        {"word": "parlare", "lang": "it"},
    ]
    
    # Результаты транскрипции
    results = {}
    
    # Обрабатываем каждое слово
    for word_data in test_words:
        word = word_data["word"]
        lang_code = word_data["lang"]
        
        logger.info(f"\nПолучение всех транскрипций для слова '{word}' ({lang_code}):")
        
        # Получаем все транскрипции
        all_transcriptions = transcription_manager.get_transcription(word, lang_code)
        
        # Выводим результаты для наглядности
        if all_transcriptions:
            logger.info(f"Найдено {len(all_transcriptions)} вариантов транскрипции:")
            for i, (service_name, transcription) in enumerate(all_transcriptions, 1):
                logger.info(f"  {i}. {service_name}: {transcription}")
        else:
            logger.warning(f"Не найдено ни одной транскрипции для '{word}'")
        
        # Сохраняем результаты
        results[word] = {
            "language": lang_code,
            "transcriptions": [
                {"service": service_name, "transcription": transcription}
                for service_name, transcription in all_transcriptions
            ]
        }
    
    # Сохраняем результаты в JSON-файл
    output_file = 'output/all_transcriptions_example.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    logger.info(f"\nРезультаты сохранены в файл: {output_file}")
    
    # Пример автоматического определения языка с получением всех транскрипций
    logger.info("\nПример автоматического определения языка:")
    unknown_words = ['hello', 'bonjour', 'hola', 'ciao', 'hallo', 'guten tag', 'merci beaucoup']
    
    # Создаем таблицу для наглядного вывода результатов
    print("\n{:<20} {:<10} {:<20} {:<30}".format(
        "Слово", "Язык", "Сервис", "Транскрипция"
    ))
    print("-" * 80)
    
    for word in unknown_words:
        # Определяем язык
        detected_lang = detect_language_advanced(word)
        
        # Получаем все транскрипции с определенным языком
        all_transcriptions = transcription_manager.get_transcription(word, detected_lang)
        
        if all_transcriptions:
            # Выводим первую транскрипцию в таблицу
            service_name, transcription = all_transcriptions[0]
            print("{:<20} {:<10} {:<20} {:<30}".format(
                word, detected_lang, service_name, transcription
            ))
            
            # Выводим остальные транскрипции, если есть
            for service_name, transcription in all_transcriptions[1:]:
                print("{:<20} {:<10} {:<20} {:<30}".format(
                    "", "", service_name, transcription
                ))
        else:
            print("{:<20} {:<10} {:<20} {:<30}".format(
                word, detected_lang, "-", "транскрипция не найдена"
            ))
    
    # Пример формата вывода в JSON
    logger.info("\nПример формата данных в JSON:")
    sample_word = "computer"
    sample_result = results.get(sample_word, {})
    print(json.dumps(sample_result, ensure_ascii=False, indent=4))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
    