#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Основной файл для обработки транскрипции иностранных слов
"""

import logging
import argparse
import time
import os
import json
import sys
from typing import Dict, List, Optional, Tuple, Any

# Настройка пути для импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Импортируем модули проекта
from src.transcription_manager import TranscriptionManager

# Импортируем модуль для работы с Excel
try:
    # Сначала пробуем импортировать из того же каталога
    import excel_processor
    process_excel_to_json = excel_processor.process_excel_to_json
except ImportError as e:
    print("Ошибка импорта модуля excel_processor. ")
    print(e)
    try:
        # Потом пробуем импортировать как часть пакета
        from src.excel_processor import process_excel_to_json
    except ImportError as e:
        print("Ошибка импорта модуля excel_processor. ")
        print(e)
        print("Убедитесь, что он находится в том же каталоге или в src/")
        sys.exit(1)

# Настройка логирования
log_dir = os.path.join(parent_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'transcription.log')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def process_words(data: Dict[str, Dict[str, Any]], 
                 output_file,
                 n_records_save = 100,
                 transcription_manager: TranscriptionManager = None,
                 language_field: str = 'language',
                 word_field: str = 'word',
                 transcription_field: str = 'transcription',
                 all_transcriptions_field: str = 'all_transcriptions') -> Tuple[int, int]:
    """
    Обрабатывает все слова, добавляя транскрипцию.
    
    Args:
        data: Словарь словарей со словами
        transcription_manager: Менеджер транскрипций
        language_field: Имя поля с кодом языка
        word_field: Имя поля со словом
        transcription_field: Имя поля для сохранения основной транскрипции
        all_transcriptions_field: Имя поля для сохранения всех транскрипций
        
    Returns:
        Кортеж (успешно_обработано, всего_слов)
    """
    success_count = 0
    
    # Создаем контекст для определения языка
    all_words = ' '.join([word_data.get(word_field, '') for word_data in data.values() if word_field in word_data])
    
    for index, (word_id, word_data) in enumerate(data.items()):
        logger.info(f"[{index}/{len(data)}]")

        # Проверяем наличие поля со словом
        if word_field not in word_data:
            logger.warning(f"Запись {word_id} не содержит поля '{word_field}', пропускаем")
            continue
            
        word = word_data[word_field]
        
        # Пропускаем пустые слова
        if not word:
            logger.warning(f"Запись {word_id} содержит пустое слово, пропускаем")
            continue
        
        # Получаем код языка или определяем его
        # Проверяем наличие кода языка в правильном поле
        if language_field in word_data:
            lang_code = word_data[language_field]
        
        # Получаем все транскрипции от всех сервисов
        all_transcriptions = transcription_manager.get_transcription(word, lang_code)
        
        # Добавляем транскрипции в данные
        if all_transcriptions:
            # Сохраняем объединенную транскрипцию через запятую (вместо первой)
            word_data[transcription_field] = transcription_manager._combine_transcriptions(all_transcriptions)
            
            # Сохраняем все транскрипции в отдельное поле
            word_data[all_transcriptions_field] = [
                {"service": service_name, "transcription": transcription}
                for service_name, transcription in all_transcriptions
            ]
            
            success_count += 1
            
            # Если код языка был определен автоматически, сохраняем его в правильное поле
            if language_field not in word_data:
                word_data[language_field] = lang_code
        else:
            # Если транскрипции не найдены, устанавливаем пустые значения
            word_data[transcription_field] = ""
            word_data[all_transcriptions_field] = []

        if (index % n_records_save) == 0:
            # Сохранение результатов
            save_json_file(output_file, data, count_processed=index)

        # Добавляем паузу, чтобы не перегружать API
        time.sleep(0.2)
        
    return success_count, len(data)

def load_json_file(file_path: str) -> Dict[str, Dict[str, Any]]:
    """Загружает данные из JSON-файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Успешно загружено {len(data)} записей из файла {file_path}")
        return data
    except Exception as e:
        logger.error(f"Ошибка загрузки JSON из файла {file_path}: {e}")
        raise


