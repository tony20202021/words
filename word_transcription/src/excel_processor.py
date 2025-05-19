import pandas as pd
import logging
import os
from typing import List, Tuple, Dict, Any, Optional

# Настройка логирования
logger = logging.getLogger(__name__)

def read_excel_file(file_path: str, start_index: int = 0, end_index: Optional[int] = None) -> Tuple[List[str], List[int]]:
    """
    Читает файл Excel и извлекает слова и их номера
    
    Args:
        file_path (str): Путь к Excel-файлу
        start_index (int): Начальный индекс (от 0)
        end_index (int, optional): Конечный индекс, если None - до конца файла
    
    Returns:
        Tuple[List[str], List[int]]: Кортеж (список слов, список номеров)
    
    Raises:
        FileNotFoundError: Если файл не найден
        ValueError: Если индексы некорректны или формат файла не поддерживается
        Exception: При ошибке чтения Excel-файла
    """
    # Проверка наличия файла
    if not os.path.exists(file_path):
        logger.error(f"Файл {file_path} не найден")
        raise FileNotFoundError(f"Файл {file_path} не найден")
    
    # Проверка корректности индексов
    if start_index < 0:
        logger.error(f"Некорректный начальный индекс: {start_index}")
        raise ValueError(f"Некорректный начальный индекс: {start_index}")
    
    if end_index is not None and end_index < start_index:
        logger.error(f"Конечный индекс ({end_index}) должен быть больше или равен начальному ({start_index})")
        raise ValueError(f"Конечный индекс ({end_index}) должен быть больше или равен начальному ({start_index})")
    
    logger.info(f"Чтение файла: {file_path}")
    
    try:
        # Определение движка для чтения Excel в зависимости от расширения файла
        if file_path.endswith('.xls'):
            logger.info("Используется движок xlrd для файла .xls")
            df = pd.read_excel(file_path, sheet_name=0, engine='xlrd')
        elif file_path.endswith('.xlsx'):
            logger.info("Используется движок openpyxl для файла .xlsx")
            df = pd.read_excel(file_path, sheet_name=0, engine='openpyxl')
        else:
            logger.error(f"Неподдерживаемый формат файла: {file_path}")
            raise ValueError(f"Неподдерживаемый формат файла: {file_path}")
        
        # Вывод информации о DataFrame
        logger.debug(f"Размер DataFrame: {df.shape}")
        logger.debug(f"Колонки DataFrame: {df.columns.tolist()}")
        logger.debug(f"Типы данных колонок: {df.dtypes}")
        
        # Проверка, достаточно ли строк в DataFrame
        if start_index >= len(df):
            logger.error(f"Начальный индекс ({start_index}) превышает количество строк в файле ({len(df)})")
            raise ValueError(f"Начальный индекс ({start_index}) превышает количество строк в файле ({len(df)})")
        
        # Если конечный индекс не указан, используем последнюю строку DataFrame
        if end_index is None:
            end_index = len(df) - 1
            logger.info(f"Конечный индекс не указан, используется последняя строка: {end_index}")
        
        # Проверка, не превышает ли конечный индекс размер DataFrame
        if end_index >= len(df):
            end_index = len(df) - 1
            logger.warning(f"Конечный индекс превышает количество строк, используется последняя строка: {end_index}")
        
        # Извлечение слов и номеров
        # Предполагается, что слова находятся в колонке с индексом 1, а номера - в колонке с индексом 0
        words = df.iloc[start_index:end_index+1, 1].tolist()
        numbers = df.iloc[start_index:end_index+1, 0].tolist()
        
        # Конвертация значений в строки, если необходимо
        words = [str(word) if not isinstance(word, str) else word for word in words]
        numbers = [int(num) if not isinstance(num, int) else num for num in numbers]
        
        logger.info(f"Успешно извлечено {len(words)} слов из файла")
        
        return words, numbers
    
    except Exception as e:
        logger.error(f"Ошибка при чтении Excel-файла: {str(e)}")
        raise Exception(f"Ошибка при чтении Excel-файла: {str(e)}")

def convert_to_json_structure(words: List[str], numbers: List[int], 
                             language: str = None) -> Dict[str, Dict[str, Any]]:
    """
    Преобразует списки слов и номеров в структуру JSON
    
    Args:
        words (List[str]): Список слов
        numbers (List[int]): Список номеров
        language (str, optional): Код языка (если None, будет определен автоматически)
    
    Returns:
        Dict[str, Dict[str, Any]]: Словарь в формате JSON
    """
    result = {}
    
    for i, (num, word) in enumerate(zip(numbers, words)):
        result[str(num)] = {
            "word": word,
            "transcription": "",  # Пустая строка, будет заполнена позже
            "description": [],    # Пустой список, может быть заполнен позже
            "frequency": num      # Используем номер как частоту
        }
        
        # Если язык указан, добавляем его
        if language:
            result[str(num)]["language"] = language
    
    logger.info(f"Создана JSON-структура с {len(result)} записями")
    return result

