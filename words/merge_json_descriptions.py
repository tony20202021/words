#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import argparse
from pathlib import Path


def load_json_file(file_path):
    """Загружает JSON файл и возвращает данные"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Ошибка: Файл {file_path} не найден")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Ошибка: Некорректный JSON в файле {file_path}: {e}")
        sys.exit(1)


def clean_numbering(text):
    """Удаляет латинскую и арабскую нумерацию в начале строки (только с точкой)"""
    import re
    
    # Паттерн для удаления нумерации:
    # - Римские цифры (I, II, III, IV, V и т.д.) 
    # - Арабские цифры (1, 2, 3 и т.д.)
    # - С любыми точками и буквами после них
    # Примеры: "I.1.", "II.3.а.", "1.2.", "3.а."
    pattern = r'^(?:[IVX]+|[0-9]+)(?:\.[0-9а-яa-z]*)*\.\s*'
    
    cleaned = re.sub(pattern, '', text, flags=re.IGNORECASE)
    return cleaned.strip()


def remove_duplicate_descriptions(descriptions):
    """Удаляет дублирующиеся описания и подстроки (без учета регистра)"""
    if not descriptions:
        return []
    
    # Приводим к нижнему регистру для сравнения, но сохраняем оригинальные строки
    cleaned = []
    lower_descriptions = []
    
    for desc in descriptions:
        # Удаляем нумерацию из строки
        cleaned_desc = clean_numbering(desc)
        desc_lower = cleaned_desc.lower().strip()
        
        # Проверяем, не является ли текущее описание подстрокой уже добавленных
        is_substring = False
        for i, existing_lower in enumerate(lower_descriptions):
            if desc_lower in existing_lower and desc_lower != existing_lower:
                # Текущее описание является подстрокой существующего - пропускаем
                is_substring = True
                break
            elif existing_lower in desc_lower and existing_lower != desc_lower:
                # Существующее описание является подстрокой текущего - заменяем
                cleaned[i] = cleaned_desc
                lower_descriptions[i] = desc_lower
                is_substring = True
                break
            elif desc_lower == existing_lower:
                # Полное совпадение - пропускаем
                is_substring = True
                break
        
        if not is_substring:
            cleaned.append(cleaned_desc)
            lower_descriptions.append(desc_lower)
    
    return cleaned


def merge_descriptions(data1, data2):
    """Объединяет описания из двух словарей данных"""
    merged_data = {}
    
    # Получаем все ключи кроме _meta
    all_keys = set(data1.keys()) | set(data2.keys())
    all_keys.discard('_meta')
    
    for key in all_keys:
        if key in data1 and key in data2:
            # Копируем запись из первого файла
            merged_data[key] = data1[key].copy()
            
            # Заменяем поле "character" на "word"
            if 'character' in merged_data[key]:
                merged_data[key]['word'] = merged_data[key].pop('character')
            
            # Объединяем описания из двух файлов в массив
            desc1 = data1[key].get('description', '')
            desc2 = data2[key].get('description', '')
            
            combined_desc = []
            if desc1:
                combined_desc.append(desc1)
            if desc2:
                combined_desc.append(desc2)
            
            # Добавляем первую строку из long_description
            long_desc = data1[key].get('long_description', [])
            if long_desc and len(long_desc) > 0:
                combined_desc.append(long_desc[0])
            
            # Удаляем дубликаты и подстроки
            merged_data[key]['description'] = remove_duplicate_descriptions(combined_desc)
                
        elif key in data1:
            # Запись есть только в первом файле
            merged_data[key] = data1[key].copy()
            
            # Заменяем поле "character" на "word"
            if 'character' in merged_data[key]:
                merged_data[key]['word'] = merged_data[key].pop('character')
            
            # Добавляем первую строку из long_description к существующему description
            desc = data1[key].get('description', '')
            long_desc = data1[key].get('long_description', [])
            
            combined_desc = []
            if desc:
                combined_desc.append(desc)
            if long_desc and len(long_desc) > 0:
                combined_desc.append(long_desc[0])
            
            if combined_desc:
                # Удаляем дубликаты и подстроки
                merged_data[key]['description'] = remove_duplicate_descriptions(combined_desc)
                
        elif key in data2:
            # Запись есть только во втором файле
            merged_data[key] = data2[key].copy()
            
            # Заменяем поле "character" на "word"
            if 'character' in merged_data[key]:
                merged_data[key]['word'] = merged_data[key].pop('character')
            
            # Добавляем первую строку из long_description к существующему description
            desc = data2[key].get('description', '')
            long_desc = data2[key].get('long_description', [])
            
            combined_desc = []
            if desc:
                combined_desc.append(desc)
            if long_desc and len(long_desc) > 0:
                combined_desc.append(long_desc[0])
            
            if combined_desc:
                # Удаляем дубликаты и подстроки
                merged_data[key]['description'] = remove_duplicate_descriptions(combined_desc)
    
    return merged_data


def main():
    parser = argparse.ArgumentParser(
        description='Объединяет описания из двух JSON файлов с одинаковой структурой'
    )
    parser.add_argument('file1', help='Путь к первому JSON файлу')
    parser.add_argument('file2', help='Путь ко второму JSON файлу')
    parser.add_argument('-o', '--output', help='Путь к выходному файлу (по умолчанию: merged_output.json)', 
                       default='merged_output.json')
    
    args = parser.parse_args()
    
    # Проверяем существование файлов
    if not Path(args.file1).exists():
        print(f"Ошибка: Файл {args.file1} не существует")
        sys.exit(1)
    
    if not Path(args.file2).exists():
        print(f"Ошибка: Файл {args.file2} не существует")
        sys.exit(1)
    
    # Загружаем данные
    print(f"Загружаем {args.file1}...")
    data1 = load_json_file(args.file1)
    
    print(f"Загружаем {args.file2}...")
    data2 = load_json_file(args.file2)
    
    # Объединяем описания
    print("Объединяем описания...")
    merged_data = merge_descriptions(data1, data2)
    
    # Сортируем ключи по числовому значению
    def numeric_sort_key(key):
        try:
            return int(key)
        except ValueError:
            return float('inf')  # Нечисловые ключи в конец
    
    sorted_keys = sorted(merged_data.keys(), key=numeric_sort_key)
    
    # Создаем отсортированный словарь
    sorted_merged_data = {key: merged_data[key] for key in sorted_keys}
    
    # Сохраняем результат
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(sorted_merged_data, f, ensure_ascii=False, indent=4)
        print(f"Результат сохранен в {args.output}")
        print(f"Обработано записей: {len(merged_data)}")
    except Exception as e:
        print(f"Ошибка при сохранении файла: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
    