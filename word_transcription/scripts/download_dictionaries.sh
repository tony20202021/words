#!/bin/bash
# download_dictionaries.sh - скрипт для загрузки и подготовки словарей для транскрипции

# Определение цветов для вывода
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
RESET="\033[0m"

# Директория для словарей
DICT_DIR="data/dictionaries"

# Создание директории для словарей, если она не существует
mkdir -p "$DICT_DIR"

echo -e "${BLUE}Начало загрузки и подготовки словарей...${RESET}"

# Функция для загрузки данных из интернета
function download_file {
    URL=$1
    OUTPUT=$2
    
    echo -e "${YELLOW}Загрузка файла $OUTPUT...${RESET}"
    
    if command -v curl &> /dev/null; then
        curl -s -o "$OUTPUT" "$URL"
    elif command -v wget &> /dev/null; then
        wget -q -O "$OUTPUT" "$URL"
    else
        echo -e "${RED}Ошибка: curl и wget не найдены. Установите одну из этих программ для загрузки файлов.${RESET}"
        return 1
    fi
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Ошибка загрузки файла $OUTPUT${RESET}"
        return 1
    fi
    
    echo -e "${GREEN}Файл $OUTPUT успешно загружен${RESET}"
    return 0
}

# Функция для конвертации данных в формат JSON
function convert_to_json {
    INPUT=$1
    OUTPUT=$2
    LANG=$3
    
    echo -e "${YELLOW}Конвертация файла $INPUT в JSON...${RESET}"
    
    # Здесь должен быть код конвертации, зависящий от формата входного файла
    # Пример: использование Python для конвертации
    python -c "
import json
import re

# Функция для обработки файла с произношениями
def process_pronunciation_file(file_path, output_path, lang_code):
    result = {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Пропуск комментариев и пустых строк
            if line.startswith('#') or not line.strip():
                continue
                
            # Разбор строки: ожидаемый формат зависит от языка
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                word = parts[0].strip().lower()
                transcription = parts[1].strip()
                
                # Сохранение слова и транскрипции
                result[word] = transcription
    
    # Сохранение результата в JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    
    return len(result)

# Выполнение конвертации
try:
    count = process_pronunciation_file('$INPUT', '$OUTPUT', '$LANG')
    print(f'Успешно сконвертировано {count} слов')
except Exception as e:
    print(f'Ошибка при конвертации: {str(e)}')
    exit(1)
"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Ошибка конвертации файла $INPUT${RESET}"
        return 1
    fi
    
    echo -e "${GREEN}Файл $INPUT успешно сконвертирован в $OUTPUT${RESET}"
    return 0
}

# Загрузка и подготовка немецкого словаря
echo -e "${BLUE}Подготовка немецкого словаря...${RESET}"
DE_TEMP="$DICT_DIR/de_temp.txt"
DE_DICT="$DICT_DIR/de_dict.json"

download_file "https://raw.githubusercontent.com/open-dict-data/ipa-dict/master/data/de.txt" "$DE_TEMP"
if [ $? -eq 0 ]; then
    convert_to_json "$DE_TEMP" "$DE_DICT" "de"
    rm "$DE_TEMP"
else
    echo -e "${YELLOW}Создание пустого немецкого словаря...${RESET}"
    echo "{}" > "$DE_DICT"
fi

# Загрузка и подготовка французского словаря
echo -e "${BLUE}Подготовка французского словаря...${RESET}"
FR_TEMP="$DICT_DIR/fr_temp.txt"
FR_DICT="$DICT_DIR/fr_dict.json"

download_file "https://raw.githubusercontent.com/open-dict-data/ipa-dict/master/data/fr_FR.txt" "$FR_TEMP"
if [ $? -eq 0 ]; then
    convert_to_json "$FR_TEMP" "$FR_DICT" "fr"
    rm "$FR_TEMP"
else
    echo -e "${YELLOW}Создание пустого французского словаря...${RESET}"
    echo "{}" > "$FR_DICT"
fi

# Загрузка и подготовка испанского словаря
echo -e "${BLUE}Подготовка испанского словаря...${RESET}"
ES_TEMP="$DICT_DIR/es_temp.txt"
ES_DICT="$DICT_DIR/es_dict.json"

download_file "https://raw.githubusercontent.com/open-dict-data/ipa-dict/master/data/es_ES.txt" "$ES_TEMP"
if [ $? -eq 0 ]; then
    convert_to_json "$ES_TEMP" "$ES_DICT" "es"
    rm "$ES_TEMP"
else
    echo -e "${YELLOW}Создание пустого испанского словаря...${RESET}"
    echo "{}" > "$ES_DICT"
fi

# Загрузка и подготовка английского словаря
echo -e "${BLUE}Подготовка английского словаря...${RESET}"
EN_TEMP="$DICT_DIR/en_temp.txt"
EN_DICT="$DICT_DIR/en_dict.json"

download_file "https://raw.githubusercontent.com/open-dict-data/ipa-dict/master/data/en_US.txt" "$EN_TEMP"
if [ $? -eq 0 ]; then
    convert_to_json "$EN_TEMP" "$EN_DICT" "en"
    rm "$EN_TEMP"
else
    echo -e "${YELLOW}Создание пустого английского словаря...${RESET}"
    echo "{}" > "$EN_DICT"
fi

echo -e "${GREEN}Подготовка словарей завершена!${RESET}"
echo -e "${BLUE}Словари доступны в директории: ${YELLOW}$DICT_DIR${RESET}"
