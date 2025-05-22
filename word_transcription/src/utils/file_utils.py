#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Утилиты для работы с файлами
"""

import os
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

def ensure_dir_exists(path: str) -> None:
    """
    Убеждается, что директория существует, создавая её при необходимости.
    
    Args:
        path: Путь к директории
    """
    if not os.path.exists(path):
        try:
            os.makedirs(path)
            logger.debug(f"Создана директория: {path}")
        except Exception as e:
            logger.error(f"Ошибка при создании директории {path}: {e}")
            raise

def load_json(file_path: str, default: Optional[Any] = None) -> Any:
    """
    Загружает данные из JSON-файла.
    
    Args:
        file_path: Путь к JSON-файлу
        default: Значение по умолчанию, если файл не найден или произошла ошибка
        
    Returns:
        Загруженные данные или default, если файл не найден или произошла ошибка
    """
    if not os.path.exists(file_path):
        logger.warning(f"Файл {file_path} не найден, возвращается значение по умолчанию")
        return default
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.debug(f"Загружены данные из файла {file_path}")
        return data
    except Exception as e:
        logger.error(f"Ошибка при загрузке JSON из файла {file_path}: {e}")
        if default is not None:
            return default
        raise

def save_json(file_path: str, data: Any, ensure_dir: bool = True) -> None:
    """
    Сохраняет данные в JSON-файл.
    
    Args:
        file_path: Путь к JSON-файлу
        data: Данные для сохранения
        ensure_dir: Если True, убеждается что директория существует
    """
    if ensure_dir:
        directory = os.path.dirname(file_path)
        if directory:
            ensure_dir_exists(directory)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.debug(f"Данные сохранены в файл {file_path}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении JSON в файл {file_path}: {e}")
        raise

def get_file_extension(file_path: str) -> str:
    """
    Получает расширение файла.
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        Расширение файла (без точки)
    """
    return os.path.splitext(file_path)[1][1:].lower()

def change_file_extension(file_path: str, new_extension: str) -> str:
    """
    Изменяет расширение файла.
    
    Args:
        file_path: Путь к файлу
        new_extension: Новое расширение (без точки)
        
    Returns:
        Путь к файлу с новым расширением
    """
    base = os.path.splitext(file_path)[0]
    return f"{base}.{new_extension.lstrip('.')}"

def list_files(directory: str, extension: Optional[str] = None) -> list:
    """
    Возвращает список файлов в директории.
    
    Args:
        directory: Путь к директории
        extension: Расширение файлов для фильтрации (без точки)
        
    Returns:
        Список файлов в директории
    """
    if not os.path.exists(directory) or not os.path.isdir(directory):
        logger.warning(f"Директория {directory} не существует или не является директорией")
        return []
    
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    
    if extension:
        ext = extension.lstrip('.')
        files = [f for f in files if get_file_extension(f) == ext]
    
    return files
    