def extract_frequency_from_excel(file_path: str, word_column: int = 1, 
                                frequency_column: Optional[int] = None) -> Dict[str, int]:
    """
    Извлекает частоты слов из Excel-файла
    
    Args:
        file_path (str): Путь к Excel-файлу
        word_column (int): Индекс колонки со словами
        frequency_column (int, optional): Индекс колонки с частотами, если None - используются номера строк
    
    Returns:
        Dict[str, int]: Словарь вида {слово: частота}
    """
    try:
        # Определение движка для чтения Excel в зависимости от расширения файла
        if file_path.endswith('.xls'):
            df = pd.read_excel(file_path, sheet_name=0, engine='xlrd')
        elif file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path, sheet_name=0, engine='openpyxl')
        else:
            logger.error(f"Неподдерживаемый формат файла: {file_path}")
            raise ValueError(f"Неподдерживаемый формат файла: {file_path}")
        
        # Словарь для хранения частот
        frequency_dict = {}
        
        # Если колонка с частотами указана, используем её
        if frequency_column is not None:
            if frequency_column >= len(df.columns):
                logger.error(f"Индекс колонки с частотами ({frequency_column}) превышает количество колонок в файле ({len(df.columns)})")
                raise ValueError(f"Индекс колонки с частотами ({frequency_column}) превышает количество колонок в файле ({len(df.columns)})")
            
            # Извлечение слов и частот
            for i in range(len(df)):
                word = df.iloc[i, word_column]
                freq = df.iloc[i, frequency_column]
                
                # Конвертация в строку для слова
                if not isinstance(word, str):
                    word = str(word)
                
                # Конвертация в int для частоты
                if not isinstance(freq, int):
                    try:
                        freq = int(freq)
                    except (ValueError, TypeError):
                        logger.warning(f"Невозможно преобразовать частоту '{freq}' в целое число. Используется значение по умолчанию 0.")
                        freq = 0
                
                frequency_dict[word] = freq
        else:
            # Если колонка не указана, используем индексы строк
            for i in range(len(df)):
                word = df.iloc[i, word_column]
                
                # Конвертация в строку для слова
                if not isinstance(word, str):
                    word = str(word)
                
                # Используем индекс строки + 1 как частоту
                frequency_dict[word] = i + 1
        
        logger.info(f"Извлечены частоты для {len(frequency_dict)} слов")
        return frequency_dict
    
    except Exception as e:
        logger.error(f"Ошибка при извлечении частот из Excel-файла: {str(e)}")
        raise Exception(f"Ошибка при извлечении частот из Excel-файла: {str(e)}")

def process_excel_to_json(file_path: str, start_index: int = 0, end_index: Optional[int] = None,
                         language: str = None) -> Dict[str, Dict[str, Any]]:
    """
    Обрабатывает Excel-файл и возвращает структуру JSON
    
    Args:
        file_path (str): Путь к Excel-файлу
        start_index (int): Начальный индекс (от 0)
        end_index (int, optional): Конечный индекс, если None - до конца файла
        language (str, optional): Код языка (если None, будет определен автоматически)
    
    Returns:
        Dict[str, Dict[str, Any]]: Словарь в формате JSON
    """
    # Чтение данных из Excel-файла
    words, numbers = read_excel_file(file_path, start_index, end_index)
    
    # Преобразование в структуру JSON
    result = convert_to_json_structure(words, numbers, language)
    
    # Извлечение частот из файла (используем номера как частоты)
    try:
        frequency_dict = extract_frequency_from_excel(file_path)
        
        # Обновление частот в результате
        for key, entry in result.items():
            word = entry["word"]
            if word in frequency_dict:
                entry["frequency"] = frequency_dict[word]
    except Exception as e:
        logger.warning(f"Не удалось извлечь частоты из файла: {str(e)}. Используются номера как частоты.")
    
    return result

# Пример использования
if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("excel_processor.log"),
            logging.StreamHandler()
        ]
    )
    
    # Тестирование функций
    try:
        file_path = "data/example/foreign_words.xls"
        result = process_excel_to_json(file_path, 0, 10)
        print(f"Результат обработки файла {file_path}:")
        for key, value in result.items():
            print(f"{key}: {value}")
    except Exception as e:
        print(f"Ошибка при тестировании: {str(e)}")