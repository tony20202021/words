#!/usr/bin/env python3
import json
import os
import sys

def process_errors_in_json(input_file):
    """
    Читает JSON-файл с информацией о китайских иероглифах, находит записи с ошибками
    (пустое описание или отсутствие частоты) и перемещает их в отдельный файл с ошибками.
    
    Args:
        input_file (str): Путь к JSON-файлу с данными о китайских иероглифах
    
    Returns:
        tuple: (количество обработанных записей, количество записей с ошибками)
    """
    # Проверка существования файла
    if not os.path.exists(input_file):
        print(f"Ошибка: Файл {input_file} не найден.")
        return 0, 0
    
    # Проверка расширения файла
    if not input_file.endswith('.json'):
        print(f"Ошибка: Файл {input_file} должен иметь расширение .json")
        return 0, 0
    
    # Генерация имени файла для записей с ошибками
    error_file = f"{os.path.splitext(input_file)[0]}.errors.json"
    valid_file = f"{os.path.splitext(input_file)[0]}.valid.json"
    
    print(f"Обработка файла: {input_file}")
    print(f"Файл для записей с ошибками: {error_file}")
    print(f"Файл для записей valid: {valid_file}")
    
    try:
        # Чтение данных из JSON файла
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Проверка, что данные - это словарь
        if not isinstance(data, dict):
            print(f"Ошибка: Файл {input_file} не содержит данные в формате словаря")
            return 0, 0
        
        print(f"Всего записей в файле: {len(data)}")
        
        # Словари для хранения корректных и ошибочных записей
        valid_entries = {}
        error_entries = {}
        
        # Проверка каждой записи
        for key, entry in data.items():
            has_error = False
            
            # Проверка наличия описания
            if "description" not in entry or not entry["description"]:
                print(f"Запись {key} ({entry.get('character', 'неизвестно')}): отсутствует описание")
                has_error = True
            
            # Проверка наличия частотности
            if "frequency" not in entry or entry["frequency"] == "":
                print(f"Запись {key} ({entry.get('character', 'неизвестно')}): отсутствует частотность")
                has_error = True
            
            # Распределение по словарям
            if has_error:
                error_entries[key] = entry
            else:
                valid_entries[key] = entry
        
        # Запись ошибочных записей в отдельный файл
        if error_entries:
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(error_entries, f, ensure_ascii=False, indent=4)
            print(f"Записи с ошибками сохранены в файл: {error_file}")
        
        # только с корректными записями
        if valid_entries:
            with open(valid_file, 'w', encoding='utf-8') as f:
                json.dump(valid_entries, f, ensure_ascii=False, indent=4)
            print(f"Корректные записи сохранены в файл: {valid_file}")
        
        # Вывод статистики
        print(f"Обработка завершена.")
        print(f"Всего записей: {len(data)}")
        print(f"Корректных записей: {len(valid_entries)}")
        print(f"Записей с ошибками: {len(error_entries)}")
        
        return len(data), len(error_entries)
        
    except json.JSONDecodeError:
        print(f"Ошибка: Файл {input_file} не является корректным JSON файлом")
        return 0, 0
    except Exception as e:
        print(f"Произошла ошибка при обработке файла: {str(e)}")
        return 0, 0

if __name__ == "__main__":
    # Определение имени файла как константы
    input_file = "chinese_characters_0_1000.json"
    process_errors_in_json(input_file)