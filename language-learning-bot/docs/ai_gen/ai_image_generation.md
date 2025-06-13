# AI Image Generation - Реальная система генерации изображений

## Обзор AI системы

Writing Service включает **реальную AI систему** для генерации изображений написания слов, построенную на **Stable Diffusion XL** с **Union ControlNet**.

### 🎯 Основные возможности
- **Union ControlNet генерация** - единая модель вместо 4 отдельных
- **GPU оптимизация** - автонастройка под железо (12GB-80GB)
- **Production ready** - health monitoring, error handling

### 🏗️ Технологический стек
```
AI Models:
├── Stable Diffusion XL Base 1.0        # Основная модель
├── Union ControlNet SDXL 1.0            # ControlNet модель
└── Optimized VAE & Scheduler            # Оптимизации

AI Frameworks:  
├── Diffusers >= 0.25.0                  # HuggingFace
├── PyTorch >= 2.1.0                     # ML framework
├── XFormers >= 0.0.22                   # Optimization
└── CUDA 11.8+                           # GPU support
```

## Архитектура AI компонентов

### 🎯 AI Pipeline:
```
Character → Preprocessing → Multi-Conditioning → Prompt → Union ControlNet → SDXL → Result
```

### 🏗️ Основные компоненты:

#### 1. **AIImageGenerator** (`ai_image_generator.py`)
Основной orchestrator AI pipeline:
```python
class AIImageGenerator:
    async def generate_character_image(
        self, character: str, translation: str = ""
    ) -> AIGenerationResult
```

#### 2. **MultiControlNetPipeline** (`multi_controlnet_pipeline.py`) 
Union ControlNet integration:
```python
class MultiControlNetPipeline:
    async def generate(
        self, prompt: str, control_images: Dict
    ) -> Image.Image
```

#### 3. **Conditioning Generators**
- **CannyConditioning** - edge detection
- **DepthConditioning** - depth estimation  
- **SegmentationConditioning** - image segmentation
- **ScribbleConditioning** - artistic sketches

#### 4. **PromptBuilder** (`prompt_builder.py`)
Intelligent prompt engineering:
```python
class PromptBuilder:
    async def build_prompt(
        self, character: str, style: str = "comic"
    ) -> PromptResult
```

#### 5. **ModelLoader** (`model_loader.py`)
AI model management:
```python
class ModelLoader:
    async def load_stable_diffusion_xl(self, model_name: str)
    async def load_controlnet_models(self, model_configs: Dict)
```

#### 6. **GPUManager** (`gpu_manager.py`)
GPU resource management:
```python
class GPUManager:
    def get_gpu_status(self) -> GPUStatus
    def optimize_pipeline(self, pipeline) -> Dict
```

## Multi-ControlNet Pipeline

### 🎛️ Union ControlNet Architecture
Union ControlNet объединяет **4 типа conditioning** в единой модели:

```python
# Типы conditioning в Union ControlNet
control_type_mapping = {
    "depth": 1,       # Depth estimation
    "canny": 3,       # Edge detection  
    "segment": 5,     # Segmentation
    "scribble": 2     # Artistic sketches
}
```

### ⚡ GPU Optimization Profiles:
```python
# Автоматическая настройка по GPU памяти
if gpu_memory >= 80:  # A100
    - memory_efficient: False
    - batch_size: 4-8
    - torch_compile: True

elif gpu_memory >= 24:  # RTX 4090
    - memory_efficient: True  
    - batch_size: 2
    - attention_slicing: True

else:  # <24GB
    - cpu_offload: True
    - batch_size: 1
    - all optimizations: True
```

## Conditioning генераторы

### 🖼️ Четыре типа Conditioning:

#### 1. **Canny Edge Detection**
```python
class CannyConditioning:
    available_methods = [
        "opencv_canny",              # Классический OpenCV
        "structured_edge_detection", # Structured edges
        "adaptive_canny"             # Adaptive thresholding
    ]
```

#### 2. **Depth Estimation**  
```python
class DepthConditioning:
    available_methods = [
        "stroke_thickness_depth",    # На основе толщины линий
        "distance_transform_depth",  # Distance transform
        "ai_depth_estimation"        # MiDaS AI модель
    ]
```

#### 3. **Segmentation**
```python
class SegmentationConditioning:
    available_methods = [
        "radical_segmentation",      # По радикалам Kangxi
        "stroke_type_segmentation",  # По типам штрихов
        "ai_segmentation"            # SAM модель
    ]
```

