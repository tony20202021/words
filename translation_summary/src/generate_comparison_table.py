#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для создания сравнительной таблицы результатов перевода
из нескольких JSON-файлов с результатами.
"""

import json
import os
import argparse
import glob
import csv
from datetime import datetime

def load_json_file(file_path):
    """Загружает JSON из файла."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка при чтении файла {file_path}: {e}")
        return None

def truncate_text(text, max_length=50):
    """Сокращает текст до указанной длины с добавлением '...'."""
    if isinstance(text, str) and len(text) > max_length:
        return text[:max_length] + '...'
    return text

def escape_markdown(text):
    """Экранирует специальные символы Markdown."""
    if not isinstance(text, str):
        return str(text)
    # Экранируем символы: | * _ # [ ] ( ) < > \ ` 
    chars_to_escape = r'\|*_#[]()<>`'
    for char in chars_to_escape:
        text = text.replace(char, '\\' + char)
    return text

def save_csv_file(translations_data, time_data, output_file):
    """
    Сохраняет данные переводов и времени выполнения в CSV файл.
    
    Args:
        translations_data (list): Список словарей с данными переводов
        time_data (list): Список словарей с данными времени выполнения
        output_file (str): Путь к CSV файлу
    """
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            # Заголовки для CSV
            fieldnames = ['Иероглиф', 'Исходное_описание', 'Модель', 'Режим', 'Перевод', 'Время_выполнения']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Записываем заголовки
            writer.writeheader()
            
            # Создаем словарь времени выполнения для быстрого поиска
            time_dict = {}
            for time_item in time_data:
                key = f"{time_item['model']}_{time_item['mode']}"
                time_dict[key] = time_item['time']
            
            # Записываем данные переводов
            for item in translations_data:
                # Ищем соответствующее время выполнения
                time_key = f"{item['model']}_{item['mode']}"
                execution_time = time_dict.get(time_key, 'N/A')
                
                writer.writerow({
                    'Иероглиф': item['character'],
                    'Исходное_описание': item['orig_desc'],
                    'Модель': item['model'],
                    'Режим': item['mode'],
                    'Перевод': item['short_desc'],
                    'Время_выполнения': execution_time
                })
                
        print(f"CSV файл успешно сохранен: {output_file}")
        return True
    except Exception as e:
        print(f"Ошибка при сохранении CSV файла: {e}")
        return False

