"""
API request models for writing image generation.
Модели запросов API для генерации изображений написания.
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
    """Запрос на генерацию AI изображения"""
    word: str
    translation: str = ""
    
    # Параметры генерации
    width: int = 512
    height: int = 512    
    batch_size: int = 1

    # отладочная информация
    include_conditioning_images: bool = False
    include_prompt: bool = False
    include_semantic_analysis: bool = False