#### 4. **Scribble Generation**
```python
class ScribbleConditioning:
    available_methods = [
        "skeletonization_scribble",  # Zhang-Suen алгоритм
        "hand_drawn_simulation",     # Имитация рисования
        "style_aware_scribble"       # Стиль-зависимые наброски
    ]
```

## Prompt Engineering

### 🎨 Style-Aware Prompt Building:

#### **Style Definitions** (`style_definitions.py`)
```python
styles = {
    "comic": StyleDefinition(
        base_template="A vibrant comic book style illustration of {meaning}, inspired by {character}",
        controlnet_weights={"canny": 0.9, "depth": 0.5, "segmentation": 0.7, "scribble": 0.3}
    ),
    "watercolor": StyleDefinition(
        base_template="A soft watercolor painting depicting {meaning}, with flowing brushstrokes",
        controlnet_weights={"canny": 0.4, "depth": 0.3, "segmentation": 0.3, "scribble": 0.8}
    )
}
```

#### **Intelligent Prompt Builder**
- Автоматическое построение промптов

## GPU управление и оптимизация

### 🎮 Intelligent GPU Management:

#### **Hardware Detection:**
```python
def _detect_gpu_info(self) -> Dict:
    device_props = torch.cuda.get_device_properties(0)
    return {
        "name": device_props.name,
        "total_memory_gb": device_props.total_memory / 1024**3,
        "temperature": get_gpu_temperature(),
        "power_usage": get_gpu_power()
    }
```

#### **Automatic Optimization:**
```python
def _determine_optimization_profile(self) -> OptimizationProfile:
    total_memory = self.gpu_info["total_memory_gb"]
    
    if total_memory >= 80:    # A100
        return UltraHighMemoryProfile()
    elif total_memory >= 24:  # RTX 4090  
        return HighMemoryProfile()
    else:                     # <24GB
        return MinimalMemoryProfile()
```

#### **Memory Monitoring:**
```python
@contextmanager
def memory_monitor(self, operation_name: str):
    memory_before = self.get_memory_usage()
    try:
        yield
    finally:
        memory_after = self.get_memory_usage()
        self.track_memory_usage(operation_name, memory_before, memory_after)
```

## API интеграция

### 🌐 Writing Service API:

#### **AI Generation:**
```bash
curl -X POST http://localhost:8600/api/writing/generate-writing-image \
  -H "Content-Type: application/json" \
  -d '{
    "word": "学习",
    "translation": "study",
    "width": 1024,
    "height": 1024
  }'
```

#### **Response Format:**
```json
{
  "success": true,
  "generated_image_base64": "iVBORw0KGgoAAAANS...",
  "conditioning_images_base64": {
    "canny": {"opencv_canny": "base64..."},
    "depth": {"ai_depth_estimation": "base64..."}
  },
  "prompt_used": "A comic book style illustration...",
  "generation_metadata": {
    "generation_time_ms": 8500,
    "model_used": "stabilityai/stable-diffusion-xl-base-1.0",
    "controlnet_model": "union"
  }
}
```

#### **Health Checks:**
```bash
# Базовая проверка
GET /health

# AI диагностика  
GET /health/detailed

# Готовность моделей
GET /health/ready

# Прогрев AI
POST /health/warmup
```

## Мониторинг и производительность

### 📊 Performance Monitoring:

#### **Generation Times by GPU:**
```
RTX 4090 (24GB):
├── Cold start: ~15-30s (model loading)
├── Warm generation: ~8-12s  
└── Batch 2: ~14-18s

A100 (80GB):
├── Cold start: ~10-20s
├── Warm generation: ~6-8s
└── Batch 4: ~18-24s
```

#### **Memory Usage:**
```
Models: ~6-8GB VRAM
├── Stable Diffusion XL: ~4-5GB
├── Union ControlNet: ~2-3GB  
└── Generation overhead: +2-4GB peak
```

#### **Optimization Features:**
- **Lazy loading** - модели загружаются при запросе
- **Memory efficient attention** - XFormers optimization
- **GPU memory management** - автоматическая очистка

### 🔍 Debugging:

#### **AI Status Dashboard:**
```bash
# Статус моделей
curl http://localhost:8600/api/writing/status

# GPU utilization  
curl http://localhost:8600/health/detailed | jq '.gpu_status'

# Generation statistics
curl http://localhost:8600/health/detailed | jq '.service_status.ai_status'
```

#### **Logging:**
```yaml
# AI-specific logging
logging:
  loggers:
    ai_models:
      level: "DEBUG" 
      include_model_loading: true
      include_memory_usage: true
    
    generation:
      level: "INFO"
      include_timing: true
      include_parameters: true
```
