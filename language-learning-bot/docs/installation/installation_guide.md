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
conda activate amikhalev_writing_images_service

# Проверка CUDA
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name()}')"
```

### 3. 🔥 Установка AI зависимостей
```bash
# AI зависимости для GPU
pip install -r writing_service/requirements_gpu.txt

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
mkdir -p writing_service/cache/{huggingface,transformers,torch,pytorch_kernel_cache}

# Настройка переменных окружения
export HF_HOME="./writing_service/cache/huggingface"
export TORCH_HOME="./writing_service/cache/torch"
export TRANSFORMERS_CACHE="./writing_service/cache/transformers"
```

### 6. Запуск сервисов
```bash
./start_1_db.sh          # MongoDB
./start_2_backend.sh     # Backend API
./start_4_writing_service.sh # 🔥 AI сервис
./start_3_frontend.sh    # Telegram бот
```

## Детальная установка

### 🔥 AI Environment Setup

#### **GPU Validation:**
```bash
# Проверка NVIDIA драйверов
nvidia-smi

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
pip install controlnet-aux>=0.0.10

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

### 🔥 Writing Service Configuration

#### **AI Generation Config** (`writing_service/conf/config/ai_generation.yaml`):
```yaml
ai_generation:
  enabled: true
  
  models:
    base_model: "stabilityai/stable-diffusion-xl-base-1.0"
    controlnet_models:
      union: "xinsir/controlnet-union-sdxl-1.0"
  
  generation:
    width: 1024
    height: 1024
    batch_size: 1  # Увеличить для 80GB GPU
  
  gpu:
    device: "cuda"
    memory_efficient: true    # false для 80GB GPU
    enable_attention_slicing: true  # false для 80GB GPU
    max_batch_size: 2         # 4-8 для 80GB GPU
```

## Первый запуск

### 1. Инициализация базы данных
```bash
python scripts/init_db.py
python scripts/seed_data.py
```

### 2. 🔥 Проверка AI сервиса
```bash
# Проверка здоровья AI
curl http://localhost:8600/health

# Детальная AI диагностика
curl http://localhost:8600/health/detailed

# Готовность AI моделей
curl http://localhost:8600/health/ready
```

### 3. 🔥 Тестовая AI генерация
```bash
curl -X POST http://localhost:8600/api/writing/generate-writing-image \
  -H "Content-Type: application/json" \
  -d '{
    "word": "测试",
    "translation": "test",
    "width": 512,
    "height": 512
  }'
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
- Union ControlNet: ~2.5GB
- VAE & Scheduler: ~1GB

### Manual Model Download (опционально)
```bash
python scripts/ai_model_downloader.py --model sdxl-base
python scripts/ai_model_downloader.py --model union-controlnet
```

### Model Cache Locations
```bash
writing_service/cache/
├── huggingface/               # HuggingFace модели
│   └── hub/
│       ├── models--stabilityai--stable-diffusion-xl-base-1.0/
│       └── models--xinsir--controlnet-union-sdxl-1.0/
├── torch/                     # PyTorch cache
└── pytorch_kernel_cache/      # Compiled CUDA kernels
```

## Troubleshooting

### 🔥 AI Issues

#### **CUDA Out of Memory:**
```bash
# Уменьшить batch size
echo "generation.batch_size: 1" >> writing_service/conf/config/ai_generation.yaml

# Включить memory optimizations
echo "gpu.memory_efficient: true" >> writing_service/conf/config/ai_generation.yaml
```

#### **Model Loading Failures:**
```bash
# Очистить cache
rm -rf writing_service/cache/huggingface/*

# Проверить сетевое подключение
curl -I https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
```

#### **Slow Generation:**
```bash
# Проверить GPU utilization
nvidia-smi -l 1

# Включить оптимизации
echo "gpu.use_torch_compile: true" >> writing_service/conf/config/ai_generation.yaml
```

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
chmod -R 755 writing_service/cache/
```

#### **Port Conflicts:**
```bash
# Проверка занятых портов
lsof -i :8600  # Writing Service
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
watch -n 1 nvidia-smi

# AI service monitoring
tail -f writing_service/logs/writing_service.log | grep "AI"
```

## Development Setup

### Auto-reload Development
```bash
# Frontend auto-reload
./start_3_frontend_auto_reload.sh

# Backend auto-reload (built-in FastAPI)
# Writing Service auto-reload (built-in FastAPI)
```

### Testing
```bash
# Все тесты
./run_tests.sh

# AI тесты отдельно
pytest writing_service/tests/test_ai/ -v

# Интеграционные AI тесты
pytest writing_service/tests/integration/ -v
```

---

**🎯 После установки:**

1. ✅ Проверьте AI health checks
2. ✅ Протестируйте генерацию изображений
3. ✅ Настройте мониторинг GPU
4. ✅ Запустите Telegram бота
5. ✅ Проверьте все сервисы работают

**🔥 Ready для production AI generation!**
