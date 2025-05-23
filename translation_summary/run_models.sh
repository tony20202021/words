#!/bin/bash
# Скрипт для запуска различных моделей для перевода китайских слов
# с поддержкой режимов с описанием и без

# Передаем токен Hugging Face, если он установлен
if [ -z "$HUGGING_FACE_HUB_TOKEN" ]; then
    echo "ВНИМАНИЕ: Переменная HUGGING_FACE_HUB_TOKEN не установлена. Доступ к закрытым моделям может быть ограничен."
    echo "Установите токен командой: export HUGGING_FACE_HUB_TOKEN=ваш_токен"
fi

# Проверяем наличие OpenAI API ключа
if [ -z "$OPENAI_API_KEY" ]; then
    echo "ВНИМАНИЕ: Переменная OPENAI_API_KEY не установлена. OpenAI модели будут недоступны."
    echo "Установите ключ командой: export OPENAI_API_KEY=ваш_ключ"
fi

# Путь к входному файлу
INPUT_FILE="../words/chinese_characters_0_30.json"

# Максимальное количество слов для обработки (для демонстрации)
MAX_ITEMS=30

# Текущая дата и время для уникальности имен файлов
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Корневой каталог для результатов
RESULTS_DIR="results"
# Подкаталог для текущего запуска
RUN_DIR="$RESULTS_DIR/run_${TIMESTAMP}"

# Создаем структуру каталогов
mkdir -p "$RUN_DIR"

# Экспортируем переменную окружения для Python-скриптов
export RUN_DIR="$RUN_DIR"

# Лог-файл (основной лог скрипта, отдельно от логов Python)
LOG_FILE="$RUN_DIR/run.log"

