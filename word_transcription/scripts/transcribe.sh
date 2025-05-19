#!/bin/bash
# transcribe.sh - скрипт для добавления транскрипций к иностранным словам

# Определение цветов для вывода
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
RESET="\033[0m"

# Функция для вывода справки
function show_help {
    echo -e "${BLUE}Скрипт для добавления транскрипций к иностранным словам${RESET}"
    echo ""
    echo "Использование: $0 <файл> [опции]"
    echo ""
    echo "Аргументы:"
    echo "  <файл>            Путь к входному файлу (Excel или JSON)"
    echo ""
    echo "Опции:"
    echo "  -o, --output      Путь к выходному JSON-файлу"
    echo "  -s, --start       Начальный индекс для обработки Excel-файла (по умолчанию: 0)"
    echo "  -e, --end         Конечный индекс для обработки Excel-файла"
    echo "  -d, --dict-dir    Путь к директории со словарями"
    echo "  -f, --forvo-key   API ключ для Forvo"
    echo "  -l, --language    Код языка для всех слов (de, fr, es, en)"
    echo "  --lang-field      Имя поля для хранения кода языка (по умолчанию: language)"
    echo "  --use-epitran     Использовать Epitran для транскрипции"
    echo "  --use-wiktionary  Использовать Wiktionary API для транскрипции"
    echo "  --use-forvo       Использовать Forvo API для транскрипции"
    echo "  --use-google      Использовать Google Translate API для транскрипции"
    echo "  -v, --verbose     Подробный вывод"
    echo "  -h, --help        Показать эту справку"
    echo ""
    echo "Примеры:"
    echo "  $0 words.xlsx                     # Обработка Excel-файла с иностранными словами"
    echo "  $0 words.xlsx -o output.json      # Сохранение результатов в указанный файл"
    echo "  $0 words.json                     # Обработка JSON-файла"
    echo "  $0 words.xlsx -s 100 -e 200       # Обработка строк с 100 по 200"
    echo "  $0 words.xlsx -l fr               # Указать французский язык для всех слов"
    echo "  $0 words.xlsx --use-epitran       # Использовать Epitran для транскрипции"
    echo ""
    exit 0
}

# Проверка наличия аргументов
if [ $# -lt 1 ]; then
    echo -e "${RED}Ошибка: не указан входной файл${RESET}"
    show_help
fi

# Парсинг аргументов
INPUT_FILE=""
OUTPUT_FILE=""
START_INDEX=0
END_INDEX=""
DICT_DIR=""
FORVO_KEY=""
LANGUAGE=""
LANG_FIELD="language"
VERBOSE=""
USE_EPITRAN=""
USE_WIKTIONARY=""
USE_FORVO=""
USE_GOOGLE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -s|--start)
            START_INDEX="$2"
            shift 2
            ;;
        -e|--end)
            END_INDEX="$2"
            shift 2
            ;;
        -d|--dict-dir)
            DICT_DIR="$2"
            shift 2
            ;;
        -f|--forvo-key)
            FORVO_KEY="$2"
            shift 2
            ;;
        -l|--language)
            LANGUAGE="$2"
            shift 2
            ;;
        --lang-field)
            LANG_FIELD="$2"
            shift 2
            ;;
        --use-epitran)
            USE_EPITRAN="--use-epitran"
            shift
            ;;
        --use-wiktionary)
            USE_WIKTIONARY="--use-wiktionary"
            shift
            ;;
        --use-forvo)
            USE_FORVO="--use-forvo"
            shift
            ;;
        --use-google)
            USE_GOOGLE="--use-google"
            shift
            ;;
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        *)
            if [ -z "$INPUT_FILE" ]; then
                INPUT_FILE="$1"
                shift
            else
                echo -e "${RED}Ошибка: неизвестный аргумент '$1'${RESET}"
                show_help
            fi
            ;;
    esac
done

# Проверка существования входного файла
if [ ! -f "$INPUT_FILE" ]; then
    echo -e "${RED}Ошибка: файл '$INPUT_FILE' не найден${RESET}"
    exit 1
fi

# Формирование имени выходного файла, если не указано
if [ -z "$OUTPUT_FILE" ]; then
    # Замена расширения на .json
    OUTPUT_FILE="${INPUT_FILE%.*}.json"
    echo -e "${BLUE}Выходной файл не указан, будет использоваться: ${YELLOW}$OUTPUT_FILE${RESET}"
fi

