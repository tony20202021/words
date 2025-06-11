# Руководство по установке Language Learning Bot

## Содержание
1. [Предварительные требования](#предварительные-требования)
2. [🆕 GPU требования для AI генерации](#gpu-требования-для-ai-генерации)
3. [Быстрая установка](#быстрая-установка)
4. [Пошаговая установка](#пошаговая-установка)
   - [Получение исходного кода](#получение-исходного-кода)
   - [🆕 Выбор режима установки](#выбор-режима-установки)
   - [Настройка окружения](#настройка-окружения)
   - [🆕 Установка AI зависимостей](#установка-ai-зависимостей)
   - [Установка MongoDB](#установка-mongodb)
   - [Конфигурация проекта](#конфигурация-проекта)
   - [Инициализация базы данных](#инициализация-базы-данных)
5. [🆕 Проверка AI компонентов](#проверка-ai-компонентов)
6. [Варианты установки MongoDB](#варианты-установки-mongodb)
7. [Проверка установки](#проверка-установки)
8. [🆕 AI Troubleshooting](#ai-troubleshooting)
9. [Устранение проблем](#устранение-проблем)
10. [Следующие шаги](#следующие-шаги)

## Предварительные требования

### Базовые требования:
- Python 3.8 или выше (**Python 3.10 рекомендуется для AI**)
- Conda (для управления окружением)
- Git с Git LFS (для AI моделей)
- Доступ к Telegram Bot API (токен)
- FFmpeg (для обработки аудиофайлов)
- Интернет соединение (для загрузки AI моделей)

### 🆕 Дополнительные требования для AI генерации:
- **NVIDIA GPU** с поддержкой CUDA 11.8+
- **NVIDIA Drivers** последней версии
- **Минимум 12GB GPU памяти** (рекомендуется 24GB+)
- **32GB+ системной RAM** (рекомендуется 64GB+)
- **100GB+ свободного места** для AI моделей и cache

---

## 🆕 GPU требования для AI генерации

Language Learning Bot теперь включает реальную AI генерацию изображений написания слов. Для полной функциональности требуется совместимый GPU.

### 🎮 Минимальная конфигурация (Basic AI):
```
GPU: RTX 3080, RTX 4070 Ti, A4000 (12GB VRAM)
RAM: 32GB System RAM
Storage: 100GB+ для моделей
Время генерации: ~15-20 секунд на изображение
Batch size: 1
```

### 🚀 Рекомендуемая конфигурация (Standard AI):
```
GPU: RTX 3090, RTX 4090, A5000, A6000 (24GB+ VRAM)
RAM: 64GB System RAM  
Storage: 500GB+ NVMe SSD
Время генерации: ~8-12 секунд на изображение
Batch size: 2-4
```

### ⚡ Оптимальная конфигурация (High-Performance AI):
```
GPU: A100, H100 (80GB+ VRAM)
RAM: 128GB+ System RAM
Storage: 1TB+ NVMe SSD
Время генерации: ~6-8 секунд на изображение  
Batch size: 8+
```

### 📊 Поддерживаемые GPU:
| GPU Model | VRAM | Status | Performance |
|-----------|------|--------|-------------|
| RTX 3080 | 12GB | ✅ Minimum | Slow (CPU offload required) |
| RTX 3090 | 24GB | ✅ Good | Standard |
| RTX 4070 Ti | 12GB | ✅ Minimum | Slow (optimizations required) |
| RTX 4080 | 16GB | ✅ Good | Standard |
| RTX 4090 | 24GB | ✅ Excellent | Fast |
| A4000 | 16GB | ✅ Good | Standard |
| A5000 | 24GB | ✅ Excellent | Fast |
| A6000 | 48GB | ✅ Excellent | Very Fast |
| A100 | 80GB | ✅ Optimal | Ultra Fast |
| H100 | 80GB | ✅ Optimal | Ultra Fast |

### ⚠️ Без GPU:
Если у вас нет совместимого GPU, бот будет работать в **Legacy Mode** без AI генерации, используя простые заглушки изображений.

---

## Быстрая установка

### 🚀 Для пользователей с GPU (AI режим):
```bash
# Клонирование репозитория с Git LFS
git clone https://github.com/username/language-learning-bot.git
cd language-learning-bot

# Инициализация Git LFS для AI моделей
git lfs install
git lfs pull

# Создание AI окружения с GPU поддержкой
conda env create -f writing_service/environment_gpu.yml
conda activate amikhalev_writing_images_service

# Проверка CUDA
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name()}')"

# Настройка конфигурации
cp .env.example .env
# Отредактируйте .env добавив TELEGRAM_BOT_TOKEN

# Запуск всех сервисов
./start_1_db.sh
python scripts/init_db.py
./start_2_backend.sh
./start_4_writing_service.sh  # 🆕 AI сервис
./start_3_frontend.sh

# Проверка AI функциональности
curl http://localhost:8600/health/detailed
```

### 📱 Для пользователей без GPU (Legacy режим):
```bash
# Клонирование и базовая установка
git clone https://github.com/username/language-learning-bot.git
cd language-learning-bot

# Базовое окружение без AI
conda env create -f environment.yml
conda activate language-learning-bot

# Копирование и настройка .env файла
cp .env.example .env
# Отредактируйте .env добавив TELEGRAM_BOT_TOKEN

# Запуск базовых сервисов (без Writing Service)
./start_1_db.sh
python scripts/init_db.py
./start_2_backend.sh
./start_3_frontend.sh
```

---

## Пошаговая установка

### Получение исходного кода

```bash
# Клонирование репозитория
git clone https://github.com/username/language-learning-bot.git
cd language-learning-bot

# 🆕 Инициализация Git LFS для AI моделей (если планируете использовать AI)
git lfs install
git lfs pull
```

### 🆕 Выбор режима установки

Перед установкой определитесь с режимом работы:

#### 🤖 AI Mode (с GPU):
- ✅ Полная функциональность включая AI генерацию
- ✅ Высококачественные изображения написания
- ✅ Multi-ControlNet генерация
- ⚠️ Требует совместимый GPU
- ⚠️ Длительная первая установка (загрузка ~15GB моделей)

#### 📱 Legacy Mode (без GPU):
- ✅ Вся основная функциональность бота
- ✅ Быстрая установка и запуск
- ✅ Простые изображения-заглушки
- ❌ Нет AI генерации изображений

**Рекомендация**: Если у вас есть совместимый GPU, используйте AI Mode для полного опыта.

### Настройка окружения

#### 🤖 Для AI Mode (с GPU):

```bash
# Создание специального AI окружения
conda env create -f writing_service/environment_gpu.yml

# Активация окружения
conda activate amikhalev_writing_images_service

# Проверка CUDA доступности
python -c "
import torch
print(f'✓ CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'✓ GPU: {torch.cuda.get_device_name()}')
    print(f'✓ GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB')
    print(f'✓ CUDA Version: {torch.version.cuda}')
else:
    print('❌ CUDA not available - falling back to Legacy Mode')
"
```

#### 📱 Для Legacy Mode (без GPU):

```bash
# Создание базового окружения
conda env create -f environment.yml

# Активация окружения
conda activate language-learning-bot

# Проверка базовых зависимостей
python -c "
import sys
print(f'✓ Python: {sys.version}')
print('✓ Ready for Legacy Mode')
"
```

### 🆕 Установка AI зависимостей

Если вы выбрали **AI Mode**, необходимо установить дополнительные AI зависимости:

#### Установка AI пакетов:
```bash
# Убедитесь что активировано AI окружение
conda activate amikhalev_writing_images_service

# Установка AI зависимостей
cd writing_service
pip install -r requirements_gpu.txt

# Проверка ключевых AI компонентов
python -c "
import diffusers
import transformers
import accelerate
import xformers
print('✓ Diffusers:', diffusers.__version__)
print('✓ Transformers:', transformers.__version__)
print('✓ Accelerate:', accelerate.__version__)
print('✓ XFormers:', xformers.__version__)
"
```

#### Создание cache директорий:
```bash
# Создание директорий для AI моделей
mkdir -p writing_service/cache/{huggingface,transformers,datasets,torch,pytorch_kernel_cache}
mkdir -p writing_service/temp/generated_images

# Настройка переменных окружения
export HF_HOME="$(pwd)/writing_service/cache/huggingface"
export TORCH_HOME="$(pwd)/writing_service/cache/torch"
export TRANSFORMERS_CACHE="$(pwd)/writing_service/cache/transformers"

echo "✓ AI cache directories created"
```

#### Тестовая загрузка модели (опционально):
```bash
# Предварительная загрузка основной модели (займет ~10-15 минут)
python -c "
print('Downloading Stable Diffusion XL model...')
from diffusers import StableDiffusionXLPipeline
pipeline = StableDiffusionXLPipeline.from_pretrained('stabilityai/stable-diffusion-xl-base-1.0', torch_dtype=torch.float16)
print('✓ Model downloaded successfully')
"
```

### Установка MongoDB

#### Использование скрипта start_1_db.sh (рекомендуется):
```bash
# Сделать скрипт исполняемым
chmod +x start_1_db.sh

# Запустить MongoDB
./start_1_db.sh
```

Для других способов установки MongoDB см. раздел [Варианты установки MongoDB](#варианты-установки-mongodb).

### Конфигурация проекта

#### Создание файла .env:
```bash
cp .env.example .env
```

Отредактируйте файл `.env` и установите необходимые параметры:

```ini
# Настройки MongoDB
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DB_NAME=language_learning_bot

# Настройки Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here

# 🆕 Настройки Writing Service (AI)
WRITING_SERVICE_HOST=localhost
WRITING_SERVICE_PORT=8600
WRITING_SERVICE_ENABLED=true  # false для Legacy Mode
```

#### 🆕 Настройка AI конфигурации:

Если используете **AI Mode**, настройте конфигурацию в `writing_service/conf/config/ai_generation.yaml`:

```yaml
# Можете оставить настройки по умолчанию или настроить под ваш GPU
ai_generation:
  enabled: true
  
  # GPU настройки (автоматически определяются, но можно переопределить)
  gpu:
    device: "cuda"
    memory_efficient: true  # true для GPU <24GB
    enable_attention_slicing: true  # true для GPU <24GB
    enable_cpu_offload: false  # true для GPU <12GB
    max_batch_size: 1  # увеличьте для мощных GPU
    
  # Параметры генерации (можете настроить)
  generation:
    num_inference_steps: 30  # больше = качественнее, но медленнее
    guidance_scale: 7.5      # контроль соответствия промпту
    width: 1024
    height: 1024
```

### Инициализация базы данных

После установки и настройки инициализируйте базу данных:

```bash
# Проверьте, что MongoDB запущена
./start_1_db.sh

# Инициализация базы данных
python scripts/init_db.py

# Заполнение базы тестовыми данными (опционально)
python scripts/seed_data.py
```

---

## 🆕 Проверка AI компонентов

Если вы установили **AI Mode**, проверьте работоспособность AI системы:

### Проверка GPU:
```bash
# NVIDIA System Management Interface
nvidia-smi

# Должны увидеть информацию о GPU, драйверах и CUDA
```

### Проверка PyTorch + CUDA:
```bash
python -c "
import torch
print('PyTorch version:', torch.__version__)
print('CUDA available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('CUDA version:', torch.version.cuda)
    print('GPU device:', torch.cuda.get_device_name())
    print('GPU memory:', f'{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB')
    
    # Тест GPU операции
    x = torch.randn(1000, 1000).cuda()
    y = torch.mm(x, x)
    print('✓ GPU computation test passed')
else:
    print('❌ CUDA not available - check GPU drivers')
"
```

### Проверка AI библиотек:
```bash
python -c "
# Проверка ключевых AI библиотек
try:
    import diffusers
    print('✓ Diffusers:', diffusers.__version__)
except ImportError:
    print('❌ Diffusers not installed')

try:
    import transformers
    print('✓ Transformers:', transformers.__version__)
except ImportError:
    print('❌ Transformers not installed')

try:
    import xformers
    print('✓ XFormers:', xformers.__version__)
except ImportError:
    print('⚠️ XFormers not available (performance will be slower)')

try:
    import controlnet_aux
    print('✓ ControlNet-Aux available')
except ImportError:
    print('❌ ControlNet-Aux not installed')
"
```

### Тест AI pipeline:
```bash
# Запуск Writing Service для тестирования
./start_4_writing_service.sh

# Ожидание запуска (может занять несколько минут при первом запуске)
echo "Waiting for Writing Service to start..."
sleep 30

# Проверка health check
curl http://localhost:8600/health

# Детальная проверка AI статуса
curl http://localhost:8600/health/detailed | jq '.ai_status'

# Если все OK, увидите status: "healthy" или "initializing"
```

---

## Варианты установки MongoDB

### Способ 1: Установка в пользовательский каталог (без прав суперпользователя)

```bash
# Создание директорий для MongoDB
mkdir -p ~/mongodb/data ~/mongodb/log ~/mongodb/config ~/mongodb/bin

# Скачивание MongoDB (для Ubuntu 22.04, x86_64)
cd ~/Downloads
wget https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-ubuntu2204-7.0.5.tgz

# Распаковка архива
tar -zxvf mongodb-linux-x86_64-ubuntu2204-7.0.5.tgz

# Копирование исполняемых файлов
cp -R mongodb-linux-x86_64-ubuntu2204-7.0.5/bin/* ~/mongodb/bin/

# Добавление MongoDB в PATH
echo 'export PATH=~/mongodb/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

### Способ 2: Установка через менеджер пакетов (с правами суперпользователя)

#### Для Ubuntu/Debian:
```bash
# Импорт публичного ключа MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -

# Создание файла источника пакетов
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# Обновление базы пакетов
sudo apt update

# Установка MongoDB
sudo apt install -y mongodb-org

# Запуск MongoDB
sudo systemctl start mongod

# Включение автозапуска при старте системы
sudo systemctl enable mongod
```

### Способ 3: Использование Docker

```bash
# Запуск MongoDB в контейнере
docker run --name mongodb -d -p 27017:27017 -v ~/mongodb/data:/data/db mongo:7.0.5
```

---

## Проверка установки

После завершения установки проверьте работоспособность всех компонентов:

### 1. Проверка MongoDB
```bash
# Проверка запущена ли MongoDB
ps aux | grep mongod

# Подключение к MongoDB
mongosh
```

### 2. Проверка Backend
```bash
# Запуск бэкенда
./start_2_backend.sh

# Проверка доступности API
curl http://localhost:8500/api/health
```

### 3. 🆕 Проверка Writing Service (AI Mode)
```bash
# Запуск Writing Service
./start_4_writing_service.sh

# Базовая проверка
curl http://localhost:8600/health

# Детальная проверка AI компонентов
curl http://localhost:8600/health/detailed

# Проверка API статуса
curl http://localhost:8600/api/writing/status
```

### 4. Проверка Frontend
```bash
# Запуск фронтенда
./start_3_frontend.sh
```

Проверьте, что бот отвечает на команду `/start` в Telegram.

### 5. 🆕 Тест полного AI pipeline
```bash
# Тест генерации изображения (требует запущенного Writing Service)
curl -X POST http://localhost:8600/api/writing/generate-writing-image \
  -H "Content-Type: application/json" \
  -d '{
    "word": "test",
    "translation": "тест", 
    "language": "english",
    "style": "traditional"
  }'

# Если успешно, получите JSON с generated_image_base64
```

---

## 🆕 AI Troubleshooting

### CUDA не доступен
**Проблема**: `torch.cuda.is_available()` возвращает `False`

**Решения**:
1. Проверьте NVIDIA драйверы:
   ```bash
   nvidia-smi
   ```

2. Проверьте CUDA installation:
   ```bash
   nvcc --version
   ```

3. Переустановите PyTorch с CUDA:
   ```bash
   conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
   ```

### XFormers проблемы
**Проблема**: Ошибки импорта XFormers или low performance

**Решения**:
1. Установите XFormers для вашей CUDA версии:
   ```bash
   pip install xformers --index-url https://download.pytorch.org/whl/cu118
   ```

2. Если проблемы продолжаются, отключите XFormers:
   ```yaml
   # В writing_service/conf/config/ai_generation.yaml
   gpu:
     enable_xformers: false
   ```

### Out of Memory ошибки
**Проблема**: `CUDA out of memory` during generation

**Решения**:
1. Уменьшите batch size:
   ```yaml
   # В writing_service/conf/config/ai_generation.yaml
   generation:
     batch_size: 1
   ```

2. Включите memory optimizations:
   ```yaml
   gpu:
     memory_efficient: true
     enable_attention_slicing: true
     enable_cpu_offload: true  # для GPU <16GB
   ```

3. Уменьшите размер изображения:
   ```yaml
   generation:
     width: 512
     height: 512
   ```

### Медленная генерация
**Проблема**: Генерация изображений занимает >30 секунд

**Решения**:
1. Проверьте temperature GPU:
   ```bash
   nvidia-smi
   ```

2. Включите оптимизации:
   ```yaml
   gpu:
     use_torch_compile: true
     enable_xformers: true
   ```

3. Проверьте что GPU используется:
   ```bash
   watch nvidia-smi
   ```

### Модели не загружаются
**Проблема**: Ошибки загрузки HuggingFace моделей

**Решения**:
1. Проверьте интернет соединение:
   ```bash
   curl -I https://huggingface.co
   ```

2. Очистите cache:
   ```bash
   rm -rf writing_service/cache/huggingface/*
   ```

3. Установите git-lfs:
   ```bash
   git lfs install
   ```

---

## Устранение проблем

### MongoDB не запускается
**Проблема**: Ошибки при запуске MongoDB с использованием скрипта `start_1_db.sh`.

**Решение**:
1. Проверьте наличие директорий:
   ```bash
   ls -la ~/mongodb/data
   ls -la ~/mongodb/log
   ```

2. Проверьте права доступа:
   ```bash
   chmod 755 ~/mongodb/data
   chmod 755 ~/mongodb/log
   ```

3. Проверьте логи MongoDB:
   ```bash
   cat ~/mongodb/log/mongod.log
   ```

### Бэкенд не запускается
**Проблема**: Ошибки при запуске бэкенда.

**Решение**:
1. Проверьте подключение к MongoDB:
   ```bash
   mongosh --eval "db.stats()"
   ```

2. Проверьте конфигурацию в `.env`:
   ```bash
   cat .env | grep MONGODB
   ```

3. Проверьте порт бэкенда:
   ```bash
   lsof -i :8500
   ```

### Фронтенд не запускается
**Проблема**: Ошибки при запуске фронтенда.

**Решение**:
1. Проверьте токен Telegram бота:
   ```bash
   cat frontend/conf/config/bot.yaml | grep token
   ```

2. Проверьте доступность бэкенда:
   ```bash
   curl http://localhost:8500/api/health
   ```

3. Проверьте доступность Writing Service (AI Mode):
   ```bash
   curl http://localhost:8600/health
   ```

---

## Следующие шаги

После успешной установки:

### Для всех режимов:
1. [Руководство по запуску](../running/running_guide.md) - запуск и управление компонентами 
2. [Функциональность бота](../functionality/bot_commands.md) - команды и возможности бота
3. [API-интерфейс](../api/api_reference.md) - документация по API-клиенту

### 🆕 Для AI Mode:
1. [AI Image Generation](../functionality/ai_image_generation.md) - полное руководство по AI
2. [GPU Optimization](../running/performance_tuning.md) - оптимизация производительности
3. [AI Monitoring](../running/monitoring_ai.md) - мониторинг AI компонентов

### Для разработчиков:
1. [Тестирование](../development/testing_guide.md) - как запускать и писать тесты
2. [Конфигурация](../development/configuration.md) - детали конфигурации с Hydra
3. [🆕 AI Development](../development/ai_configuration.md) - разработка AI компонентов

---

## 📊 Итоговая проверка установки

После завершения установки выполните финальную проверку:

### Базовая функциональность:
```bash
# ✅ MongoDB работает
curl http://localhost:8500/api/health

# ✅ Backend API доступен
curl http://localhost:8500/api/languages

# ✅ Telegram бот отвечает
# Отправьте /start боту в Telegram
```

### 🆕 AI функциональность (AI Mode):
```bash
# ✅ Writing Service работает
curl http://localhost:8600/health

# ✅ AI компоненты готовы
curl http://localhost:8600/health/detailed | jq '.ai_status'

# ✅ Генерация изображений работает
curl -X POST http://localhost:8600/api/writing/generate-writing-image \
  -H "Content-Type: application/json" \
  -d '{"word": "hello", "translation": "привет"}'
```

Если все проверки прошли успешно, Language Learning Bot готов к работе! 🎉

### 🎯 Режимы работы:

- **🤖 AI Mode**: Полная функциональность + AI генерация изображений
- **📱 Legacy Mode**: Базовая функциональность без AI (простые заглушки)

Выберите режим в зависимости от доступного оборудования и потребностей!
