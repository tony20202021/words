"""
API request models for writing image generation.
Модели запросов API для генерации изображений написания.
ОБНОВЛЕНО: Добавлена поддержка пользовательской подсказки hint_writing
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum


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
    MULTI_LAYER_DEPTH = "multi_layer_depth"
    
    # Segmentation methods
    RADICAL_SEGMENTATION = "radical_segmentation"
    STROKE_TYPE_SEGMENTATION = "stroke_type_segmentation"
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
    """
    Запрос на генерацию AI изображения.
    ОБНОВЛЕНО: Добавлена поддержка пользовательской подсказки hint_writing
    """
    word: str
    translation: str = ""
    
    # НОВОЕ: Пользовательская подсказка для AI генерации
    hint_writing: str = ""
    
    # Параметры изображения
    width: int = 512
    height: int = 512    
    batch_size: int = 1
    
    # Стиль генерации
    style: str = "comic"
    
    # AI параметры генерации
    seed: Optional[int] = None
    
    # ControlNet параметры
    conditioning_methods: Optional[Dict[str, str]] = None
    
    # Translation параметры
    include_translation: bool = True
    translation_model: str = "auto"
    translation_cache: bool = True
    
    # Отладочная информация
    include_conditioning_images: bool = False
    include_prompt: bool = False
    
    def __post_init__(self):
        """Валидация и инициализация после создания"""
        # Очистка пустых строк
        self.word = self.word.strip() if self.word else ""
        self.translation = self.translation.strip() if self.translation else ""
        self.hint_writing = self.hint_writing.strip() if self.hint_writing else ""
        
        # Валидация обязательных полей
        if not self.word:
            raise ValueError("Field 'word' cannot be empty")
        
        # Валидация размеров изображения
        if self.width < 64 or self.width > 2048:
            raise ValueError("Width must be between 64 and 2048 pixels")
        if self.height < 64 or self.height > 2048:
            raise ValueError("Height must be between 64 and 2048 pixels")
            
    def has_user_hint(self) -> bool:
        """
        Проверяет есть ли пользовательская подсказка.
        
        Returns:
            bool: True если подсказка не пустая
        """
        return bool(self.hint_writing and self.hint_writing.strip())
    
    def get_effective_translation(self) -> str:
        """
        Возвращает эффективный перевод для использования в промпте.
        Комбинирует основной перевод с пользовательской подсказкой.
        
        Returns:
            str: Комбинированный перевод
        """
        parts = []
        
        if self.translation:
            parts.append(self.translation.strip())
        
        if self.has_user_hint():
            parts.append(f"user hint: {self.hint_writing.strip()}")
        
        return ", ".join(parts) if parts else ""
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертирует запрос в словарь для JSON сериализации.
        
        Returns:
            Dict[str, Any]: Словарь с данными запроса
        """
        return {
            "word": self.word,
            "translation": self.translation,
            "hint_writing": self.hint_writing,
            "width": self.width,
            "height": self.height,
            "batch_size": self.batch_size,
            "style": self.style,
            "seed": self.seed,
            "conditioning_methods": self.conditioning_methods,
            "include_translation": self.include_translation,
            "translation_model": self.translation_model,
            "translation_cache": self.translation_cache,
            "include_conditioning_images": self.include_conditioning_images,
            "include_prompt": self.include_prompt,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIImageRequest':
        """
        Создает запрос из словаря.
        
        Args:
            data: Словарь с данными запроса
            
        Returns:
            AIImageRequest: Объект запроса
        """
        # Извлекаем только известные поля
        known_fields = {
            field.name for field in cls.__dataclass_fields__.values()
        }
        
        filtered_data = {
            key: value for key, value in data.items() 
            if key in known_fields
        }
        
        return cls(**filtered_data)


@dataclass
class AIImageBatchRequest:
    """
    Запрос на пакетную генерацию AI изображений.
    Для обработки нескольких слов одновременно.
    """
    requests: List[AIImageRequest]
    
    # Общие параметры для всего пакета
    batch_processing: bool = True
    max_concurrent: int = 3
    
    def __post_init__(self):
        """Валидация пакетного запроса"""
        if not self.requests:
            raise ValueError("Batch request cannot be empty")
        
        if len(self.requests) > 10:
            raise ValueError("Batch size cannot exceed 10 requests")
        
        if not (1 <= self.max_concurrent <= 5):
            raise ValueError("max_concurrent must be between 1 and 5")
    
    def get_total_words(self) -> int:
        """Возвращает общее количество слов в пакете"""
        return len(self.requests)
    
    def get_words_with_hints(self) -> int:
        """Возвращает количество слов с пользовательскими подсказками"""
        return sum(1 for req in self.requests if req.has_user_hint())
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь"""
        return {
            "requests": [req.to_dict() for req in self.requests],
            "batch_processing": self.batch_processing,
            "max_concurrent": self.max_concurrent
        }
    