"""
Segmentation conditioning generation.
Генерация conditioning на основе сегментации изображений.
"""

import time
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import cv2
from PIL import Image
from skimage import segmentation, measure, morphology

from sklearn.cluster import MeanShift, KMeans

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
        
        # База данных радикалов для radical_segmentation
        self._radical_database = self._init_radical_database()
        
        logger.debug("SegmentationConditioning initialized")
    
    async def generate_from_image(
        self, 
        image: Image.Image, 
        method: str = "simple_segmentation",
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
                    error_message=error_msg,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
            
            # Выбор метода генерации
            if method == "simple_segmentation":
                result_image = await self._simple_segmentation(processed_data['image'], **kwargs)
            elif method == "radical_segmentation":
                result_image = await self._radical_segmentation(processed_data['image'], **kwargs)
            elif method == "semantic_segmentation":
                result_image = await self._semantic_segmentation(processed_data['image'], **kwargs)
            elif method == "color_based_segmentation":
                result_image = await self._color_based_segmentation(processed_data['image'], **kwargs)
            else:
                return ConditioningResult(
                    success=False,
                    error_message=f"Unknown method: {method}",
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
            
            # Проверяем результат
            if result_image is None:
                return ConditioningResult(
                    success=False,
                    error_message=f"Method {method} failed to generate image",
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
            
            result_image = self.wave_distort(result_image, amplitude=5, wavelength=100)
            result_image = self.blur_image(result_image, radius=10)
            result_image = self.add_noise_to_mask(result_image, noise_level=30, mask_threshold=20, mask_is_less_than=False)
            
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
                    'output_size': result_image.size,
                    'parameters_used': kwargs,
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
        method: str = "simple_segmentation",
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
        start_time = time.time()
        
        try:
            # Валидация входных данных
            is_valid, error_msg, processed_data = await self.validate_and_process_inputs(
                character=character, width=width, height=height, **kwargs
            )
            if not is_valid:
                return ConditioningResult(
                    success=False,
                    error_message=error_msg,
                    processing_time_ms=int((time.time() - start_time) * 1000)
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
                error_message=str(e),
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def get_available_methods(self) -> List[str]:
        """Возвращает список доступных методов сегментации."""
        return [
            "simple_segmentation",
            "radical_segmentation",
            "semantic_segmentation",
            "color_based_segmentation",
        ]
    
    def get_method_info(self, method: str) -> Dict[str, Any]:
        """Возвращает информацию о конкретном методе."""
        method_info = {
            "simple_segmentation": {
                "description": "Простая бинарная сегментация",
                "parameters": {
                    "invert": {"type": "bool", "default": False},
                    "gaussian_blur": {"type": "int", "default": 3, "range": [0, 15]}
                },
                "speed": "very_fast",
                "quality": "basic",
                "memory_usage": "very_low",
                "best_for": "basic_separation"
            },
            
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
    
    async def _simple_segmentation(
        self, 
        image: Image.Image,
        invert: bool = False,
        gaussian_blur: int = 3,
        **kwargs
    ) -> Optional[Image.Image]:
        """
        Простая бинарная сегментация.
        """
        try:
            # Конвертация в numpy
            img_array = np.array(image)
            
            # Конвертация в grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Простая пороговая обработка
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            
            if invert:
                binary = 255 - binary
            
            # Опциональное размытие
            if gaussian_blur > 0:
                binary = cv2.GaussianBlur(binary, (gaussian_blur, gaussian_blur), 0)
            
            return Image.fromarray(binary, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error in simple segmentation: {e}")
            return None

    async def _radical_segmentation(
        self, 
        image: Image.Image,
        use_kangxi_radicals: bool = True,
        color_per_radical: bool = True,
        radical_detection_threshold: float = 0.7,
        **kwargs
    ) -> Optional[Image.Image]:
        """Сегментация по радикалам иероглифа."""
        try:
            # Конвертация в numpy
            img_array = np.array(image)
            
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
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
            
        except Exception as e:
            logger.error(f"Error in radical segmentation: {e}")
            return None
    
    async def _semantic_segmentation(
        self, 
        image: Image.Image,
        semantic_classes: List[str] = ["radical", "phonetic", "modifier", "background"],
        context_analysis: bool = True,
        **kwargs
    ) -> Optional[Image.Image]:
        """Семантическая сегментация по смыслу частей иероглифа."""
        try:
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
            
        except Exception as e:
            logger.error(f"Error in semantic segmentation: {e}")
            return None
    
    async def _color_based_segmentation(
        self, 
        image: Image.Image,
        num_clusters: int = 5,
        algorithm: str = "kmeans",
        color_space: str = "RGB",
        **kwargs
    ) -> Optional[Image.Image]:
        """Сегментация на основе кластеризации цветов."""
        try:
            # Конвертация в numpy
            img_array = np.array(image)
            
            # Конвертация цветового пространства
            if color_space == "HSV" and len(img_array.shape) == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
            elif color_space == "LAB" and len(img_array.shape) == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
            
            # Reshape для кластеризации
            if len(img_array.shape) == 3:
                pixel_values = img_array.reshape((-1, 3))
            else:
                # Для grayscale создаем псевдо-3D
                pixel_values = np.stack([img_array.flatten()] * 3, axis=1)
            
            pixel_values = np.float32(pixel_values)
            
            if algorithm == "kmeans" or not SKLEARN_AVAILABLE:
                # K-means кластеризация (OpenCV)
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
                
            elif algorithm == "meanshift" and SKLEARN_AVAILABLE:
                # Mean-shift кластеризация
                ms = MeanShift(bandwidth=30)
                labels = ms.fit_predict(pixel_values)
                segment_map = labels.reshape(img_array.shape[:2])
                
            else:  # watershed
                # Watershed сегментация
                if len(img_array.shape) == 3:
                    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                else:
                    gray = img_array
                
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
            
        except Exception as e:
            logger.error(f"Error in color based segmentation: {e}")
            return None
    
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
        try:
            # Distance transform
            dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
            
            # Находим локальные максимумы
            try:
                from skimage.feature import peak_local_maxima
                peaks = peak_local_maxima(dist_transform, min_distance=20, threshold_abs=0.3)
                markers = np.zeros_like(dist_transform, dtype=np.int32)
                for i, (y, x) in enumerate(peaks):
                    markers[y, x] = i + 1
            except ImportError:
                markers = None
            
            # Применяем watershed
            # Создаем 3-канальное изображение для watershed
            image_3ch = np.stack([binary] * 3, axis=-1)
            
            try:
                segments = segmentation.watershed(-dist_transform, markers, mask=binary)
            except:
                segments = None
            
            # Комбинируем с существующими сегментами
            combined = existing_segments.copy()
            mask = existing_segments == 0
            combined[mask] = (segments[mask] * 32) % 256  # Масштабируем новые сегменты
            
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
        try:
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
                            cv2.floodFill(filled_segments, None, (x, y), int(nearest_color))
            
            return filled_segments
        except Exception as e:
            logger.warning(f"Error filling stroke regions: {e}")
            return segment_map
    
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
        try:
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
        except Exception as e:
            logger.warning(f"Error merging small segments: {e}")
            return segments
    
    def _post_process_segments(self, segments: np.ndarray, min_area: int = 100) -> np.ndarray:
        """Постобработка сегментов - объединение маленьких областей."""
        try:
            # Находим уникальные сегменты и их размеры
            unique_labels, counts = np.unique(segments, return_counts=True)
            
            # Объединяем маленькие сегменты
            for label, count in zip(unique_labels, counts):
                if count < min_area and label != 0:  # Не трогаем фон
                    segments = self._merge_small_segments(segments, label, min_area)
            
            # Перенумеровываем сегменты для непрерывности
            unique_labels = np.unique(segments)
            normalized_segments = np.zeros_like(segments)
            
            for i, label in enumerate(unique_labels):
                normalized_segments[segments == label] = i * (255 // len(unique_labels))
            
            return normalized_segments
        except Exception as e:
            logger.warning(f"Error in post-processing segments: {e}")
            return segments
    
    def _validate_segmentation_result(self, segments: np.ndarray) -> bool:
        """Валидирует результат сегментации."""
        try:
            # Проверяем базовые условия
            if segments is None or segments.size == 0:
                return False
            
            # Проверяем количество уникальных сегментов
            unique_segments = np.unique(segments)
            if len(unique_segments) < 2:
                logger.warning("Segmentation produced too few segments")
                return False
            
            if len(unique_segments) > 50:
                logger.warning("Segmentation produced too many segments")
                return False
            
            # Проверяем распределение размеров сегментов
            _, counts = np.unique(segments, return_counts=True)
            largest_segment_ratio = np.max(counts) / segments.size
            
            if largest_segment_ratio > 0.95:
                logger.warning("One segment dominates the image")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating segmentation result: {e}")
            return False
   