# Проверка наличия словарей
if [ -z "$DICT_DIR" ]; then
    DICT_DIR="data/dictionaries"
    
    if [ ! -d "$DICT_DIR" ]; then
        echo -e "${YELLOW}Директория словарей не найдена. Создание...${RESET}"
        
        # Создание директории для словарей
        mkdir -p "$DICT_DIR"
        
        # Создание пустых словарей для основных языков
        echo "{}" > "$DICT_DIR/de_dict.json"  # Немецкий
        echo "{}" > "$DICT_DIR/fr_dict.json"  # Французский
        echo "{}" > "$DICT_DIR/es_dict.json"  # Испанский
        echo "{}" > "$DICT_DIR/en_dict.json"  # Английский
        
        echo -e "${GREEN}Созданы пустые словари для основных языков${RESET}"
    else
        echo -e "${GREEN}Директория словарей найдена: ${YELLOW}$DICT_DIR${RESET}"
    fi
fi

# Формирование параметров командной строки
CMD_ARGS=""

if [ ! -z "$OUTPUT_FILE" ]; then
    CMD_ARGS="$CMD_ARGS --output-file \"$OUTPUT_FILE\""
fi

if [ ! -z "$START_INDEX" ]; then
    CMD_ARGS="$CMD_ARGS --start-index $START_INDEX"
fi

if [ ! -z "$END_INDEX" ]; then
    CMD_ARGS="$CMD_ARGS --end-index $END_INDEX"
fi

if [ ! -z "$DICT_DIR" ]; then
    CMD_ARGS="$CMD_ARGS --dict-dir \"$DICT_DIR\""
fi

if [ ! -z "$FORVO_KEY" ]; then
    CMD_ARGS="$CMD_ARGS --forvo-key \"$FORVO_KEY\""
fi

if [ ! -z "$LANGUAGE" ]; then
    CMD_ARGS="$CMD_ARGS --language \"$LANGUAGE\""
fi

if [ ! -z "$LANG_FIELD" ]; then
    CMD_ARGS="$CMD_ARGS --lang-field \"$LANG_FIELD\""
fi

if [ ! -z "$USE_EPITRAN" ]; then
    CMD_ARGS="$CMD_ARGS $USE_EPITRAN"
fi

if [ ! -z "$USE_WIKTIONARY" ]; then
    CMD_ARGS="$CMD_ARGS $USE_WIKTIONARY"
fi

if [ ! -z "$USE_FORVO" ]; then
    CMD_ARGS="$CMD_ARGS $USE_FORVO"
fi

if [ ! -z "$USE_GOOGLE" ]; then
    CMD_ARGS="$CMD_ARGS $USE_GOOGLE"
fi

if [ ! -z "$VERBOSE" ]; then
    CMD_ARGS="$CMD_ARGS $VERBOSE"
fi

# Запуск скрипта
echo -e "${BLUE}Запуск процесса добавления транскрипций...${RESET}"
echo -e "${YELLOW}python ./src/transcription_script.py \"$INPUT_FILE\" $CMD_ARGS${RESET}"

# Установка переменной PYTHONPATH для корректного импорта модулей
eval "PYTHONPATH=. python ./src/transcription_script.py \"$INPUT_FILE\" $CMD_ARGS"

# Проверка успешности выполнения
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Транскрипции успешно добавлены в файл: ${YELLOW}$OUTPUT_FILE${RESET}"
else
    echo -e "${RED}Ошибка при добавлении транскрипций${RESET}"
    exit 1
fi

# Вывод статистики
if [ -f "$OUTPUT_FILE" ]; then
    WORD_COUNT=$(grep -o "\"word\"" "$OUTPUT_FILE" | wc -l)
    # Улучшенный подсчет непустых транскрипций
    TRANS_COUNT=$(grep -o "\"transcription\":\s*\"[^\"]*[^\"\s]" "$OUTPUT_FILE" | wc -l)
    
    echo -e "${GREEN}Статистика:${RESET}"
    echo -e "  ${BLUE}Всего слов:${RESET} $WORD_COUNT"
    echo -e "  ${BLUE}С транскрипцией:${RESET} $TRANS_COUNT"
    if [ $WORD_COUNT -gt 0 ]; then
        echo -e "  ${BLUE}Процент заполнения:${RESET} $(( TRANS_COUNT * 100 / WORD_COUNT ))%"
    else
        echo -e "  ${BLUE}Процент заполнения:${RESET} 0%"
    fi
fi

echo -e "${GREEN}Готово!${RESET}"
