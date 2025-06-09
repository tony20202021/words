"""
API request models for writing image generation.
Модели запросов API для генерации изображений написания.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum


class AIGenerationStyle(str, Enum):
    """Поддерживаемые стили AI генерации"""
    COMIC = "comic"
    WATERCOLOR = "watercolor"
    REALISTIC = "realistic"
    ANIME = "anime"
    CARTOON = "cartoon"
    TRADITIONAL = "traditional"


class ConditioningMethod(str, Enum):
    """Методы генерации conditioning"""
    # Canny methods
    OPENCV_CANNY = "opencv_canny"
    HED_CANNY = "hed_canny"
    STRUCTURED_EDGE = "structured_edge_detection"
    MULTI_SCALE_CANNY = "multi_scale_canny"
    ADAPTIVE_CANNY = "adaptive_canny"
    
    # Depth methods
    STROKE_THICKNESS = "stroke_thickness_depth"
    DISTANCE_TRANSFORM = "distance_transform_depth"
    MORPHOLOGICAL_DEPTH = "morphological_depth"
    AI_DEPTH_ESTIMATION = "ai_depth_estimation"
    SYNTHETIC_3D = "synthetic_3d_depth"
    MULTI_LAYER_DEPTH = "multi_layer_depth"
    
    # Segmentation methods
    RADICAL_SEGMENTATION = "radical_segmentation"
    STROKE_TYPE_SEGMENTATION = "stroke_type_segmentation"
    HIERARCHICAL_SEGMENTATION = "hierarchical_segmentation"
    SEMANTIC_SEGMENTATION = "semantic_segmentation"
    AI_SEGMENTATION = "ai_segmentation"
    COLOR_BASED_SEGMENTATION = "color_based_segmentation"
    GEOMETRIC_SEGMENTATION = "geometric_segmentation"
    
    # Scribble methods
    SKELETONIZATION = "skeletonization_scribble"
    MORPHOLOGICAL_SIMPLIFICATION = "morphological_simplification"
    VECTORIZATION_SIMPLIFICATION = "vectorization_simplification"
    AI_SKETCH_GENERATION = "ai_sketch_generation"
    HAND_DRAWN_SIMULATION = "hand_drawn_simulation"
    MULTI_LEVEL_ABSTRACTION = "multi_level_abstraction"
    STYLE_AWARE_SCRIBBLE = "style_aware_scribble"


@dataclass
class AIImageRequest:
    """Запрос на генерацию AI изображения"""
    word: str
    translation: str = ""
    language: str = "chinese"
    style: AIGenerationStyle = AIGenerationStyle.COMIC
    
    # Multi-ControlNet настройки
    conditioning_weights: Optional[Dict[str, float]] = None
    conditioning_methods: Optional[Dict[str, List[ConditioningMethod]]] = None
    
    # Параметры генерации
    width: int = 1024
    height: int = 1024
    num_inference_steps: int = 30
    guidance_scale: float = 7.5
    negative_prompt: Optional[str] = None
    
    # Дополнительные параметры
    include_conditioning_images: bool = False
    include_prompt: bool = False
    include_semantic_analysis: bool = False
    seed: Optional[int] = None
    batch_size: int = 1
    
    # Постобработка
    enable_postprocessing: bool = True
    custom_postprocessing_filters: Optional[List[str]] = None
    
    def __post_init__(self):
        """Валидация и установка значений по умолчанию"""
        if self.conditioning_weights is None:
            self.conditioning_weights = {
                "canny": 0.8,
                "depth": 0.6,
                "segmentation": 0.5,
                "scribble": 0.4
            }
        
        if self.conditioning_methods is None:
            self.conditioning_methods = {
                "canny": [ConditioningMethod.OPENCV_CANNY],
                "depth": [ConditioningMethod.STROKE_THICKNESS],
                "segmentation": [ConditioningMethod.RADICAL_SEGMENTATION],
                "scribble": [ConditioningMethod.SKELETONIZATION]
            }


@dataclass
class MultiConditioningRequest:
    """Запрос на генерацию множественных conditioning изображений"""
    character: str
    methods: Dict[str, List[ConditioningMethod]]
    
    # Параметры изображения
    width: int = 512
    height: int = 512
    
    # Параметры методов
    method_parameters: Optional[Dict[str, Dict[str, Any]]] = None
    
    # Дополнительные опции
    return_timing_info: bool = True
    return_method_comparison: bool = False
    
    def __post_init__(self):
        """Установка параметров по умолчанию"""
        if self.method_parameters is None:
            self.method_parameters = {}


@dataclass
class SemanticAnalysisRequest:
    """Запрос на семантический анализ иероглифа"""
    character: str
    
    # Опции анализа
    include_etymology: bool = True
    include_radical_analysis: bool = True
    include_visual_associations: bool = True
    include_context_analysis: bool = True
    
    # Языковые настройки
    target_language: str = "en"  # Язык для переводов и описаний
    include_pronunciations: bool = True
    
    # Глубина анализа
    analysis_depth: str = "full"  # minimal, standard, full, comprehensive
    
    # Кэширование
    use_cache: bool = True
    cache_ttl: Optional[int] = None


@dataclass
class PromptTestRequest:
    """Запрос для тестирования генерации промптов"""
    character: str
    translation: str
    style: AIGenerationStyle
    
    # Опции промпта
    include_semantic_analysis: bool = True
    include_visual_elements: bool = True
    include_cultural_context: bool = True
    
    # Варианты промптов
    generate_variations: bool = False
    num_variations: int = 3
    
    # Анализ промпта
    analyze_prompt_elements: bool = True
    estimate_generation_quality: bool = False


@dataclass 
class BatchAIImageRequest:
    """Пакетный запрос на генерацию AI изображений"""
    requests: List[AIImageRequest]
    
    # Настройки пакетной обработки
    parallel_processing: bool = True
    max_concurrent: int = 2
    
    # Общие настройки для всех запросов
    common_style: Optional[AIGenerationStyle] = None
    common_conditioning_weights: Optional[Dict[str, float]] = None
    
    # Результаты
    return_individual_results: bool = True
    return_batch_summary: bool = True
    
    def __post_init__(self):
        """Валидация пакетного запроса"""
        if not self.requests:
            raise ValueError("Batch request must contain at least one individual request")
        
        if len(self.requests) > 10:
            raise ValueError("Batch size cannot exceed 10 requests")
        
        # Применяем общие настройки к отдельным запросам
        if self.common_style:
            for request in self.requests:
                if request.style == AIGenerationStyle.COMIC:  # Default
                    request.style = self.common_style
        
        if self.common_conditioning_weights:
            for request in self.requests:
                if request.conditioning_weights is None:
                    request.conditioning_weights = self.common_conditioning_weights.copy()


@dataclass
class ModelStatusRequest:
    """Запрос статуса AI моделей"""
    include_memory_usage: bool = True
    include_model_details: bool = False
    include_performance_stats: bool = False
    
    # Конкретные модели для проверки
    specific_models: Optional[List[str]] = None


@dataclass
class CacheManagementRequest:
    """Запрос управления кэшем"""
    action: str  # "clear", "status", "optimize", "cleanup"
    
    # Типы кэша
    cache_types: Optional[List[str]] = None  # ["model", "conditioning", "semantic"]
    
    # Параметры очистки
    max_age_hours: Optional[int] = None
    max_size_mb: Optional[int] = None
    
    # Статистика
    include_detailed_stats: bool = True


# Дополнительные валидационные модели
@dataclass
class ConditioningMethodParams:
    """Параметры для конкретного метода conditioning"""
    method: ConditioningMethod
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Метаданные
    expected_quality: str = "medium"  # low, medium, high
    processing_time_estimate: Optional[int] = None  # в миллисекундах


@dataclass
class StyleConfiguration:
    """Конфигурация стиля для генерации"""
    style_name: AIGenerationStyle
    
    # Веса conditioning
    conditioning_weights: Dict[str, float]
    
    # Промпт модификаторы
    prompt_modifiers: List[str] = field(default_factory=list)
    negative_prompt_additions: List[str] = field(default_factory=list)
    
    # Постобработка
    postprocessing_filters: List[str] = field(default_factory=list)
    
    # Параметры генерации
    generation_params: Dict[str, Any] = field(default_factory=dict)


# Предустановленные конфигурации стилей
PRESET_STYLE_CONFIGS = {
    AIGenerationStyle.COMIC: StyleConfiguration(
        style_name=AIGenerationStyle.COMIC,
        conditioning_weights={"canny": 0.9, "depth": 0.5, "segmentation": 0.7, "scribble": 0.3},
        prompt_modifiers=["bold outlines", "vibrant colors", "pop art style"],
        negative_prompt_additions=["realistic", "photographic", "blurry"],
        postprocessing_filters=["enhance_contrast", "sharpen_edges", "boost_saturation"],
        generation_params={"guidance_scale": 8.0}
    ),
    
    AIGenerationStyle.WATERCOLOR: StyleConfiguration(
        style_name=AIGenerationStyle.WATERCOLOR,
        conditioning_weights={"canny": 0.4, "depth": 0.3, "segmentation": 0.3, "scribble": 0.8},
        prompt_modifiers=["soft edges", "bleeding colors", "artistic brushstrokes"],
        negative_prompt_additions=["sharp edges", "digital art", "3d render"],
        postprocessing_filters=["soft_blur", "edge_smoothing", "color_bleeding_effect"],
        generation_params={"guidance_scale": 6.5}
    ),
    
    AIGenerationStyle.REALISTIC: StyleConfiguration(
        style_name=AIGenerationStyle.REALISTIC,
        conditioning_weights={"canny": 0.8, "depth": 0.9, "segmentation": 0.6, "scribble": 0.2},
        prompt_modifiers=["photorealistic", "detailed textures", "natural lighting"],
        negative_prompt_additions=["cartoon", "anime", "stylized"],
        postprocessing_filters=["noise_reduction", "detail_enhancement", "color_correction"],
        generation_params={"guidance_scale": 7.5, "num_inference_steps": 40}
    ),
    
    AIGenerationStyle.ANIME: StyleConfiguration(
        style_name=AIGenerationStyle.ANIME,
        conditioning_weights={"canny": 0.7, "depth": 0.4, "segmentation": 0.8, "scribble": 0.5},
        prompt_modifiers=["cell shading", "bright colors", "expressive style"],
        negative_prompt_additions=["realistic", "dark", "gloomy"],
        postprocessing_filters=["enhance_contrast", "boost_saturation"],
        generation_params={"guidance_scale": 7.0}
    )
}
