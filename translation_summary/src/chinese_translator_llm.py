#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для создания кратких осмысленных переводов китайских слов
на основе их подробных русских описаний в JSON-файле.
Использует языковые модели из Hugging Face.
"""

import json
import re
import os
import sys
from pathlib import Path
import logging
from tqdm import tqdm

# Получаем logger, но не настраиваем базовую конфигурацию
logger = logging.getLogger(__name__)

def load_json_file(file_path):
    """
    Загружает данные из JSON-файла.
    
    Args:
        file_path (str): Путь к JSON-файлу
        
    Returns:
        dict: Данные из JSON-файла
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            logger.info(f"Успешно загружен файл: {file_path}")
            return data
    except Exception as e:
        logger.error(f"Ошибка при чтении файла {file_path}: {e}")
        return None

def save_json_file(data, file_path):
    """
    Сохраняет данные в JSON-файл.
    
    Args:
        data (dict): Данные для сохранения
        file_path (str): Путь к файлу для сохранения
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        logger.info(f"Файл успешно сохранен: {file_path}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении файла {file_path}: {e}")

def create_short_description_with_llm(translator, character, descriptions, use_description=True):
    """
    Создает краткое осмысленное описание для китайского слова
    с использованием языковой модели.
    
    Args:
        translator: Экземпляр класса LLMTranslator
        character (str): Китайское слово/иероглиф
        descriptions (list): Список строк с описаниями
        use_description (bool): Использовать ли описание при переводе
        
    Returns:
        str: Краткое описание
    """
    # Используем языковую модель для генерации перевода
    translation = translator.translate(character, descriptions, use_description)
    logger.debug(f"Перевод для {character}: {translation}")
    return translation

def process_chinese_dictionary_with_llm(data, translator, max_items=None, use_description=True):
    """
    Обрабатывает словарь китайских слов с использованием языковой модели.
    
    Args:
        data (dict): Словарь с данными о китайских словах
        translator: Экземпляр класса LLMTranslator
        max_items (int, optional): Максимальное количество элементов для обработки
        use_description (bool): Использовать ли описание при переводе
        
    Returns:
        dict: Обновленный словарь
    """
    result = {}
    
    # Ограничиваем количество элементов для обработки, если указано
    items = list(data.items())
    if max_items and max_items > 0:
        items = items[:max_items]
        logger.info(f"Ограничиваем обработку до {max_items} элементов")
    
    logger.info(f"Начинаем обработку {len(items)} элементов")
    
    # Используем tqdm для отображения прогресса
    for key, entry in tqdm(items, desc="Обработка словаря"):
        # Проверка наличия необходимых полей
        if 'character' not in entry or 'description' not in entry:
            logger.warning(f"Пропуск записи {key}: отсутствуют необходимые поля")
            continue
        
        # Создание новой записи
        new_entry = {
            'character': entry['character'],
            'long_description': entry['description'],
        }
        
        # Копирование других полей, если они есть
        for field, value in entry.items():
            if field not in ['character', 'description']:
                new_entry[field] = value
        
        # Создание краткого описания с помощью LLM
        logger.debug(f"Обработка {entry['character']}")
        new_entry['description'] = create_short_description_with_llm(
            translator, 
            entry['character'], 
            entry['description'],
            use_description
        )
        
        result[key] = new_entry
    
    logger.info(f"Обработка завершена. Обработано {len(result)} элементов")
    return result

def batch_process_chinese_dictionary(data, translator, batch_size=10, max_items=None, use_description=True):
    """
    Обрабатывает словарь китайских слов в пакетном режиме.
    
    Args:
        data (dict): Словарь с данными о китайских словах
        translator: Экземпляр класса LLMTranslator
        batch_size (int): Размер пакета для обработки
        max_items (int, optional): Максимальное количество элементов для обработки
        use_description (bool): Использовать ли описание при переводе
        
    Returns:
        dict: Обновленный словарь
    """
    result = {}
    
    # Ограничиваем количество элементов для обработки, если указано
    items = list(data.items())
    if max_items and max_items > 0:
        items = items[:max_items]
        logger.info(f"Ограничиваем обработку до {max_items} элементов")
    
    # Подготавливаем данные для пакетной обработки
    batch_items = []
    for key, entry in items:
        if 'character' in entry and 'description' in entry:
            batch_items.append((key, entry['character'], entry['description']))
        else:
            logger.warning(f"Пропуск записи {key}: отсутствуют необходимые поля")
    
    # Разбиваем на пакеты
    total_batches = (len(batch_items) + batch_size - 1) // batch_size
    logger.info(f"Начинаем пакетную обработку: {len(batch_items)} элементов в {total_batches} пакетах")
    
    for batch_index in range(total_batches):
        start_idx = batch_index * batch_size
        end_idx = min(start_idx + batch_size, len(batch_items))
        current_batch = batch_items[start_idx:end_idx]
        
        logger.info(f"Обработка пакета {batch_index+1}/{total_batches} ({len(current_batch)} элементов)")
        
        # Подготавливаем данные для переводчика
        translator_inputs = [(item[1], item[2]) for item in current_batch]
        
        # Выполняем пакетную обработку
        translations = translator.batch_translate(translator_inputs, batch_size, use_description)
                
        # Создаем новые записи с переводами
        for i, (key, character, descriptions) in enumerate(current_batch):
            entry = data[key]
            new_entry = {
                'character': character,
                'long_description': descriptions,
            }
            
            # Копирование других полей, если они есть
            for field, value in entry.items():
                if field not in ['character', 'description']:
                    new_entry[field] = value
            
            # Устанавливаем перевод
            new_entry['description'] = translations[i]
            
            result[key] = new_entry
            logger.debug(f"Обработан элемент {key}: {character} -> {translations[i]}")
    
    logger.info(f"Пакетная обработка завершена. Обработано {len(result)} элементов")
    
    # Выводим статистику, если доступна
    try:
        if hasattr(translator, 'print_statistics') and callable(getattr(translator, 'print_statistics', None)):
            translator.print_statistics()
        else:
            logger.info("Метод print_statistics недоступен")
    except Exception as e:
        logger.debug(f"Не удалось вывести статистику: {e}")
    
    return result
