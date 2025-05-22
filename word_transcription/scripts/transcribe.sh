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
    echo "  -l, --language    Код языка для всех слов (de, fr, es, en)"
    echo "  --lang-field      Имя поля для хранения кода языка (по умолчанию: language)"
    echo "  --word-field      Имя поля со словом (по умолчанию: word)"
    echo "  --trans-field     Имя поля для основной транскрипции (по умолчанию: transcription)"
    echo "  --all-trans-field Имя поля для всех транскрипций (по умолчанию: all_transcriptions)"
    echo ""
    echo "API ключи:"
    echo "  -f, --forvo-key             API ключ для Forvo"
    echo "  --easypronunciation-key     API ключ для EasyPronunciation"
    echo "  --ibm-watson-key            API ключ для IBM Watson"
    echo "  --openai-key                API ключ для OpenAI"
    echo ""
    echo "Выбор сервисов:"
    echo "  --services [список]  Список сервисов для использования, разделенных пробелом"
    echo "                       Доступные значения: dictionary epitran forvo google wiktionary"
    echo "                       g2p phonemize easypronunciation ibm_watson charsiu openai all"
    echo ""
    echo "Отдельные флаги для сервисов (будут проигнорированы, если указан --services):"
    echo "  --use-epitran               Использовать Epitran для транскрипции"
    echo "  --use-wiktionary            Использовать Wiktionary API для транскрипции"
    echo "  --use-forvo                 Использовать Forvo API для транскрипции"
    echo "  --use-google                Использовать Google Translate API для транскрипции"
    echo "  --use-g2p                   Использовать g2p библиотеку для транскрипции"
    echo "  --use-phonemize             Использовать phonemizer для транскрипции"
    echo "  --use-easypronunciation     Использовать EasyPronunciation API для транскрипции"
    echo "  --use-ibm-watson            Использовать IBM Watson API для транскрипции"
    echo "  --use-charsiu               Использовать CharsiuG2P для транскрипции"
    echo "  --use-openai                Использовать OpenAI API для транскрипции"
    echo ""
    echo "  -v, --verbose     Подробный вывод"
    echo "  -h, --help        Показать эту справку"
    echo ""
    echo "Примеры:"
    echo "  $0 words.xlsx                     # Обработка Excel-файла с иностранными словами"
    echo "  $0 words.xlsx -o output.json      # Сохранение результатов в указанный файл"
    echo "  $0 words.json                     # Обработка JSON-файла"
    echo "  $0 words.xlsx -s 100 -e 200       # Обработка строк с 100 по 200"
    echo "  $0 words.xlsx -l fr               # Указать французский язык для всех слов"
    echo "  $0 words.xlsx --services g2p epitran  # Использовать только g2p и epitran"
    echo "  $0 words.xlsx --use-g2p --use-epitran # То же самое, другой способ"
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
EASYPRONUNCIATION_KEY=""
IBM_WATSON_KEY=""
OPENAI_KEY=""
LANGUAGE=""
LANG_FIELD="language"
WORD_FIELD="word"
TRANS_FIELD="transcription"
ALL_TRANS_FIELD="all_transcriptions"
VERBOSE=""
SERVICES=""

# Флаги для отдельных сервисов
USE_EPITRAN=""
USE_WIKTIONARY=""
USE_FORVO=""
USE_GOOGLE=""
USE_G2P=""
USE_PHONEMIZE=""
USE_EASYPRONUNCIATION=""
USE_IBM_WATSON=""
USE_CHARSIU=""
USE_OPENAI=""

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
        --easypronunciation-key)
            EASYPRONUNCIATION_KEY="$2"
            shift 2
            ;;
        --ibm-watson-key)
            IBM_WATSON_KEY="$2"
            shift 2
            ;;
        --openai-key)
            OPENAI_KEY="$2"
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
        --word-field)
            WORD_FIELD="$2"
            shift 2
            ;;
        --trans-field)
            TRANS_FIELD="$2"
            shift 2
            ;;
        --all-trans-field)
            ALL_TRANS_FIELD="$2"
            shift 2
            ;;
        --services)
            # Собираем все сервисы до следующего флага
            SERVICES=""
            shift
            while [[ $# -gt 0 && ! $1 == -* ]]; do
                SERVICES="$SERVICES $1"
                shift
            done
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
        --use-g2p)
            USE_G2P="--use-g2p"
            shift
            ;;
        --use-phonemize)
            USE_PHONEMIZE="--use-phonemize"
            shift
            ;;
        --use-easypronunciation)
            USE_EASYPRONUNCIATION="--use-easypronunciation"
            shift
            ;;
        --use-ibm-watson)
            USE_IBM_WATSON="--use-ibm-watson"
            shift
            ;;
        --use-charsiu)
            USE_CHARSIU="--use-charsiu"
            shift
            ;;
        --use-openai)
            USE_OPENAI="--use-openai"
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

if [ ! -z "$EASYPRONUNCIATION_KEY" ]; then
    CMD_ARGS="$CMD_ARGS --easypronunciation-key \"$EASYPRONUNCIATION_KEY\""
fi

if [ ! -z "$IBM_WATSON_KEY" ]; then
    CMD_ARGS="$CMD_ARGS --ibm-watson-key \"$IBM_WATSON_KEY\""
fi

if [ ! -z "$OPENAI_KEY" ]; then
    CMD_ARGS="$CMD_ARGS --openai-key \"$OPENAI_KEY\""
fi

if [ ! -z "$LANGUAGE" ]; then
    CMD_ARGS="$CMD_ARGS --language \"$LANGUAGE\""
fi

if [ ! -z "$LANG_FIELD" ]; then
    CMD_ARGS="$CMD_ARGS --lang-field \"$LANG_FIELD\""
fi

if [ ! -z "$WORD_FIELD" ]; then
    CMD_ARGS="$CMD_ARGS --word-field \"$WORD_FIELD\""
fi

if [ ! -z "$TRANS_FIELD" ]; then
    CMD_ARGS="$CMD_ARGS --transcription-field \"$TRANS_FIELD\""
fi

if [ ! -z "$ALL_TRANS_FIELD" ]; then
    CMD_ARGS="$CMD_ARGS --all-transcriptions-field \"$ALL_TRANS_FIELD\""
fi

if [ ! -z "$SERVICES" ]; then
    CMD_ARGS="$CMD_ARGS --services$SERVICES"
fi

# Добавляем флаги для отдельных сервисов, только если не указаны сервисы через --services
if [ -z "$SERVICES" ]; then
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
    
    if [ ! -z "$USE_G2P" ]; then
        CMD_ARGS="$CMD_ARGS $USE_G2P"
    fi
    
    if [ ! -z "$USE_PHONEMIZE" ]; then
        CMD_ARGS="$CMD_ARGS $USE_PHONEMIZE"
    fi
    
    if [ ! -z "$USE_EASYPRONUNCIATION" ]; then
        CMD_ARGS="$CMD_ARGS $USE_EASYPRONUNCIATION"
    fi
    
    if [ ! -z "$USE_IBM_WATSON" ]; then
        CMD_ARGS="$CMD_ARGS $USE_IBM_WATSON"
    fi
    
    if [ ! -z "$USE_CHARSIU" ]; then
        CMD_ARGS="$CMD_ARGS $USE_CHARSIU"
    fi
    
    if [ ! -z "$USE_OPENAI" ]; then
        CMD_ARGS="$CMD_ARGS $USE_OPENAI"
    fi
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

echo -e "${GREEN}Готово!${RESET}"
