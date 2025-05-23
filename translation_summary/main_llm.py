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
from datetime import datetime

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

def setup_logging(results_dir=None, run_id=None):
    """
    Настраивает логирование для записи в файл в каталоге results.
    
    Args:
        results_dir (str): Базовый каталог для результатов
        run_id (str): Идентификатор текущего запуска
    """
    # Определяем каталог для логов
    if results_dir and run_id:
        log_dir = Path(results_dir) / f"run_{run_id}"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "translation.log"
    else:
        # Создаем каталог на основе текущего времени
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = Path("results") / f"run_{timestamp}"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "translation.log"
    
    # Очищаем существующие обработчики
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Настраиваем новые обработчики
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Вывод в консоль
            logging.FileHandler(log_file, encoding='utf-8')  # Запись в файл
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Логирование настроено. Файл логов: {log_file}")
    
    return str(log_file), str(log_dir)

def detect_run_context():
    """
    Определяет контекст запуска (из run_models.sh или напрямую).
    
    Returns:
        tuple: (results_dir, run_id) или (None, None) если запуск напрямую
    """
    # Проверяем переменные окружения, которые может установить run_models.sh
    run_dir = os.environ.get('RUN_DIR')
    if run_dir:
        # Запуск из run_models.sh
        run_path = Path(run_dir)
        results_dir = str(run_path.parent)
        run_id = run_path.name.replace('run_', '')
        return results_dir, run_id
    
    return None, None

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
    parser.add_argument('--results-dir', help='Каталог для результатов (автоопределение)')
    
    args = parser.parse_args()
    
    # Вывод списка моделей, если запрошено (без настройки логирования)
    if args.list_models:
        list_available_models()
        return 0
    
    # Определяем контекст запуска
    results_dir, run_id = detect_run_context()
    if args.results_dir:
        results_dir = args.results_dir
    
    # Настраиваем логирование
    log_file, log_dir = setup_logging(results_dir, run_id)
    logger = logging.getLogger(__name__)
    
    logger.info("="*50)
    logger.info("Запуск переводчика китайских слов с использованием LLM")
    logger.info(f"Модель: {args.model}")
    logger.info(f"Режим: {'без описания' if args.no_description else 'с описанием'}")
    logger.info(f"Каталог логов: {log_dir}")
    logger.info("="*50)
    
    # Определяем путь к входному файлу
    if args.input:
        file_path = args.input
    else:
        file_path = input("Введите путь к JSON-файлу: ")
    
    if not os.path.exists(file_path):
        logger.error(f"Файл не найден: {file_path}")
        return 1
    
    logger.info(f"Входной файл: {file_path}")
    
    # Загрузка данных
    data = load_json_file(file_path)
    if not data:
        logger.error("Не удалось загрузить данные")
        return 1
    
    logger.info(f"Загружено записей: {len(data)}")
    
    # Инициализация переводчика с выбранной моделью
    logger.info(f"Инициализация переводчика с моделью {args.model}")
    try:
        translator = LLMTranslator(
            model_name=args.model,
            use_cuda=not args.cpu,
            temperature=args.temp
        )
        logger.info("Переводчик успешно инициализирован")
        
        # Добавим отладочную информацию
        logger.debug(f"Тип модели: {translator.model_type}")
        logger.debug(f"Имеет openai_handler: {hasattr(translator, 'openai_handler')}")
        if hasattr(translator, 'openai_handler'):
            logger.debug(f"openai_handler не None: {translator.openai_handler is not None}")
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации переводчика: {e}")
        import traceback
        logger.error(f"Полная трассировка: {traceback.format_exc()}")
        return 1
    
    # Засекаем время выполнения
    start_time = time.time()
    
    # Обработка данных (с использованием пакетной обработки)
    logger.info("Начало обработки данных")
    logger.info(f"Размер пакета: {args.batch}")
    logger.info(f"Максимальное количество элементов: {args.max if args.max else 'все'}")
    
    try:
        processed_data = batch_process_chinese_dictionary(
            data, 
            translator, 
            batch_size=args.batch,
            max_items=args.max,
            use_description=not args.no_description  # Передаем параметр use_description
        )
        logger.info(f"Успешно обработано записей: {len(processed_data)}")
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
    
    logger.info(f"Сохранение результатов в: {output_path}")
    
    # Сохранение результата
    save_json_file(processed_data, output_path)
    logger.info(f"Обработанные данные сохранены в: {output_path}")
    
    logger.info("="*50)
    logger.info("Выполнение завершено успешно")
    logger.info(f"Файл логов: {log_file}")
    logger.info("="*50)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
    