# Заголовок лога
echo "==================================" | tee -a "$LOG_FILE"
echo "Запуск тестирования моделей" | tee -a "$LOG_FILE"
echo "Дата и время: $(date)" | tee -a "$LOG_FILE"
echo "Входной файл: $INPUT_FILE" | tee -a "$LOG_FILE"
echo "Максимальное количество слов: $MAX_ITEMS" | tee -a "$LOG_FILE"
echo "Каталог результатов: $RUN_DIR" | tee -a "$LOG_FILE"
echo "==================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Получаем список доступных моделей из модуля Python
# Используем абсолютные импорты вместо относительных
MODELS_LIST=$(python -c '
import sys
import os
sys.path.insert(0, os.path.abspath("."))
try:
    from src.model_config import AVAILABLE_MODELS
    for key, value in AVAILABLE_MODELS.items():
        print(f"{key}|{value}")
except ImportError as e:
    print(f"Ошибка импорта: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Ошибка: {e}", file=sys.stderr)
    sys.exit(1)
')

# Проверяем, что получили список моделей
if [ $? -ne 0 ]; then
    echo "Ошибка при получении списка моделей" | tee -a "$LOG_FILE"
    exit 1
fi

# Разделяем модели на категории
declare -a API_MODELS=()
declare -a LIGHT_MODELS=()
declare -a HEAVY_MODELS=()

while IFS='|' read -r model_key model_path; do
    if [[ "$model_key" == gpt-* ]]; then
        API_MODELS+=("$model_key")
    elif [[ "$model_key" == *"7b"* || "$model_key" == *"7B"* || "$model_path" == *"7B"* || "$model_path" == *"7b"* || 
          "$model_key" == *"8b"* || "$model_key" == *"8B"* || "$model_path" == *"8B"* || "$model_path" == *"8b"* ]]; then
        HEAVY_MODELS+=("$model_key")
    else
        LIGHT_MODELS+=("$model_key")
    fi
done <<< "$MODELS_LIST"

# Выводим информацию о найденных моделях
echo "Найдены модели:" | tee -a "$LOG_FILE"
echo "API модели: ${API_MODELS[*]}" | tee -a "$LOG_FILE"
echo "Легкие модели: ${LIGHT_MODELS[*]}" | tee -a "$LOG_FILE"
echo "Тяжелые модели: ${HEAVY_MODELS[*]}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Функция для запуска модели и вывода затраченного времени
run_model() {
    local model_name=$1
    local model_param=$2
    local use_desc=$3
    local desc_suffix=""
    local desc_param=""
    
    # Настраиваем суффикс и параметр в зависимости от режима
    if [ "$use_desc" = "no" ]; then
        desc_suffix="_no_desc"
        desc_param="--no-description"
    fi
    
    local output_file="$RUN_DIR/results_${model_name}${desc_suffix}.json"
    
    echo "==================================" | tee -a "$LOG_FILE"
    echo "Запуск модели: $model_name (режим: ${use_desc:-с описанием})" | tee -a "$LOG_FILE"
    echo "==================================" | tee -a "$LOG_FILE"
    
    # Измеряем время выполнения
    start_time=$(date +%s)
    
    # Запускаем скрипт с выбранной моделью
    # Передаем каталог результатов через параметр
    python ./main_llm.py -i "$INPUT_FILE" -o "$output_file" -m "$model_param" --max $MAX_ITEMS $desc_param --results-dir "$RESULTS_DIR" 2>&1 | tee -a "$LOG_FILE"
    exit_code=$?
    
    # Проверяем успешность выполнения
    if [ $exit_code -ne 0 ]; then
        echo "Ошибка при запуске модели $model_name. Пропускаем и продолжаем..." | tee -a "$LOG_FILE"
        return 1
    fi
    
    # Вычисляем затраченное время
    end_time=$(date +%s)
    elapsed_time=$((end_time - start_time))
    
    echo "Модель $model_name (режим: ${use_desc:-с описанием}) завершила работу за $elapsed_time секунд" | tee -a "$LOG_FILE"
    echo "Результаты сохранены в $output_file" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    
    # Добавляем метаинформацию в файл результатов
    python -c "
import json, sys
try:
    with open('$output_file', 'r', encoding='utf-8') as f:
        data = json.load(f)
    data['_meta'] = {
        'model': '$model_name',
        'mode': '${use_desc:-с описанием}',
        'processing_time': $elapsed_time
    }
    with open('$output_file', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
except Exception as e:
    print(f'Ошибка при добавлении метаданных: {e}', file=sys.stderr)
"
    return 0
}

# Запускаем API модели в обоих режимах (если доступен ключ)
if [ -n "$OPENAI_API_KEY" ]; then
    echo "Тестирование API моделей с описанием..." | tee -a "$LOG_FILE"
    for model in "${API_MODELS[@]}"; do
        echo "Попытка запуска API модели: $model" | tee -a "$LOG_FILE"
        run_model "$model" "$model" ""
        # Проверяем успешность выполнения для API модели
        if [ $? -ne 0 ]; then
            echo "ВНИМАНИЕ: API модель $model недоступна (возможно, региональные ограничения)" | tee -a "$LOG_FILE"
        fi
    done

    echo "Тестирование API моделей без описания..." | tee -a "$LOG_FILE"
    for model in "${API_MODELS[@]}"; do
        echo "Попытка запуска API модели: $model (без описания)" | tee -a "$LOG_FILE"
        run_model "$model" "$model" "no"
        # Проверяем успешность выполнения для API модели
        if [ $? -ne 0 ]; then
            echo "ВНИМАНИЕ: API модель $model недоступна (возможно, региональные ограничения)" | tee -a "$LOG_FILE"
        fi
    done
else
    echo "Пропускаем API модели - не установлен OPENAI_API_KEY" | tee -a "$LOG_FILE"
fi

# Запускаем легкие модели в обоих режимах
echo "Тестирование легких моделей с описанием..." | tee -a "$LOG_FILE"
for model in "${LIGHT_MODELS[@]}"; do
    run_model "$model" "$model" ""
done

echo "Тестирование легких моделей без описания..." | tee -a "$LOG_FILE"
for model in "${LIGHT_MODELS[@]}"; do
    run_model "$model" "$model" "no"
done

# Проверяем наличие достаточной видеопамяти для более тяжелых моделей
gpu_mem=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n 1 2>/dev/null || echo "0")

if [ "$gpu_mem" -ge 16000 ]; then
    echo "Обнаружена GPU с достаточной памятью. Тестирование тяжелых моделей с описанием..." | tee -a "$LOG_FILE"
    for model in "${HEAVY_MODELS[@]}"; do
        run_model "$model" "$model" ""
    done
    
    echo "Тестирование тяжелых моделей без описания..." | tee -a "$LOG_FILE"
    for model in "${HEAVY_MODELS[@]}"; do
        run_model "$model" "$model" "no"
    done
else
    echo "ВНИМАНИЕ: Недостаточно видеопамяти для запуска тяжелых моделей" | tee -a "$LOG_FILE"
    echo "Доступно: ${gpu_mem:-N/A}MB, требуется: 16000MB" | tee -a "$LOG_FILE"
    echo "Пропускаем тяжелые модели" | tee -a "$LOG_FILE"
fi

echo "Все тесты завершены. Результаты сохранены в каталоге $RUN_DIR:" | tee -a "$LOG_FILE"
ls -l "$RUN_DIR"/results_*.json | tee -a "$LOG_FILE"

# Запускаем Python-скрипт для создания сравнительной таблицы
COMPARISON_FILE="$RUN_DIR/comparison.md"
echo "" | tee -a "$LOG_FILE"
echo "Создание сравнительной таблицы..." | tee -a "$LOG_FILE"

# Используем абсолютный путь и устанавливаем PYTHONPATH
PYTHONPATH="$(pwd)" python ./src/generate_comparison_table.py --results-dir "$RUN_DIR" --output "$COMPARISON_FILE" --input-file "$INPUT_FILE" --max-items "$MAX_ITEMS" 2>&1 | tee -a "$LOG_FILE"

# Создаем символическую ссылку на последний запуск для удобства
ln -sf "run_${TIMESTAMP}" "$RESULTS_DIR/latest"

echo "" | tee -a "$LOG_FILE"
echo "Сравнительная таблица сохранена в $COMPARISON_FILE" | tee -a "$LOG_FILE"
echo "Создана символическая ссылка на текущий запуск: $RESULTS_DIR/latest" | tee -a "$LOG_FILE"
echo "Логи Python-скриптов сохранены в отдельные файлы translation.log в каталоге $RUN_DIR" | tee -a "$LOG_FILE"
echo "Выполнение скрипта завершено" | tee -a "$LOG_FILE"
