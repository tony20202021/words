import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional

# Настройка логирования
logger = logging.getLogger(__name__)

def ensure_dir_exists(dir_path: str) -> None:
    """Создает директорию, если она не существует"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        logger.info(f"Создана директория: {dir_path}")

def load_json_file(file_path: str, default: Optional[Any] = None) -> Any:
    """
    Загружает данные из JSON-файла.
    
    Args:
        file_path: Путь к файлу
        default: Значение по умолчанию, если файл не существует или возникла ошибка
        
    Returns:
        Данные из файла или значение по умолчанию
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"Файл {file_path} не найден. Возвращается значение по умолчанию.")
            return default
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.debug(f"Успешно загружен файл {file_path}")
            return data
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла {file_path}: {str(e)}")
        return default

def save_json_file(file_path: str, data: Any, ensure_dir: bool = True) -> bool:
    """
    Сохраняет данные в JSON-файл.
    
    Args:
        file_path: Путь к файлу
        data: Данные для сохранения
        ensure_dir: Если True, создает директорию при необходимости
        
    Returns:
        True, если сохранение успешно, иначе False
    """
    try:
        # Создать директорию, если она не существует
        if ensure_dir:
            dir_path = os.path.dirname(file_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
                logger.debug(f"Создана директория: {dir_path}")
                
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            logger.debug(f"Успешно сохранен файл {file_path}")
            return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении файла {file_path}: {str(e)}")
        return False

def get_data_dir() -> str:
    """
    Возвращает путь к директории с данными.
    
    Returns:
        Путь к директории с данными
    """
    # Определяем путь к директории проекта
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    data_dir = os.path.join(project_dir, "data")
    
    # Создаем директорию, если она не существует
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        logger.debug(f"Создана директория для данных: {data_dir}")
        
    return data_dir

def get_dict_dir() -> str:
    """
    Возвращает путь к директории со словарями.
    
    Returns:
        Путь к директории со словарями
    """
    dict_dir = os.path.join(get_data_dir(), "dictionaries")
    
    # Создаем директорию, если она не существует
    if not os.path.exists(dict_dir):
        os.makedirs(dict_dir)
        logger.debug(f"Создана директория для словарей: {dict_dir}")
        
    return dict_dir

def get_output_dir() -> str:
    """
    Возвращает путь к директории для выходных файлов.
    
    Returns:
        Путь к директории для выходных файлов
    """
    output_dir = os.path.join(get_data_dir(), "output")
    
    # Создаем директорию, если она не существует
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.debug(f"Создана директория для выходных файлов: {output_dir}")
        
    return output_dir

def get_log_dir() -> str:
    """
    Возвращает путь к директории для логов.
    
    Returns:
        Путь к директории для логов
    """
    # Определяем путь к директории проекта
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    log_dir = os.path.join(project_dir, "logs")
    
    # Создаем директорию, если она не существует
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    return log_dir

def setup_logging(log_file: Optional[str] = None, level: int = logging.INFO) -> None:
    """
    Настраивает логирование.
    
    Args:
        log_file: Путь к файлу логов
        level: Уровень логирования
    """
    # Если путь к файлу логов не указан, используем стандартный
    if log_file is None:
        log_dir = get_log_dir()
        log_file = os.path.join(log_dir, "transcription.log")
    
    # Настройка логирования
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Устанавливаем уровень логирования для urllib3 и requests на WARNING
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    logger.debug("Логирование настроено")
    