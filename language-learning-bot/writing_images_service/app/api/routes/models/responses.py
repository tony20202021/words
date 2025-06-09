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


class ConditioningQuality(str, Enum):
    """Оценка качества conditioning"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    FAILED = "failed"


@dataclass
class AIImageResponse:
    """Ответ на запрос генерации AI изображения"""
    success: bool
    status: GenerationStatus
    generated_image: Optional[str] = None  # base64
    
    # Промежуточные результаты
    conditioning_images: Optional[Dict[str, Dict[str, str]]] = None  # {"canny": {"opencv_canny": "base64", "hed_canny": "base64"}}
    prompt_used: Optional[str] = None
    negative_prompt_used: Optional[str] = None
    
    # Семантический анализ
    semantic_analysis: Optional['SemanticAnalysisResult'] = None
    
    # Метаданные генерации
    generation_metadata: Optional['AIGenerationMetadata'] = None
    
    # Информация об ошибках
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    # Качество результата
    quality_assessment: Optional['QualityAssessment'] = None


@dataclass 
class AIGenerationMetadata:
    """Метаданные процесса AI генерации"""
    # Модели
    model_used: str
    controlnet_models_used: Dict[str, str]
    
    # Параметры conditioning
    conditioning_weights_used: Dict[str, float]
    conditioning_methods_used: Dict[str, List[str]]
    conditioning_quality_scores: Dict[str, Dict[str, float]]  # {"canny": {"opencv_canny": 0.8, "hed_canny": 0.9}}
    
    # Временные метрики
    generation_time_ms: int
    conditioning_time_ms: Dict[str, Dict[str, int]]  # {"canny": {"opencv_canny": 150, "hed_canny": 200}}
    semantic_analysis_time_ms: Optional[int] = None
    total_processing_time_ms: int = 0
    
    # Ресурсы
    gpu_memory_used_mb: float
    gpu_memory_peak_mb: float
    cpu_memory_used_mb: Optional[float] = None
    
    # Параметры генерации
    seed_used: int
    actual_steps_completed: int
    guidance_scale_used: float
    
    # Статистика модели
    model_loading_time_ms: Optional[int] = None
    model_cache_hit: bool = False
    
    # Версии и окружение
    diffusers_version: str = ""
    torch_version: str = ""
    cuda_version: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


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
    method_comparison: Optional['MethodComparisonResult'] = None
    
    # Ошибки по методам
    method_errors: Dict[str, Dict[str, str]] = None    # {"canny": {"hed_canny": "Model not available"}}


@dataclass
class SemanticAnalysisResult:
    """Результаты семантического анализа иероглифа"""
    character: str
    analysis_successful: bool
    
    # Базовая информация
    basic_info: Dict[str, Any] = field(default_factory=dict)  # Unihan данные
    meanings: List[str] = field(default_factory=list)         # Все значения
    primary_meaning: str = ""                                 # Основное значение
    pronunciations: Dict[str, str] = field(default_factory=dict) # {"mandarin": "huǒ", "cantonese": "fo2"}
    
    # Структурный анализ
    radicals: Dict[str, Any] = field(default_factory=dict)    # Анализ радикалов
    composition: Dict[str, Any] = field(default_factory=dict) # IDS композиция
    etymology: Dict[str, Any] = field(default_factory=dict)   # Этимология
    stroke_analysis: Dict[str, Any] = field(default_factory=dict) # Анализ штрихов
    
    # Контекстуальный анализ
    context: Dict[str, Any] = field(default_factory=dict)     # Частотность, коллокации
    semantic_domains: List[str] = field(default_factory=list) # Семантические области
    usage_examples: List[str] = field(default_factory=list)   # Примеры использования
    
    # Визуальные свойства
    visual_properties: Dict[str, Any] = field(default_factory=dict) # Визуальные свойства
    color_associations: List[str] = field(default_factory=list)     # Цветовые ассоциации
    texture_associations: List[str] = field(default_factory=list)   # Текстурные ассоциации
    motion_associations: List[str] = field(default_factory=list)    # Ассоциации движения
    
    # Элементы для промпта
    prompt_elements: Dict[str, Any] = field(default_factory=dict)   # Готовые элементы для промпта
    suggested_modifiers: List[str] = field(default_factory=list)    # Рекомендуемые модификаторы
    
    # Метаданные анализа
    analysis_metadata: Dict[str, Any] = field(default_factory=dict) # Время, версии баз данных
    confidence_scores: Dict[str, float] = field(default_factory=dict) # Уверенность в разных аспектах
    data_sources_used: List[str] = field(default_factory=list)      # Использованные источники данных
    
    # Предупреждения и ограничения
    warnings: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)


@dataclass
class PromptAnalysisResult:
    """Результат анализа и генерации промпта"""
    character: str
    translation: str
    style: str
    
    # Сгенерированные промпты
    main_prompt: str
    negative_prompt: str
    prompt_variations: List[str] = field(default_factory=list)
    
    # Анализ элементов промпта
    prompt_elements: Dict[str, List[str]] = field(default_factory=dict) # {"visual": [...], "style": [...]}
    semantic_contribution: Dict[str, float] = field(default_factory=dict) # Вклад семантики в промпт
    
    # Оценки
    estimated_quality_score: Optional[float] = None     # Оценка ожидаемого качества
    prompt_complexity_score: float = 0.0                # Сложность промпта
    semantic_richness_score: float = 0.0                # Семантическая насыщенность
    
    # Рекомендации
    suggestions: List[str] = field(default_factory=list)
    alternative_approaches: List[str] = field(default_factory=list)
    
    # Использованные данные
    semantic_analysis_used: bool = False
    visual_elements_used: List[str] = field(default_factory=list)
    cultural_context_used: List[str] = field(default_factory=list)


@dataclass
class QualityAssessment:
    """Оценка качества сгенерированного изображения"""
    overall_score: float  # 0.0 - 1.0
    
    # Компонентные оценки
    visual_coherence: float = 0.0        # Визуальная согласованность
    semantic_accuracy: float = 0.0       # Семантическая точность
    style_consistency: float = 0.0       # Соответствие стилю
    technical_quality: float = 0.0       # Техническое качество
    
    # Детальная оценка
    conditioning_effectiveness: Dict[str, float] = field(default_factory=dict) # Эффективность каждого conditioning
    prompt_adherence: float = 0.0        # Соответствие промпту
    
    # Проблемы и рекомендации
    identified_issues: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    
    # Автоматическая оценка
    automated_scores: Dict[str, float] = field(default_factory=dict)
    confidence_in_assessment: float = 0.0


@dataclass
class MethodComparisonResult:
    """Результат сравнения различных методов conditioning"""
    comparison_type: str  # "canny", "depth", "segmentation", "scribble"
    
    # Ранжирование методов
    method_rankings: List[Dict[str, Any]] = field(default_factory=list) # [{"method": "opencv_canny", "score": 0.8, "rank": 1}]
    
    # Сравнительные метрики
    quality_comparison: Dict[str, float] = field(default_factory=dict)    # {"opencv_canny": 0.8, "hed_canny": 0.9}
    speed_comparison: Dict[str, int] = field(default_factory=dict)        # Время в мс
    resource_usage: Dict[str, float] = field(default_factory=dict)        # Использование ресурсов
    
    # Рекомендации
    best_method_overall: str = ""
    best_method_for_speed: str = ""
    best_method_for_quality: str = ""
    
    # Анализ различий
    visual_differences_description: str = ""
    use_case_recommendations: Dict[str, str] = field(default_factory=dict) # {"comic_style": "opencv_canny"}


@dataclass
class BatchGenerationResult:
    """Результат пакетной генерации изображений"""
    total_requests: int
    successful_generations: int
    failed_generations: int
    
    # Индивидуальные результаты
    individual_results: List[AIImageResponse] = field(default_factory=list)
    
    # Сводная статистика
    total_processing_time_ms: int = 0
    average_generation_time_ms: float = 0.0
    total_gpu_memory_used_mb: float = 0.0
    
    # Ошибки пакета
    batch_errors: List[str] = field(default_factory=list)
    
    # Анализ эффективности пакетной обработки
    batch_efficiency_score: float = 0.0
    parallel_processing_benefit: float = 0.0  # Выигрыш от параллельной обработки
    
    # Рекомендации для оптимизации
    optimization_suggestions: List[str] = field(default_factory=list)


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
    #   "controlnet_canny": {"loaded": True, "memory_mb": 1200, "load_time_ms": 2000}
    # }
    
    # Использование ресурсов
    total_gpu_memory_used_mb: float = 0.0
    total_gpu_memory_available_mb: float = 0.0
    gpu_utilization_percent: float = 0.0
    
    # Производительность
    average_generation_time_ms: float = 0.0
    total_generations_completed: int = 0
    generations_per_hour: float = 0.0
    
    # Кэш статус
    cache_status: Dict[str, Any] = field(default_factory=dict)
    
    # Проблемы и предупреждения
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class CacheStatusResponse:
    """Ответ на запрос статуса кэша"""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Статус разных типов кэша
    model_cache: Dict[str, Any] = field(default_factory=dict)
    conditioning_cache: Dict[str, Any] = field(default_factory=dict)
    semantic_cache: Dict[str, Any] = field(default_factory=dict)
    
    # Общая статистика
    total_cache_size_mb: float = 0.0
    total_cached_items: int = 0
    cache_hit_rate_percent: float = 0.0
    
    # Эффективность кэша
    memory_savings_mb: float = 0.0
    time_savings_ms: float = 0.0
    
    # Рекомендации по оптимизации
    optimization_suggestions: List[str] = field(default_factory=list)


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
