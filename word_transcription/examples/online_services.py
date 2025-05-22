#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Пример использования системы транскрипции с различными онлайн-сервисами
"""

import os
import sys
import json
import logging
import argparse

# Добавляем родительский каталог в путь поиска модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем нужные модули
from src.transcription_manager import TranscriptionManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description='Пример использования онлайн-сервисов для транскрипции')
    parser.add_argument('--forvo-key', help='API ключ для Forvo')
    parser.add_argument('--easypronunciation-key', help='API ключ для EasyPronunciation')
    parser.add_argument('--ibm-watson-key', help='API ключ для IBM Watson')
    parser.add_argument('--openai-key', help='API ключ для OpenAI')
    args = parser.parse_args()
    
    # Создаем список сервисов в зависимости от наличия API ключей
    enabled_services = ['dictionary']  # Всегда включаем словарь
    
    if args.forvo_key:
        enabled_services.append('forvo')
        logger.info("Forvo API включен")
    
    if args.easypronunciation_key:
        enabled_services.append('easypronunciation')
        logger.info("EasyPronunciation API включен")
    
    if args.ibm_watson_key:
        enabled_services.append('ibm_watson')
        logger.info("IBM Watson API включен")
    
    if args.openai_key:
        enabled_services.append('openai')
        logger.info("OpenAI API включен")
    
    # Добавляем бесплатные онлайн-сервисы
    enabled_services.extend(['wiktionary', 'google'])
    
    # Включаем локальные сервисы
    enabled_services.extend(['epitran', 'g2p', 'phonemize'])
    
    # Убираем дубликаты и сортируем список
    enabled_services = sorted(list(set(enabled_services)))
    
    logger.info(f"Используемые сервисы: {', '.join(enabled_services)}")
    
    # Создаем менеджер транскрипций
    transcription_manager = TranscriptionManager(
        forvo_api_key=args.forvo_key,
        easypronunciation_api_key=args.easypronunciation_key,
        ibm_watson_api_key=args.ibm_watson_key,
        openai_api_key=args.openai_key,
        enabled_services=enabled_services
    )
    
    # Сложные слова для транскрипции
    complex_words = [
        {'word': 'pneumonoultramicroscopicsilicovolcanoconiosis', 'lang': 'en'},
        {'word': 'Rindfleischetikettierungsüberwachungsaufgabenübertragungsgesetz', 'lang': 'de'},
        {'word': 'anticonstitutionnellement', 'lang': 'fr'},
        {'word': 'esternocleidomastoideo', 'lang': 'es'},
        {'word': 'precipitevolissimevolmente', 'lang': 'it'},
    ]
    
    # Результаты транскрипции
    results = {}
    
    # Обрабатываем каждое слово
    for word_data in complex_words:
        word = word_data['word']
        lang_code = word_data['lang']
        
        logger.info(f"Запрос транскрипции для: {word} ({lang_code})")
        
        # Получаем транскрипцию
        transcription = transcription_manager.get_transcription(word, lang_code)
        
        # Сохраняем результат
        results[word] = {
            'language': lang_code,
            'transcription': transcription
        }
        
        if transcription:
            logger.info(f"Получена транскрипция: {transcription}")
        else:
            logger.warning(f"Не удалось найти транскрипцию для слова '{word}' ({lang_code})")
    
    # Сохраняем результаты в JSON-файл
    output_file = 'output/online_services_results.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    logger.info(f"Результаты сохранены в файл: {output_file}")
    
    # Выводим сводку результатов
    logger.info("\nСводка результатов:")
    for word, data in results.items():
        transcription = data['transcription'] or 'НЕ НАЙДЕНО'
        logger.info(f"{word} ({data['language']}): {transcription}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
    