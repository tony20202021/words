"""
API response models for AI image generation.
Модели ответов API для AI генерации изображений.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Union
from datetime import datetime
from enum import Enum


class GenerationStatus(str, Enum):
    """Статусы генерации изображений"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"
    IN_PROGRESS = "in_progress"
    QUEUED = "queued"


@dataclass 
class AIGenerationMetadata:
    """Метаданные процесса AI генерации"""
    # Модели
    ai_model_used: str = None
    controlnet_model_used: str = None  # UPDATED: Single field for union model
    
    # Параметры conditioning
    conditioning_types_used: List[str] = None  # UPDATED: List of conditioning types for union model
    
    # Временные метрики
    generation_time_ms: Optional[int] = None
    conditioning_time_ms: Optional[Dict[str, Dict[str, int]]] = None # {"canny": {"opencv_canny": 150, "hed_canny": 200}}
    total_processing_time_ms: Optional[int] = None
    
    # Ресурсы
    gpu_memory_used_mb: Optional[float] = None
    gpu_memory_peak_mb: Optional[float] = None
    cpu_memory_used_mb: Optional[float] = None
    
    # Параметры генерации
    seed_used: Optional[int] = None
    image_dimensions: Optional[tuple] = None  # UPDATED: Added image dimensions
    
    # Версии и окружение
    diffusers_version: str = ""
    torch_version: str = ""
    cuda_version: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    error: bool = None


@dataclass
class AIImageResponse:
    """Ответ на запрос генерации AI изображения"""
    success: bool
    status: GenerationStatus
    generated_image_base64: Optional[str] = None  # base64
    
    # Промежуточные результаты
    base_image_base64: Optional[str] = None
    conditioning_images_base64: Optional[Dict[str, Dict[str, str]]] = None  # {"canny": {"opencv_canny": "base64", "hed_canny": "base64"}}
    prompt_used: Optional[str] = None
    
    # Метаданные генерации
    generation_metadata: Optional[AIGenerationMetadata] = None
    
    # Информация об ошибках
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    

@dataclass
class ConditioningResult:
    """Результаты генерации conditioning изображений"""
    # Множественные результаты для каждого типа
    canny_images: Optional[Dict[str, str]] = None      # {"opencv_canny": "base64", "hed_canny": "base64"}
    depth_images: Optional[Dict[str, str]] = None      # {"stroke_thickness": "base64", "distance_transform": "base64"}
    segmentation_images: Optional[Dict[str, str]] = None # {"radical_segmentation": "base64", "stroke_type": "base64"}
    scribble_images: Optional[Dict[str, str]] = None   # {"skeletonization": "base64", "morphological": "base64"}
    
    # Метаданные методов
    methods_used: Dict[str, List[str]] = None          # {"canny": ["opencv_canny", "hed_canny"]}
    generation_time_ms: Dict[str, Dict[str, int]] = None # {"canny": {"opencv_canny": 150, "hed_canny": 200}}
    
    # Оценка качества для каждого метода
    quality_scores: Dict[str, Dict[str, float]] = None # {"canny": {"opencv_canny": 0.8, "hed_canny": 0.9}}
    
    # Рекомендации
    recommended_methods: Dict[str, str] = None         # {"canny": "hed_canny", "depth": "stroke_thickness"}
    
    # Сравнительный анализ
    method_comparison: Optional["MethodComparisonResult"] = None
    
    # Ошибки по методам
    method_errors: Dict[str, Dict[str, str]] = None    # {"canny": {"hed_canny": "Model not available"}}


@dataclass
class MethodComparisonResult:
    """Результат сравнения методов conditioning"""
    best_method: str
    comparison_metrics: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class PromptAnalysisResult:
    """Результат анализа и генерации промпта"""
    character: str
    translation: str
    style: str
    
    # Сгенерированные промпты
    main_prompt: str
    

@dataclass
class ModelStatusResponse:
    """Ответ на запрос статуса AI моделей"""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Общий статус
    all_models_loaded: bool = False
    models_loading: bool = False
    
    # Статус отдельных моделей
    model_status: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # {
    #   "stable_diffusion": {"loaded": True, "memory_mb": 3500, "load_time_ms": 5000},
    #   "controlnet_union": {"loaded": True, "memory_mb": 2500, "load_time_ms": 3000}  # UPDATED
    # }
    
    # Использование ресурсов
    total_gpu_memory_used_mb: float = 0.0
    total_gpu_memory_available_mb: float = 0.0
    gpu_utilization_percent: float = 0.0
    
    # Проблемы и предупреждения
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class ErrorDetails:
    """Детальная информация об ошибке"""
    error_code: str
    error_message: str
    error_category: str  # "validation", "generation", "resource", "model"
    
    # Контекст ошибки
    component: str       # Компонент, где произошла ошибка
    operation: str       # Операция, которая вызвала ошибку
    
    # Диагностическая информация
    stack_trace: Optional[str] = None
    gpu_memory_at_error_mb: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Предложения по исправлению
    suggested_solutions: List[str] = field(default_factory=list)
    retry_possible: bool = True
    
    # Связанные ошибки
    related_errors: List[str] = field(default_factory=list)


# Вспомогательные функции для создания ответов
def create_success_response(
    generated_image: str,
    conditioning_images: Optional[Dict[str, Dict[str, str]]] = None,
    prompt_used: Optional[str] = None,
    metadata: Optional[AIGenerationMetadata] = None
) -> AIImageResponse:
    """Создает успешный ответ на генерацию изображения"""
    return AIImageResponse(
        success=True,
        status=GenerationStatus.SUCCESS,
        generated_image=generated_image,
        conditioning_images=conditioning_images,
        prompt_used=prompt_used,
        generation_metadata=metadata
    )


def create_error_response(
    error_message: str,
    error_details: Optional[ErrorDetails] = None,
    partial_results: Optional[Dict[str, Any]] = None
) -> AIImageResponse:
    """Создает ответ с ошибкой"""
    return AIImageResponse(
        success=False,
        status=GenerationStatus.FAILED,
        error=error_message,
        conditioning_images=partial_results.get("conditioning_images") if partial_results else None
    )


def create_partial_success_response(
    generated_image: Optional[str] = None,
    conditioning_images: Optional[Dict[str, Dict[str, str]]] = None,
    warnings: List[str] = None,
    metadata: Optional[AIGenerationMetadata] = None
) -> AIImageResponse:
    """Создает ответ с частичным успехом"""
    return AIImageResponse(
        success=True,
        status=GenerationStatus.PARTIAL_SUCCESS,
        generated_image=generated_image,
        conditioning_images=conditioning_images,
        warnings=warnings or [],
        generation_metadata=metadata
    )