def generate_comparison_table(results_dir, output_file, input_file, max_items):
    """
    Создает сравнительную таблицу из результатов и сохраняет в markdown файл.
    
    Args:
        results_dir (str): Директория с результатами
        output_file (str): Файл для сохранения таблицы
        input_file (str): Исходный файл с данными
        max_items (int): Максимальное количество обработанных элементов
    """
    # Находим все файлы результатов в указанной директории
    result_files = glob.glob(f"{results_dir}/results_*.json")
    
    if not result_files:
        print(f"Не найдены файлы результатов в директории {results_dir}")
        return False
    
    # Структура для хранения всех переводов
    all_translations = []
    time_results = []
    
    # Загружаем все результаты
    for file_path in result_files:
        data = load_json_file(file_path)
        if not data:
            continue
            
        meta = data.get('_meta', {})
        model = meta.get('model', 'Неизвестно')
        mode = meta.get('mode', 'Неизвестно')
        
        # Добавляем информацию о времени выполнения
        if '_meta' in data:
            time_results.append({
                'model': model,
                'mode': mode,
                'time': meta.get('processing_time', 'N/A')
            })
        
        # Обрабатываем каждое слово
        for key, entry in data.items():
            if key == '_meta':
                continue
                
            # Получаем данные
            character = entry.get('character', '')
            character_display = truncate_text(character)

            short_desc = entry.get('description', '')
            short_desc_display = truncate_text(short_desc)
            
            # Берем только первое описание из исходного массива
            long_desc = entry.get('long_description', [])
            orig_desc = long_desc[0] if isinstance(long_desc, list) and long_desc else ''
            
            # Укорачиваем описание для отображения
            orig_desc_display = truncate_text(orig_desc)
            
            # Добавляем информацию в список (сохраняем полные тексты для CSV)
            all_translations.append({
                'character': character,  # Полный текст для CSV
                'character_display': character_display,  # Обрезанный для markdown
                'orig_desc': orig_desc,  # Полный текст для CSV
                'orig_desc_display': orig_desc_display,  # Обрезанный для markdown
                'model': model,
                'mode': mode,
                'short_desc': short_desc,  # Полный текст для CSV
                'short_desc_display': short_desc_display  # Обрезанный для markdown
            })
    
    # Сортируем 
    all_translations.sort(key=lambda x: (x['model'], x['character'], x['mode']))
    time_results.sort(key=lambda x: (x['model'], x['mode']))
    
    # Создаем CSV файл
    csv_output_file = output_file.replace('.md', '.csv')
    save_csv_file(all_translations, time_results, csv_output_file)
    
    # Начинаем создавать markdown файл
    with open(output_file, 'w', encoding='utf-8') as md_file:
        # Заголовок
        md_file.write("# Сравнение результатов моделей перевода\n")
        md_file.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Информация о запуске
        md_file.write("## Информация о запуске\n")
        md_file.write(f"- Входной файл: {input_file}\n")
        md_file.write(f"- Максимальное количество слов: {max_items}\n")
        md_file.write(f"- Количество файлов результатов: {len(result_files)}\n")
        md_file.write(f"- Директория результатов: {os.path.abspath(results_dir)}\n")
        md_file.write(f"- CSV файл с данными: {os.path.basename(csv_output_file)}\n\n")
        
        # Собираем данные для таблицы переводов
        md_file.write("## Сравнительная таблица переводов\n\n")
        md_file.write("| Иероглиф | Исходное описание                       | Модель                | Режим       | Перевод                 |\n")
        md_file.write("|----------|-----------------------------------------|-----------------------|-------------|-------------------------|\n")
        
        # Записываем отсортированные результаты в таблицу (используем обрезанные версии)
        for item in all_translations:
            md_file.write(f"| {item['character_display']} | {escape_markdown(item['orig_desc_display'])} | {item['model']} | {item['mode']} | {escape_markdown(item['short_desc_display'])} |\n")
        
        # Таблица времени выполнения
        md_file.write("\n## Время выполнения\n\n")
        md_file.write("| Модель | Режим | Время (сек) |\n")
        md_file.write("|--------|-------|-------------|\n")
        
        # Записываем результаты времени выполнения
        for result in time_results:
            md_file.write(f"| {result['model']} | {result['mode']} | {result['time']} |\n")
        
        # Добавляем секцию для анализа результатов
        md_file.write("\n## Анализ результатов\n\n")
        md_file.write("### Сравнение режимов (с описанием vs без описания)\n\n")
        md_file.write("Этот раздел содержит сравнительный анализ качества переводов при использовании русских описаний и без них.\n\n")
        
        # Находим примеры для сравнения (одинаковые иероглифы в разных режимах)
        examples = {}
        for item in all_translations:
            char = item['character']
            model = item['model']
            mode = item['mode']
            trans = item['short_desc']
            
            if char not in examples:
                examples[char] = {}
            
            if model not in examples[char]:
                examples[char][model] = {}
            
            examples[char][model][mode] = trans
        
        # Выбираем до 5 примеров, где есть переводы в обоих режимах
        comparison_examples = []
        for char, models in examples.items():
            for model, modes in models.items():
                if len(modes) == 2:  # Есть оба режима
                    comparison_examples.append({
                        'character': char,
                        'model': model,
                        'with_desc': modes.get('с описанием', 'Н/Д'),
                        'without_desc': modes.get('no', 'Н/Д')
                    })
                    if len(comparison_examples) >= 5:
                        break
            if len(comparison_examples) >= 5:
                break
        
        # Показываем примеры сравнения
        if comparison_examples:
            md_file.write("#### Примеры сравнения переводов:\n\n")
            md_file.write("| Иероглиф | Модель | С описанием | Без описания |\n")
            md_file.write("|----------|--------|-------------|-------------|\n")
            
            for example in comparison_examples:
                md_file.write(f"| {example['character']} | {example['model']} | {escape_markdown(example['with_desc'])} | {escape_markdown(example['without_desc'])} |\n")
        
        # Добавляем информацию о CSV файле
        md_file.write(f"\n## Экспорт данных\n\n")
        md_file.write(f"Полная таблица с результатами переводов доступна в CSV формате: `{os.path.basename(csv_output_file)}`\n\n")
        md_file.write("CSV файл содержит:\n")
        md_file.write("- Полные тексты переводов (без сокращений)\n")
        md_file.write("- Полные исходные описания\n")
        md_file.write("- Время выполнения для каждой модели и режима\n")
        md_file.write("- Данные в удобном для анализа формате\n")
    
    print(f"Сравнительная таблица успешно создана: {output_file}")
    return True

def main():
    """Основная функция для запуска из командной строки."""
    parser = argparse.ArgumentParser(
        description="Создание сравнительной таблицы результатов перевода"
    )
    parser.add_argument('--results-dir', help='Директория с результатами', required=True)
    parser.add_argument('--output', help='Файл для сохранения таблицы', required=True)
    parser.add_argument('--input-file', help='Исходный файл с данными', required=True)
    parser.add_argument('--max-items', help='Максимальное количество обработанных элементов', 
                        type=int, default=30)
    
    args = parser.parse_args()
    
    generate_comparison_table(
        args.results_dir, 
        args.output, 
        args.input_file, 
        args.max_items
    )

if __name__ == "__main__":
    main()