def save_json_file(file_path: str, data: Dict[str, Dict[str, Any]], count_processed: int = None) -> None:
    """Сохраняет данные в JSON-файл"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        if count_processed is not None:
            logger.info(f"обработано {count_processed}.")

        logger.info(f"Успешно сохранено {len(data)} записей в файл {file_path}")
    except Exception as e:
        logger.error(f"Ошибка сохранения JSON в файл {file_path}: {e}")
        raise

def calculate_statistics(data):
    """
    Подсчитывает статистику транскрипций.
    
    Args:
        data: Словарь данных со словами и транскрипциями
        
    Returns:
        Словарь со статистикой
    """
    total_words = len(data)
    words_with_transcription = 0
    total_transcriptions = 0
    
    for word_id, word_data in data.items():
        # Проверяем наличие непустой транскрипции
        if 'transcription' in word_data and word_data['transcription']:
            words_with_transcription += 1
        
        # Подсчитываем общее количество транскрипций
        if 'all_transcriptions' in word_data:
            total_transcriptions += len(word_data['all_transcriptions'])
    
    # Расчет статистики
    fill_percentage = (words_with_transcription * 100 // total_words) if total_words > 0 else 0
    avg_transcriptions = (total_transcriptions // words_with_transcription) if words_with_transcription > 0 else 0
    
    return {
        'total_words': total_words,
        'words_with_transcription': words_with_transcription,
        'fill_percentage': fill_percentage,
        'total_transcriptions': total_transcriptions,
        'avg_transcriptions': avg_transcriptions
    }

def print_statistics(stats):
    """
    Выводит статистику в консоль с цветным форматированием.
    
    Args:
        stats: Словарь со статистикой
    """
    # ANSI коды цветов для вывода в терминал
    GREEN = "\033[0;32m"
    BLUE = "\033[0;34m"
    RESET = "\033[0m"
    
    print(f"{GREEN}Статистика:{RESET}")
    print(f"  {BLUE}Всего слов:{RESET} {stats['total_words']}")
    print(f"  {BLUE}Слов с транскрипцией:{RESET} {stats['words_with_transcription']}")
    print(f"  {BLUE}Процент заполнения:{RESET} {stats['fill_percentage']}%")
    print(f"  {BLUE}Всего найдено транскрипций:{RESET} {stats['total_transcriptions']}")
    
    if stats['words_with_transcription'] > 0:
        print(f"  {BLUE}Среднее количество транскрипций на слово:{RESET} {stats['avg_transcriptions']} (из имеющих транскрипцию)")
        

def main():
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description='Добавление транскрипций к иностранным словам')
    parser.add_argument('input_file', help='Путь к входному файлу (Excel или JSON)')
    parser.add_argument('--output-file', help='Путь к выходному JSON-файлу (по умолчанию: перезаписывает входной файл с другим расширением)')
    parser.add_argument('--start-index', type=int, default=0, help='Начальный индекс для обработки Excel-файла (по умолчанию: 0)')
    parser.add_argument('--end-index', type=int, help='Конечный индекс для обработки Excel-файла (по умолчанию: до конца файла)')
    parser.add_argument('--lang-field', default='language', help='Имя поля с кодом языка')
    parser.add_argument('--word-field', default='word', help='Имя поля со словом')
    parser.add_argument('--transcription-field', default='transcription', help='Имя поля для основной транскрипции')
    parser.add_argument('--all-transcriptions-field', default='all_transcriptions', help='Имя поля для всех транскрипций')
    parser.add_argument('--dict-dir', help='Путь к директории со словарями')
    parser.add_argument('--language', help='Код языка для всех слов (de, fr, es, en)')
    
    # Параметры для API ключей
    parser.add_argument('--forvo-key', help='API ключ для Forvo')
    parser.add_argument('--easypronunciation-key', help='API ключ для EasyPronunciation')
    parser.add_argument('--ibm-watson-key', help='API ключ для IBM Watson')
    parser.add_argument('--openai-key', help='API ключ для OpenAI')
    
    # Параметры для выбора сервисов
    parser.add_argument('--services', 
                      choices=['dictionary', 'epitran', 'forvo', 'google', 'wiktionary', 
                               'g2p', 'phonemize', 'easypronunciation', 'ibm_watson', 'charsiu', 'openai', 'all'],
                      nargs='+',
                      help='Сервисы для использования (по умолчанию: all)')
    
    # Флаги для включения отдельных сервисов (обратная совместимость)
    parser.add_argument('--use-epitran', action='store_true', help='Использовать Epitran для транскрипции')
    parser.add_argument('--use-wiktionary', action='store_true', help='Использовать Wiktionary API для транскрипции')
    parser.add_argument('--use-forvo', action='store_true', help='Использовать Forvo API для транскрипции')
    parser.add_argument('--use-google', action='store_true', help='Использовать Google Translate API для транскрипции')
    parser.add_argument('--use-g2p', action='store_true', help='Использовать g2p библиотеку для транскрипции')
    parser.add_argument('--use-phonemize', action='store_true', help='Использовать phonemizer для транскрипции')
    parser.add_argument('--use-easypronunciation', action='store_true', help='Использовать EasyPronunciation API для транскрипции')
    parser.add_argument('--use-ibm-watson', action='store_true', help='Использовать IBM Watson API для транскрипции')
    parser.add_argument('--use-charsiu', action='store_true', help='Использовать CharsiuG2P для транскрипции')
    parser.add_argument('--use-openai', action='store_true', help='Использовать OpenAI API для транскрипции')
    
    # Другие параметры
    parser.add_argument('--verbose', '-v', action='store_true', help='Подробный вывод')
    args = parser.parse_args()
    
    # Настройка уровня логирования
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Включен подробный режим логирования")
    
    # Определение типа входного файла
    input_file = args.input_file
    input_is_excel = input_file.endswith('.xls') or input_file.endswith('.xlsx')
    
    # Если выходной файл не указан, формируем его имя на основе входного
    if args.output_file:
        output_file = args.output_file
    else:
        # Если входной файл - Excel, формируем имя для JSON
        if input_is_excel:
            output_file = os.path.splitext(input_file)[0] + '.json'
        # Если входной файл - JSON, используем его же
        else:
            output_file = input_file
    
    try:
        # Получение данных - либо из Excel, либо из JSON
        if input_is_excel:
            logger.info(f"Обработка Excel-файла: {input_file}")
            data = process_excel_to_json(input_file, args.start_index, args.end_index, args.language)
        else:
            logger.info(f"Загрузка JSON-файла: {input_file}")
            data = load_json_file(input_file)
        
        # Определение активных сервисов
        enabled_services = None
        
        # Если указаны сервисы через --services
        if args.services:
            if 'all' in args.services:
                enabled_services = None  # Используем все сервисы
            else:
                enabled_services = args.services
        # Или если указаны отдельные флаги
        elif (args.use_epitran or args.use_wiktionary or args.use_forvo or args.use_google or 
              args.use_g2p or args.use_phonemize or args.use_easypronunciation or 
              args.use_ibm_watson or args.use_charsiu or args.use_openai):
            
            enabled_services = ['dictionary']  # Всегда включаем словарь
            
            # Добавляем выбранные сервисы
            if args.use_epitran:
                enabled_services.append('epitran')
            if args.use_wiktionary:
                enabled_services.append('wiktionary')
            if args.use_forvo:
                enabled_services.append('forvo')
            if args.use_google:
                enabled_services.append('google')
            if args.use_g2p:
                enabled_services.append('g2p')
            if args.use_phonemize:
                enabled_services.append('phonemize')
            if args.use_easypronunciation:
                enabled_services.append('easypronunciation')
            if args.use_ibm_watson:
                enabled_services.append('ibm_watson')
            if args.use_charsiu:
                enabled_services.append('charsiu')
            if args.use_openai:
                enabled_services.append('openai')
                
            logger.info(f"Используются следующие сервисы: {enabled_services}")
        
        # Создание менеджера транскрипций
        transcription_manager = TranscriptionManager(
            dict_dir=args.dict_dir,
            forvo_api_key=args.forvo_key,
            easypronunciation_api_key=args.easypronunciation_key,
            ibm_watson_api_key=args.ibm_watson_key,
            openai_api_key=args.openai_key,
            enabled_services=enabled_services,
            language=args.language,  # Передаем language для проверки совместимости сервисов
        )
        
        # Обработка слов
        success_count, total_count = process_words(
            data,
            output_file,
            n_records_save=100,
            transcription_manager=transcription_manager,
            language_field=args.lang_field,
            word_field=args.word_field,
            transcription_field=args.transcription_field,
            all_transcriptions_field=args.all_transcriptions_field
        )
        
        # Сохранение результатов
        save_json_file(output_file, data)
        
        # Вывод статистики процесса
        logger.info(f"Обработка завершена: {success_count}/{total_count} записей имеют транскрипции")
        
        # Подсчет и вывод детальной статистики
        stats = calculate_statistics(data)
        print_statistics(stats)

    except Exception as e:
        logger.error(f"Произошла ошибка во время обработки: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())
