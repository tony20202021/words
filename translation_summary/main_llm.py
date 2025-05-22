#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Основной модуль для запуска скрипта перевода китайских слов
с использованием LLM из Hugging Face.
"""

import sys
import os
from pathlib import Path
import argparse
import logging
import json
import time

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler("translation.log")]
)
logger = logging.getLogger(__name__)

# Добавляем путь к пакету для импорта
sys.path.append(str(Path(__file__).parent))

# Импортируем модули из src
from src.llm_translator import LLMTranslator, get_available_models
from src.chinese_translator_llm import (
    load_json_file, 
    save_json_file, 
    process_chinese_dictionary_with_llm,
    batch_process_chinese_dictionary
)

def list_available_models():
    """Выводит список доступных моделей."""
    models = get_available_models()
    print("\nДоступные модели:")
    print("=" * 50)
    for key, value in models.items():
        print(f"  {key} : {value}")
    print("=" * 50)
    print("Можно также указать полное название модели из Hugging Face")
    print("Например: --model 'Qwen/Qwen2-7B-Instruct'")
    print("\n")

def main():
    """
    Основная функция для обработки файла с китайскими словами.
    Поддерживает запуск через командную строку с параметрами.
    """
    # Создаем парсер аргументов командной строки
    parser = argparse.ArgumentParser(
        description='Обработка китайских слов и создание кратких переводов с использованием LLM'
    )
    parser.add_argument('-i', '--input', help='Путь к входному JSON-файлу', required=False)
    parser.add_argument('-o', '--output', help='Путь к выходному JSON-файлу', required=False)
    parser.add_argument('-m', '--model', help='Название модели для перевода', default='qwen2-1.5b')
    parser.add_argument('-b', '--batch', help='Размер пакета для обработки', type=int, default=5)
    parser.add_argument('--max', help='Максимальное количество слов для обработки', type=int)
    parser.add_argument('--temp', help='Температура генерации (0.0-1.0)', type=float, default=0.3)
    parser.add_argument('--cpu', help='Использовать CPU вместо GPU', action='store_true')
    parser.add_argument('--list-models', help='Показать список доступных моделей', action='store_true')
    parser.add_argument('--no-description', help='Не использовать русское описание для перевода', action='store_true')    
    
    args = parser.parse_args()
    
    # Вывод списка моделей, если запрошено
    if args.list_models:
        list_available_models()
        return 0
    
    # Определяем путь к входному файлу
    if args.input:
        file_path = args.input
    else:
        file_path = input("Введите путь к JSON-файлу: ")
    
    if not os.path.exists(file_path):
        logger.error(f"Файл не найден: {file_path}")
        return 1
    
    # Загрузка данных
    data = load_json_file(file_path)
    if not data:
        logger.error("Не удалось загрузить данные")
        return 1
    
    # Инициализация переводчика с выбранной моделью
    logger.info(f"Инициализация переводчика с моделью {args.model}")
    try:
        translator = LLMTranslator(
            model_name=args.model,
            use_cuda=not args.cpu,
            temperature=args.temp
        )
    except Exception as e:
        logger.error(f"Ошибка при инициализации переводчика: {e}")
        return 1
    
    # Засекаем время выполнения
    start_time = time.time()
    
    # Обработка данных (с использованием пакетной обработки)
    logger.info("Начало обработки данных")
    try:
        processed_data = batch_process_chinese_dictionary(
            data, 
            translator, 
            batch_size=args.batch,
            max_items=args.max,
            use_description=not args.no_description  # Передаем параметр use_description
        )
    except KeyboardInterrupt:
        logger.warning("Обработка прервана пользователем")
        # Сохраняем то, что успели обработать
        processed_data = {}
    except Exception as e:
        logger.error(f"Ошибка при обработке данных: {e}")
        return 1
    
    # Время выполнения
    elapsed_time = time.time() - start_time
    logger.info(f"Время выполнения: {elapsed_time:.2f} секунд")
    
    # Определяем путь к выходному файлу
    if args.output:
        output_path = args.output
    else:
        if '.' in file_path:
            name, ext = file_path.rsplit('.', 1)
            output_path = f"{name}_llm_processed.{ext}"
        else:
            output_path = f"{file_path}_llm_processed.json"
    
    # Сохранение результата
    save_json_file(processed_data, output_path)
    logger.info(f"Обработанные данные сохранены в: {output_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
    