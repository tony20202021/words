"""
Segmentation conditioning generation.
Генерация conditioning на основе сегментации изображений.
"""

import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import cv2
from PIL import Image
from sklearn.cluster import KMeans, MeanShift
from scipy import ndimage
from skimage import segmentation, measure, morphology
import logging

from .base_conditioning import BaseConditioning, ConditioningResult, ConditioningConfig
from app.utils.logger import get_module_logger

logger = get_module_logger(__name__)


class SegmentationConditioning(BaseConditioning):
    """
    Генерация segmentation conditioning с различными алгоритмами сегментации.
    """
    
    def __init__(self, config: Optional[ConditioningConfig] = None):
        """
        Инициализация Segmentation conditioning.
        
        Args:
            config: Конфигурация conditioning
        """
        super().__init__(config)
        
        # Инициализация AI моделей для сегментации
        self._sam_model = None
        self._segformer_model = None
        self._model_loading_attempted = False
        
        # База данных радикалов для radical_segmentation
        self._radical_database = self._init_radical_database()
        
        logger.info("SegmentationConditioning initialized")
    
    async def generate_from_image(
        self, 
        image: Image.Image, 
        method: str = "radical_segmentation",
        **kwargs
    ) -> ConditioningResult:
        """
        Генерирует segmentation map из изображения.
        
        Args:
            image: Входное изображение
            method: Метод сегментации
            **kwargs: Дополнительные параметры
            
        Returns:
            ConditioningResult: Результат генерации
        """
        start_time = time.time()
        
        try:
            # Валидация входных данных
            is_valid, error_msg, processed_data = await self.validate_and_process_inputs(
                image=image, **kwargs
            )
            if not is_valid:
                return ConditioningResult(
                    success=False,
                    error_message=error_msg
                )
            
            # Выбор метода генерации
            # TODO - добавить базовый простой метод, как метод по умолчанию, из модуля words/language-learning-bot/writing_images_service/app/ai/ai_image_generator.py, где он описан как fallback
            if method == "radical_segmentation":
                result_image = await self._radical_segmentation(processed_data['image'], **kwargs)
            elif method == "stroke_type_segmentation":
                result_image = await self._stroke_type_segmentation(processed_data['image'], **kwargs)
            elif method == "hierarchical_segmentation":
                result_image = await self._hierarchical_segmentation(processed_data['image'], **kwargs)
            elif method == "semantic_segmentation":
                result_image = await self._semantic_segmentation(processed_data['image'], **kwargs)
            elif method == "ai_segmentation":
                result_image = await self._ai_segmentation(processed_data['image'], **kwargs)
            elif method == "color_based_segmentation":
                result_image = await self._color_based_segmentation(processed_data['image'], **kwargs)
            elif method == "geometric_segmentation":
                result_image = await self._geometric_segmentation(processed_data['image'], **kwargs)
            else:
                return ConditioningResult(
                    success=False,
                    error_message=f"Unknown method: {method}"
                )
            
            # Вычисление времени обработки
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Создание результата
            result = ConditioningResult(
                success=True,
                image=result_image,
                method_used=method,
                processing_time_ms=processing_time_ms,
                metadata={
                    'input_size': image.size,
                    'output_size': result_image.size if result_image else None,
                    'parameters_used': kwargs,
                    'segment_stats': self._analyze_segments(result_image)
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Segmentation generation from image: {e}", exc_info=True)
            return ConditioningResult(
                success=False,
                error_message=str(e),
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def generate_from_text(
        self, 
        character: str, 
        method: str = "radical_segmentation",
        width: int = 512, 
        height: int = 512,
        **kwargs
    ) -> ConditioningResult:
        """
        Генерирует segmentation map из текста (иероглифа).
        
        Args:
            character: Китайский иероглиф
            method: Метод сегментации
            width: Ширина результата
            height: Высота результата
            **kwargs: Дополнительные параметры
            
        Returns:
            ConditioningResult: Результат генерации
        """
        try:
            # Валидация входных данных
            is_valid, error_msg, processed_data = await self.validate_and_process_inputs(
                character=character, width=width, height=height, **kwargs
            )
            if not is_valid:
                return ConditioningResult(
                    success=False,
                    error_message=error_msg
                )
            
            # Рендеринг иероглифа
            rendered_image = await self.render_character(
                character, width, height,
                background_color=(255, 255, 255),
                text_color=(0, 0, 0)
            )
            
            # Генерация segmentation из отрендеренного изображения
            result = await self.generate_from_image(rendered_image, method, **kwargs)
            
            # Обновление метаданных
            if result.metadata:
                result.metadata['source_character'] = character
                result.metadata['rendered_size'] = (width, height)
                
                # Для radical_segmentation добавляем информацию о радикалах
                if method == "radical_segmentation":
                    result.metadata['detected_radicals'] = self._analyze_character_radicals(character)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Segmentation generation from text: {e}", exc_info=True)
            return ConditioningResult(
                success=False,
                error_message=str(e)
            )
    
    def get_available_methods(self) -> List[str]:
        """Возвращает список доступных методов сегментации."""
        return [
            # TODO - добавить базовый простой метод, как метод по умолчанию, из модуля words/language-learning-bot/writing_images_service/app/ai/ai_image_generator.py, где он описан как fallback
            "radical_segmentation",
            "stroke_type_segmentation",
            "hierarchical_segmentation",
            "semantic_segmentation",
            "ai_segmentation",
            "color_based_segmentation",
            "geometric_segmentation"
        ]
    
    def get_method_info(self, method: str) -> Dict[str, Any]:
        """Возвращает информацию о конкретном методе."""
        method_info = {
            # TODO - добавить базовый простой метод, как метод по умолчанию, из модуля words/language-learning-bot/writing_images_service/app/ai/ai_image_generator.py, где он описан как fallback
            "radical_segmentation": {
                "description": "Сегментация по радикалам иероглифа - каждый радикал свой цвет",
                "parameters": {
                    "use_kangxi_radicals": {"type": "bool", "default": True},
                    "color_per_radical": {"type": "bool", "default": True},
                    "radical_detection_threshold": {"type": "float", "default": 0.7, "range": [0.3, 1.0]}
                },
                "speed": "medium",
                "quality": "excellent",
                "memory_usage": "medium",
                "best_for": "chinese_characters"
            },
            
            "stroke_type_segmentation": {
                "description": "Сегментация по типам штрихов (горизонтальные, вертикальные, диагональные)",
                "parameters": {
                    "segment_types": {"type": "list", "default": ["horizontal", "vertical", "diagonal", "curved"]},
                    "angle_tolerance": {"type": "float", "default": 15.0, "range": [5.0, 45.0]},
                    "min_stroke_length": {"type": "int", "default": 10, "range": [5, 50]}
                },
                "speed": "fast",
                "quality": "good",
                "memory_usage": "low",
                "best_for": "stroke_analysis"
            },
            
            "hierarchical_segmentation": {
                "description": "Многоуровневая иерархическая сегментация",
                "parameters": {
                    "levels": {"type": "int", "default": 3, "range": [2, 8]},
                    "merge_threshold": {"type": "float", "default": 0.1, "range": [0.01, 0.5]},
                    "min_segment_size": {"type": "int", "default": 100, "range": [10, 1000]}
                },
                "speed": "slow",
                "quality": "very_good",
                "memory_usage": "high",
                "best_for": "complex_structures"
            },
            
            "semantic_segmentation": {
                "description": "Семантическая сегментация по смыслу частей иероглифа",
                "parameters": {
                    "semantic_classes": {"type": "list", "default": ["radical", "phonetic", "modifier", "background"]},
                    "context_analysis": {"type": "bool", "default": True}
                },
                "speed": "medium",
                "quality": "very_good",
                "memory_usage": "medium",
                "best_for": "meaningful_parts"
            },
            
            "ai_segmentation": {
                "description": "AI сегментация с SAM (Segment Anything Model)",
                "parameters": {
                    "model_type": {"type": "str", "default": "vit_h", "options": ["vit_h", "vit_l", "vit_b"]},
                    "points_per_side": {"type": "int", "default": 16, "range": [8, 64]},
                    "confidence_threshold": {"type": "float", "default": 0.5, "range": [0.1, 0.9]}
                },
                "speed": "slow",
                "quality": "excellent",
                "memory_usage": "very_high",
                "requires_gpu": True,
                "best_for": "precise_segmentation"
            },
            
            "color_based_segmentation": {
                "description": "Сегментация на основе кластеризации цветов",
                "parameters": {
                    "num_clusters": {"type": "int", "default": 5, "range": [2, 20]},
                    "algorithm": {"type": "str", "default": "kmeans", "options": ["kmeans", "meanshift", "watershed"]},
                    "color_space": {"type": "str", "default": "RGB", "options": ["RGB", "HSV", "LAB"]}
                },
                "speed": "fast",
                "quality": "good",
                "memory_usage": "low",
                "best_for": "color_regions"
            },
            
            "geometric_segmentation": {
                "description": "Сегментация по геометрическим примитивам",
                "parameters": {
                    "detect_lines": {"type": "bool", "default": True},
                    "detect_circles": {"type": "bool", "default": True},
                    "detect_rectangles": {"type": "bool", "default": True},
                    "hough_threshold": {"type": "int", "default": 50, "range": [20, 200]}
                },
                "speed": "medium",
                "quality": "good",
                "memory_usage": "medium",
                "best_for": "geometric_shapes"
            }
        }
        
        return method_info.get(method, {})
    
    # Реализация конкретных методов
    # TODO - добавить базовый простой метод, как метод по умолчанию, из модуля words/language-learning-bot/writing_images_service/app/ai/ai_image_generator.py, где он описан как fallback

    async def _radical_segmentation(
        self, 
        image: Image.Image,
        use_kangxi_radicals: bool = True,
        color_per_radical: bool = True,
        radical_detection_threshold: float = 0.7,
        **kwargs
    ) -> Image.Image:
        """Сегментация по радикалам иероглифа."""
        # Конвертация в numpy
        img_array = np.array(image)
        
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Создаем сегментационную карту
        segment_map = np.zeros(gray.shape, dtype=np.uint8)
        
        # Детектируем границы
        edges = cv2.Canny(gray, 50, 150)
        
        current_color = 64
        
        # Детектируем линии
        if detect_lines:
            lines = cv2.HoughLinesP(
                edges, 
                rho=1, 
                theta=np.pi/180, 
                threshold=hough_threshold,
                minLineLength=20,
                maxLineGap=5
            )
            
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    cv2.line(segment_map, (x1, y1), (x2, y2), current_color, 3)
                current_color += 32
        
        # Детектируем окружности
        if detect_circles:
            circles = cv2.HoughCircles(
                gray,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=30,
                param1=50,
                param2=30,
                minRadius=5,
                maxRadius=100
            )
            
            if circles is not None:
                circles = np.round(circles[0, :]).astype("int")
                for (x, y, r) in circles:
                    cv2.circle(segment_map, (x, y), r, current_color, 3)
                current_color += 32
        
        # Детектируем прямоугольники (приблизительно через контуры)
        if detect_rectangles:
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                # Аппроксимируем контур
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Если аппроксимация дает 4 точки, считаем прямоугольником
                if len(approx) == 4:
                    cv2.drawContours(segment_map, [approx], -1, current_color, 3)
        
        # Заполняем области между геометрическими примитивами
        segment_map = self._fill_geometric_regions(segment_map, gray)
        
        # Конвертация в RGB
        return Image.fromarray(segment_map, mode='L').convert('RGB')
    
    # Вспомогательные методы
    
    def _init_radical_database(self) -> Dict[str, Any]:
        """Инициализирует базу данных радикалов Kangxi."""
        # Упрощенная база данных радикалов
        # В полной реализации это должно быть загружено из файла или API
        radical_db = {
            # Основные радикалы с их позициями и характеристиками
            "人": {"position": "left", "strokes": 2, "meaning": "person"},
            "木": {"position": "left", "strokes": 4, "meaning": "tree"},
            "水": {"position": "left", "strokes": 3, "meaning": "water"},
            "火": {"position": "left", "strokes": 4, "meaning": "fire"},
            "土": {"position": "left", "strokes": 3, "meaning": "earth"},
            "金": {"position": "left", "strokes": 8, "meaning": "metal"},
            "日": {"position": "left", "strokes": 4, "meaning": "sun"},
            "月": {"position": "left", "strokes": 4, "meaning": "moon"},
            "心": {"position": "bottom", "strokes": 4, "meaning": "heart"},
            "手": {"position": "left", "strokes": 4, "meaning": "hand"},
            # Добавьте больше радикалов по необходимости
        }
        
        logger.info(f"Initialized radical database with {len(radical_db)} radicals")
        return radical_db
    
    def _analyze_character_radicals(self, character: str) -> List[Dict[str, Any]]:
        """Анализирует радикалы в иероглифе."""
        detected_radicals = []
        
        try:
            # Простой анализ на основе известных радикалов
            for radical, info in self._radical_database.items():
                if radical in character:
                    detected_radicals.append({
                        "radical": radical,
                        "position": info["position"],
                        "strokes": info["strokes"],
                        "meaning": info["meaning"],
                        "confidence": 0.8  # Упрощенная оценка уверенности
                    })
            
            # Если не найдено известных радикалов, пытаемся разложить на компоненты
            if not detected_radicals:
                # TODO: Интеграция с библиотеками анализа иероглифов
                # Например, с cjklib или unihan database
                detected_radicals.append({
                    "radical": character,
                    "position": "whole",
                    "strokes": len(character),
                    "meaning": "unknown",
                    "confidence": 0.3
                })
        
        except Exception as e:
            logger.warning(f"Error analyzing character radicals: {e}")
        
        return detected_radicals
    
    def _generate_segment_colors(self, num_segments: int) -> List[int]:
        """Генерирует цвета для сегментов."""
        if num_segments == 0:
            return [128]
        
        # Равномерно распределяем цвета по диапазону 0-255
        colors = []
        for i in range(num_segments):
            color = int((i / max(num_segments - 1, 1)) * 255)
            colors.append(max(32, color))  # Минимальная яркость для видимости
        
        return colors
    
    def _apply_watershed_segmentation(
        self, 
        binary: np.ndarray, 
        existing_segments: np.ndarray
    ) -> np.ndarray:
        """Применяет watershed сегментацию для дополнительного разделения."""
        # Distance transform
        dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
        
        # Находим локальные максимумы
        local_maxima = morphology.local_maxima(dist_transform, min_distance=20)
        markers = measure.label(local_maxima)
        
        # Применяем watershed
        try:
            # Создаем 3-канальное изображение для watershed
            image_3ch = np.stack([binary] * 3, axis=-1)
            segments = segmentation.watershed(-dist_transform, markers, mask=binary)
            
            # Комбинируем с существующими сегментами
            combined = existing_segments.copy()
            mask = existing_segments == 0
            combined[mask] = segments[mask] * 32  # Масштабируем новые сегменты
            
            return combined
        except Exception as e:
            logger.warning(f"Watershed segmentation failed: {e}")
            return existing_segments
    
    def _fill_stroke_regions(
        self, 
        segment_map: np.ndarray, 
        gray: np.ndarray
    ) -> np.ndarray:
        """Заполняет области между штрихами."""
        # Создаем маску незаполненных областей
        unfilled_mask = segment_map == 0
        
        # Применяем морфологические операции для заполнения
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        filled_segments = cv2.morphologyEx(segment_map, cv2.MORPH_CLOSE, kernel)
        
        # Используем flood fill для заполнения больших областей
        h, w = segment_map.shape
        for y in range(0, h, 20):  # Сэмплируем каждые 20 пикселей
            for x in range(0, w, 20):
                if unfilled_mask[y, x] and gray[y, x] < 200:  # Не фон
                    # Находим ближайший сегмент
                    distances = []
                    for seg_y in range(max(0, y-30), min(h, y+30)):
                        for seg_x in range(max(0, x-30), min(w, x+30)):
                            if segment_map[seg_y, seg_x] > 0:
                                dist = np.sqrt((y-seg_y)**2 + (x-seg_x)**2)
                                distances.append((dist, segment_map[seg_y, seg_x]))
                    
                    if distances:
                        # Присваиваем цвет ближайшего сегмента
                        _, nearest_color = min(distances)
                        cv2.floodFill(filled_segments, None, (x, y), nearest_color)
        
        return filled_segments
    
    def _fill_geometric_regions(
        self, 
        segment_map: np.ndarray, 
        gray: np.ndarray
    ) -> np.ndarray:
        """Заполняет области между геометрическими примитивами."""
        # Аналогично _fill_stroke_regions, но с адаптацией для геометрических форм
        return self._fill_stroke_regions(segment_map, gray)
    
    def _merge_small_segments(
        self, 
        segments: np.ndarray, 
        small_label: int, 
        threshold: float
    ) -> np.ndarray:
        """Объединяет маленькие сегменты с соседними."""
        # Находим соседние сегменты
        mask = segments == small_label
        
        # Расширяем маску для поиска соседей
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        expanded_mask = cv2.dilate(mask.astype(np.uint8), kernel)
        
        # Находим уникальные соседние сегменты
        neighbor_values = segments[expanded_mask > 0]
        unique_neighbors = np.unique(neighbor_values)
        unique_neighbors = unique_neighbors[unique_neighbors != small_label]
        
        if len(unique_neighbors) > 0:
            # Выбираем наиболее часто встречающегося соседа
            neighbor_counts = [(np.sum(neighbor_values == neighbor), neighbor) 
                             for neighbor in unique_neighbors]
            _, best_neighbor = max(neighbor_counts)
            
            # Объединяем сегменты
            segments[mask] = best_neighbor
        
        return segments
    
    async def _load_segmentation_models(self):
        """Загружает модели для AI сегментации."""
        try:
            self._model_loading_attempted = True
            
            # TODO: Реализация загрузки SAM модели
            # Пример с segment-anything:
            # from segment_anything import sam_model_registry, SamPredictor
            # sam_checkpoint = "path/to/sam_checkpoint.pth"
            # model_type = "vit_h"
            # device = "cuda" if torch.cuda.is_available() else "cpu"
            # sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
            # sam.to(device=device)
            # self._sam_model = sam
            
            # Пример с Segformer:
            # from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
            # self._segformer_processor = SegformerImageProcessor.from_pretrained("nvidia/segformer-b5-finetuned-ade-640-640")
            # self._segformer_model = SegformerForSemanticSegmentation.from_pretrained("nvidia/segformer-b5-finetuned-ade-640-640")
            
            logger.info("Segmentation models loading not implemented yet - using fallback methods")
            self._sam_model = None
            self._segformer_model = None
            
        except Exception as e:
            logger.warning(f"Could not load segmentation models: {e}")
            self._sam_model = None
            # self._segformer_model = None(img_array.shape) == 3:
            # gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = None
        
        # Создаем сегментационную карту
        segment_map = np.zeros(gray.shape, dtype=np.uint8)
        
        # Анализируем структуру для выделения потенциальных радикалов
        # Находим связанные компоненты
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        
        # Морфологические операции для очистки
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # Находим контуры (потенциальные радикалы)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Анализируем каждый контур
        colors = self._generate_segment_colors(len(contours))
        
        for i, contour in enumerate(contours):
            # Фильтруем слишком маленькие контуры
            area = cv2.contourArea(contour)
            if area < 50:  # Минимальная площадь
                continue
            
            # Создаем маску для текущего "радикала"
            mask = np.zeros(gray.shape, dtype=np.uint8)
            cv2.fillPoly(mask, [contour], 255)
            
            # Присваиваем цвет сегменту
            color_value = colors[i % len(colors)]
            segment_map[mask > 0] = color_value
        
        # Если сегментов мало, применяем дополнительную сегментацию
        if len(contours) < 2:
            # Используем watershed для дополнительного разделения
            segment_map = self._apply_watershed_segmentation(binary, segment_map)
        
        # Конвертация в RGB
        return Image.fromarray(segment_map, mode='L').convert('RGB')
    
    async def _stroke_type_segmentation(
        self, 
        image: Image.Image,
        segment_types: List[str] = ["horizontal", "vertical", "diagonal", "curved"],
        angle_tolerance: float = 15.0,
        min_stroke_length: int = 10,
        **kwargs
    ) -> Image.Image:
        """Сегментация по типам штрихов."""
        # Конвертация в numpy
        img_array = np.array(image)
        
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Создаем сегментационную карту
        segment_map = np.zeros(gray.shape, dtype=np.uint8)
        
        # Детектируем границы
        edges = cv2.Canny(gray, 50, 150)
        
        # Детектируем линии с помощью Hough Transform
        lines = cv2.HoughLinesP(
            edges, 
            rho=1, 
            theta=np.pi/180, 
            threshold=50,
            minLineLength=min_stroke_length,
            maxLineGap=5
        )
        
        if lines is not None:
            # Классифицируем линии по типам
            for line in lines:
                x1, y1, x2, y2 = line[0]
                
                # Вычисляем угол линии
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                angle = abs(angle)
                
                # Определяем тип штриха
                if angle <= angle_tolerance or angle >= (180 - angle_tolerance):
                    stroke_type = "horizontal"
                    color = 64  # Темно-серый
                elif abs(angle - 90) <= angle_tolerance:
                    stroke_type = "vertical"
                    color = 128  # Средне-серый
                elif 30 <= angle <= 60 or 120 <= angle <= 150:
                    stroke_type = "diagonal"
                    color = 192  # Светло-серый
                else:
                    stroke_type = "curved"
                    color = 255  # Белый
                
                # Рисуем линию на карте сегментации
                if stroke_type in segment_types:
                    cv2.line(segment_map, (x1, y1), (x2, y2), color, 3)
        
        # Заполняем области между линиями
        segment_map = self._fill_stroke_regions(segment_map, gray)
        
        # Конвертация в RGB
        return Image.fromarray(segment_map, mode='L').convert('RGB')
    
    async def _hierarchical_segmentation(
        self, 
        image: Image.Image,
        levels: int = 3,
        merge_threshold: float = 0.1,
        min_segment_size: int = 100,
        **kwargs
    ) -> Image.Image:
        """Многоуровневая иерархическая сегментация."""
        try:
            # Конвертация в numpy
            img_array = np.array(image)
            
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Начинаем с базовой сегментации
            # Используем SLIC superpixels как основу
            segments = segmentation.slic(
                img_array if len(img_array.shape) == 3 else np.stack([gray]*3, axis=-1),
                n_segments=50,
                compactness=10,
                sigma=1
            )
            
            # Применяем иерархическое слияние
            for level in range(levels):
                # Вычисляем характеристики сегментов
                segment_props = measure.regionprops(segments + 1, gray)
                
                # Находим соседние сегменты для потенциального слияния
                for prop in segment_props:
                    if prop.area < min_segment_size:
                        # Объединяем маленькие сегменты с соседями
                        segments = self._merge_small_segments(segments, prop.label - 1, merge_threshold)
            
            # Нормализуем значения сегментов
            unique_segments = np.unique(segments)
            segment_map = np.zeros_like(segments, dtype=np.uint8)
            
            for i, seg_val in enumerate(unique_segments):
                color_value = int((i / len(unique_segments)) * 255)
                segment_map[segments == seg_val] = color_value
            
            # Конвертация в RGB
            return Image.fromarray(segment_map, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error in hierarchical segmentation: {e}")
            # Fallback к простой сегментации
            return await self._color_based_segmentation(image, **kwargs)
    
    async def _semantic_segmentation(
        self, 
        image: Image.Image,
        semantic_classes: List[str] = ["radical", "phonetic", "modifier", "background"],
        context_analysis: bool = True,
        **kwargs
    ) -> Image.Image:
        """Семантическая сегментация по смыслу частей иероглифа."""
        # Упрощенная реализация семантической сегментации
        # В будущем можно интегрировать с моделями понимания иероглифов
        
        # Пока используем комбинацию геометрического и позиционного анализа
        img_array = np.array(image)
        
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Создаем сегментационную карту
        segment_map = np.zeros(gray.shape, dtype=np.uint8)
        
        # Анализируем позиционную структуру иероглифа
        h, w = gray.shape
        
        # Разделяем на потенциальные семантические зоны
        # Левая часть - часто радикал
        left_region = gray[:, :w//2]
        # Правая часть - часто фонетический компонент
        right_region = gray[:, w//2:]
        # Верхняя часть - модификаторы
        top_region = gray[:h//3, :]
        # Нижняя часть - основание
        bottom_region = gray[2*h//3:, :]
        
        # Анализируем плотность штрихов в каждой зоне
        def analyze_stroke_density(region):
            _, binary = cv2.threshold(region, 127, 255, cv2.THRESH_BINARY_INV)
            return np.sum(binary) / region.size
        
        left_density = analyze_stroke_density(left_region)
        right_density = analyze_stroke_density(right_region)
        top_density = analyze_stroke_density(top_region)
        bottom_density = analyze_stroke_density(bottom_region)
        
        # Присваиваем семантические метки на основе анализа
        if left_density > 0.1:  # Достаточно штрихов слева
            segment_map[:, :w//2] = 64  # Радикал
        
        if right_density > 0.1:  # Достаточно штрихов справа
            segment_map[:, w//2:] = 128  # Фонетический компонент
        
        if top_density > 0.05:  # Модификаторы сверху
            segment_map[:h//3, :] = np.maximum(segment_map[:h//3, :], 192)
        
        # Фон
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        segment_map[binary == 0] = 32  # Фон
        
        # Конвертация в RGB
        return Image.fromarray(segment_map, mode='L').convert('RGB')
    
    async def _ai_segmentation(
        self, 
        image: Image.Image,
        model_type: str = "vit_h",
        points_per_side: int = 16,
        confidence_threshold: float = 0.5,
        **kwargs
    ) -> Image.Image:
        """AI сегментация с использованием SAM."""
        try:
            # Попытка загрузки модели
            if not self._model_loading_attempted:
                await self._load_segmentation_models()
            
            if self._sam_model is None:
                logger.warning("SAM model not available, falling back to color-based segmentation")
                return await self._color_based_segmentation(image, **kwargs)
            
            # TODO: Реализация SAM inference
            # Пример с segment-anything:
            # from segment_anything import SamPredictor
            # predictor = SamPredictor(self._sam_model)
            # predictor.set_image(np.array(image))
            # 
            # # Автоматическая генерация точек
            # input_points = self._generate_input_points(image, points_per_side)
            # input_labels = np.ones(len(input_points))
            # 
            # masks, scores, logits = predictor.predict(
            #     point_coords=input_points,
            #     point_labels=input_labels,
            #     multimask_output=True,
            # )
            # 
            # # Комбинируем маски
            # combined_mask = self._combine_sam_masks(masks, scores, confidence_threshold)
            # return Image.fromarray(combined_mask, mode='L').convert('RGB')
            
            # Пока используем fallback
            logger.info("SAM inference not implemented yet, using color-based segmentation")
            return await self._color_based_segmentation(image, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in AI segmentation: {e}")
            return await self._color_based_segmentation(image, **kwargs)
    
    async def _color_based_segmentation(
        self, 
        image: Image.Image,
        num_clusters: int = 5,
        algorithm: str = "kmeans",
        color_space: str = "RGB",
        **kwargs
    ) -> Image.Image:
        """Сегментация на основе кластеризации цветов."""
        # Конвертация в numpy
        img_array = np.array(image)
        
        # Конвертация цветового пространства
        if color_space == "HSV":
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        elif color_space == "LAB":
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
        
        # Reshape для кластеризации
        pixel_values = img_array.reshape((-1, 3))
        pixel_values = np.float32(pixel_values)
        
        if algorithm == "kmeans":
            # K-means кластеризация
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
            _, labels, centers = cv2.kmeans(
                pixel_values, 
                num_clusters, 
                None, 
                criteria, 
                10, 
                cv2.KMEANS_RANDOM_CENTERS
            )
            
            # Создаем сегментационную карту
            segment_map = labels.reshape(img_array.shape[:2])
            
        elif algorithm == "meanshift":
            # Mean-shift кластеризация
            ms = MeanShift(bandwidth=30)
            labels = ms.fit_predict(pixel_values)
            segment_map = labels.reshape(img_array.shape[:2])
            
        else:  # watershed
            # Watershed сегментация
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY) if len(img_array.shape) == 3 else img_array
            
            # Находим маркеры
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
            kernel = np.ones((3, 3), np.uint8)
            sure_bg = cv2.dilate(binary, kernel, iterations=3)
            
            dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
            _, sure_fg = cv2.threshold(dist_transform, 0.7 * dist_transform.max(), 255, 0)
            sure_fg = np.uint8(sure_fg)
            
            unknown = cv2.subtract(sure_bg, sure_fg)
            
            # Маркеры
            _, markers = cv2.connectedComponents(sure_fg)
            markers = markers + 1
            markers[unknown == 255] = 0
            
            # Watershed
            img_for_watershed = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR) if len(img_array.shape) == 3 else cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
            markers = cv2.watershed(img_for_watershed, markers)
            segment_map = markers
        
        # Нормализация значений сегментов
        unique_labels = np.unique(segment_map)
        normalized_map = np.zeros_like(segment_map, dtype=np.uint8)
        
        for i, label in enumerate(unique_labels):
            color_value = int((i / len(unique_labels)) * 255)
            normalized_map[segment_map == label] = color_value
        
        # Конвертация в RGB
        return Image.fromarray(normalized_map, mode='L').convert('RGB')
    
    async def _geometric_segmentation(
        self, 
        image: Image.Image,
        detect_lines: bool = True,
        detect_circles: bool = True,
        detect_rectangles: bool = True,
        hough_threshold: int = 50,
        **kwargs
    ) -> Image.Image:
        """Сегментация по геометрическим примитивам."""
        # Конвертация в numpy
        img_array = np.array(image)
        
        if len
        