# Руководство по установке (ОБНОВЛЕНО с AI)

## 🔥 Системные требования

### Hardware Requirements для AI:

#### **Minimum (12GB GPU):**
```
GPU: RTX 3080, RTX 4070 Ti, A4000
RAM: 32GB System RAM
Storage: 100GB+ для AI моделей
CUDA: 11.8+
```

#### **Recommended (24GB+ GPU):**
```
GPU: RTX 3090, RTX 4090, A5000, A6000
RAM: 64GB System RAM
Storage: 500GB+ NVMe SSD
CUDA: 11.8+
```

#### **Optimal (80GB+ GPU):**
```
GPU: A100, H100
RAM: 128GB+ System RAM
Storage: 1TB+ NVMe SSD
CUDA: 11.8+
```

### Software Requirements:
- Python 3.8+
- MongoDB 5.0+
- CUDA 11.8+
- Git LFS
- FFmpeg

## Быстрая установка

### 1. Клонирование репозитория
```bash
git clone https://github.com/username/language-learning-bot.git
cd language-learning-bot

# Инициализация Git LFS для AI моделей
git lfs install
```

### 2. 🔥 Настройка AI окружения
```bash
# Создание AI окружения с GPU поддержкой
conda env create -f environment_gpu.yml

# Проверка CUDA
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name()}')"
```

### 3. 🔥 Установка AI зависимостей
```bash
# AI зависимости для GPU

# Проверка ключевых AI библиотек
python -c "import diffusers, transformers, xformers; print('AI libraries OK')"
```

### 4. Настройка конфигурации
```bash
cp .env.example .env
# Отредактируйте .env и добавьте TELEGRAM_BOT_TOKEN
```

### 5. 🔥 Создание AI кэш директорий
```bash
# Создание cache директорий для AI моделей

# Настройка переменных окружения
```

### 6. Запуск сервисов
```bash
./start_1_db.sh          # MongoDB
./start_2_backend.sh     # Backend API
./start_3_frontend.sh    # Telegram бот
```

## Детальная установка

### 🔥 AI Environment Setup

#### **GPU Validation:**
```bash
# Проверка NVIDIA драйверов

# Проверка CUDA
nvcc --version

# Проверка PyTorch с CUDA
python -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'CUDA version: {torch.version.cuda}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name()}')
    print(f'Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB')
"
```

#### **AI Dependencies Installation:**
```bash
# Основные AI frameworks
pip install torch>=2.1.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# HuggingFace ecosystem
pip install diffusers>=0.25.0 transformers>=4.39.0 accelerate>=0.24.0

# Optimization libraries
pip install xformers>=0.0.22

# Monitoring
pip install pynvml>=11.5.0 gpustat>=1.1.0
```

### MongoDB Setup
```bash
# Установка MongoDB
sudo apt-get install -y mongodb

# Или через Docker
docker run -d -p 8527:8527 --name mongodb mongo:5.0
```

## Первый запуск

### 1. Инициализация базы данных
```bash
python scripts/init_db.py
python scripts/seed_data.py
```

# Проверка здоровья AI

# Детальная AI диагностика

# Готовность AI моделей
```

### 4. Запуск Telegram бота
```bash
# Проверка что бот отвечает
# Отправьте /start боту в Telegram
```

## 🔥 AI Model Management

### Automatic Model Download
Модели загружаются автоматически при первом запросе:
- Stable Diffusion XL: ~7GB
- VAE & Scheduler: ~1GB

### Manual Model Download (опционально)
```bash
```

### Model Cache Locations
```bash
│   └── hub/
```

## Troubleshooting

### Common Issues

#### **Dependencies:**
```bash
# Переустановка проблемных пакетов
pip install --force-reinstall xformers
pip install --upgrade diffusers transformers
```

#### **Permissions:**
```bash
# Права на cache директории
```

#### **Port Conflicts:**
```bash
# Проверка занятых портов
lsof -i :8500  # Backend
lsof -i :8527 # MongoDB
```

## Performance Optimization

### 🔥 GPU Optimization

#### **Memory Settings:**
```bash
# Для 12GB GPU
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128

# Для 24GB+ GPU  
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

#### **CUDA Settings:**
```bash
export CUDA_VISIBLE_DEVICES=0
export TOKENIZERS_PARALLELISM=false
```

### **Monitoring Setup:**
```bash
# Continuous GPU monitoring

# Frontend auto-reload
./start_3_frontend_auto_reload.sh

# Backend auto-reload (built-in FastAPI)
```

### Testing
```bash
# Все тесты
./run_tests.sh

# AI тесты отдельно

# Интеграционные AI тесты
```

---

**🎯 После установки:**

1. ✅ Проверьте AI health checks
2. ✅ Протестируйте генерацию изображений
3. ✅ Настройте мониторинг GPU
4. ✅ Запустите Telegram бота
5. ✅ Проверьте все сервисы работают

**🔥 Ready для production AI generation!**
