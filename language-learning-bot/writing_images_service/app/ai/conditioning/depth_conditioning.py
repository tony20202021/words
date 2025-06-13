"""
Depth map conditioning generation.
Генерация conditioning на основе карт глубины.
"""

import time
from typing import Dict, Any, Optional, List
import numpy as np
import cv2
from PIL import Image

from .base_conditioning import BaseConditioning, ConditioningResult, ConditioningConfig
from app.utils.logger import get_module_logger

logger = get_module_logger(__name__)


class DepthConditioning(BaseConditioning):
    """
    Генерация depth map conditioning с различными алгоритмами создания карт глубины.
    """
    
    def __init__(self, config: Optional[ConditioningConfig] = None):
        """
        Инициализация Depth conditioning.
        
        Args:
            config: Конфигурация conditioning
        """
        super().__init__(config)
        
        logger.debug("DepthConditioning initialized")
    
    async def generate_from_image(
        self, 
        image: Image.Image, 
        method: str = "simple_depth",
        **kwargs
    ) -> ConditioningResult:
        """
        Генерирует depth map из изображения.
        
        Args:
            image: Входное изображение
            method: Метод генерации depth map
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
            if method == "simple_depth":
                result_image = await self._simple_depth(processed_data['image'], **kwargs)
            elif method == "stroke_thickness_depth":
                result_image = await self._stroke_thickness_depth(processed_data['image'], **kwargs)
            elif method == "distance_transform_depth":
                result_image = await self._distance_transform_depth(processed_data['image'], **kwargs)
            elif method == "morphological_depth":
                result_image = await self._morphological_depth(processed_data['image'], **kwargs)
            elif method == "multi_layer_depth":
                result_image = await self._multi_layer_depth(processed_data['image'], **kwargs)
            else:
                return ConditioningResult(
                    success=False,
                    error_message=f"Unknown method: {method}"
                )
            
            result_image = self.wave_distort(result_image, amplitude=5, wavelength=100)
            result_image = self.blur_image(result_image, radius=10)
            result_image = self.add_noise_to_mask(result_image, noise_level=30, mask_threshold=50, mask_is_less_than=False)
            
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
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Depth generation from image: {e}", exc_info=True)
            return ConditioningResult(
                success=False,
                error_message=str(e),
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def generate_from_text(
        self, 
        character: str, 
        method: str = "simple_depth",
        width: int = 512, 
        height: int = 512,
        **kwargs
    ) -> ConditioningResult:
        """
        Генерирует depth map из текста (иероглифа).
        
        Args:
            character: Китайский иероглиф
            method: Метод генерации depth map
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
            
            # Генерация depth map из отрендеренного изображения
            result = await self.generate_from_image(rendered_image, method, **kwargs)
            
            # Обновление метаданных
            if result.metadata:
                result.metadata['source_character'] = character
                result.metadata['rendered_size'] = (width, height)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Depth generation from text: {e}", exc_info=True)
            return ConditioningResult(
                success=False,
                error_message=str(e)
            )
    
    def get_available_methods(self) -> List[str]:
        """Возвращает список доступных методов depth generation."""
        return [
            "simple_depth",
            "stroke_thickness_depth",
            "distance_transform_depth",
            "morphological_depth",
            "multi_layer_depth"
        ]
    
    def get_method_info(self, method: str) -> Dict[str, Any]:
        """Возвращает информацию о конкретном методе."""
        method_info = {
            "simple_depth": {
                "description": "Простая инверсия для имитации глубины (базовый fallback)",
                "parameters": {
                    "invert": {"type": "bool", "default": True},
                    "gaussian_blur": {"type": "int", "default": 3, "range": [0, 15]}
                },
                "speed": "very_fast",
                "quality": "basic",
                "memory_usage": "very_low",
                "is_fallback": True
            },
            
            "stroke_thickness_depth": {
                "description": "Depth на основе толщины штрихов - толстые штрихи ближе",
                "parameters": {
                    "normalize": {"type": "bool", "default": True},
                    "invert": {"type": "bool", "default": False},
                    "gaussian_blur": {"type": "int", "default": 3, "range": [0, 15]},
                    "contrast_enhancement": {"type": "float", "default": 1.2, "range": [0.5, 3.0]}
                },
                "speed": "fast",
                "quality": "good",
                "memory_usage": "low"
            },
            
            "distance_transform_depth": {
                "description": "Depth на основе расстояния от границ объектов",
                "parameters": {
                    "distance_type": {"type": "str", "default": "euclidean", "options": ["euclidean", "manhattan", "chessboard"]},
                    "normalize": {"type": "bool", "default": True},
                    "smooth_factor": {"type": "float", "default": 1.0, "range": [0.1, 5.0]}
                },
                "speed": "fast",
                "quality": "very_good",
                "memory_usage": "low"
            },
            
            "morphological_depth": {
                "description": "Depth с использованием морфологических операций",
                "parameters": {
                    "erosion_iterations": {"type": "int", "default": 3, "range": [1, 10]},
                    "dilation_iterations": {"type": "int", "default": 2, "range": [1, 10]},
                    "kernel_size": {"type": "int", "default": 5, "range": [3, 15]},
                    "depth_levels": {"type": "int", "default": 8, "range": [4, 16]}
                },
                "speed": "medium",
                "quality": "good",
                "memory_usage": "medium"
            },
            
            "multi_layer_depth": {
                "description": "Многослойная depth карта для сложных композиций",
                "parameters": {
                    "layers": {"type": "list", "default": ["stroke", "radical", "background"]},
                    "layer_separation": {"type": "float", "default": 0.3, "range": [0.1, 1.0]},
                    "blend_mode": {"type": "str", "default": "linear", "options": ["linear", "exponential", "sigmoid"]}
                },
                "speed": "slow",
                "quality": "excellent",
                "memory_usage": "high"
            }
        }
        
        return method_info.get(method, {})
    
    # Реализация конкретных методов
    
    async def _simple_depth(
        self, 
        image: Image.Image,
        invert: bool = True,
        gaussian_blur: int = 3,
        **kwargs
    ) -> Image.Image:
        """
        Простая инверсия для имитации глубины (базовый fallback метод).
        Перенесен из ai_image_generator._create_fallback_conditioning.
        """
        try:
            # Конвертация в numpy
            img_array = np.array(image)
            
            # Конвертация в grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Простая инверсия для имитации глубины
            if invert:
                depth = 255 - gray
            else:
                depth = gray
            
            # Опциональное размытие
            if gaussian_blur > 0:
                depth = cv2.GaussianBlur(depth, (gaussian_blur, gaussian_blur), 0)
            
            return Image.fromarray(depth, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error in simple depth: {e}")
            return None

    async def _stroke_thickness_depth(
        self, 
        image: Image.Image,
        normalize: bool = True,
        invert: bool = False,
        gaussian_blur: int = 3,
        contrast_enhancement: float = 1.2,
        **kwargs
    ) -> Image.Image:
        """Depth map на основе толщины штрихов."""
        try:
            # Конвертация в numpy
            img_array = np.array(image)
            
            # Конвертация в grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Инвертируем для работы с черными штрихами на белом фоне
            gray = 255 - gray
            
            # Морфологические операции для анализа толщины
            # Создаем структурирующие элементы разного размера
            depth_map = np.zeros_like(gray, dtype=np.float32)
            
            for kernel_size in range(3, 15, 2):
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
                
                # Эрозия для выделения штрихов определенной толщины
                eroded = cv2.erode(gray, kernel, iterations=1)
                
                # Добавляем к карте глубины с весом, зависящим от размера ядра
                weight = kernel_size / 15.0  # Больше ядро = больше глубина
                depth_map += eroded.astype(np.float32) * weight
            
            # Нормализация
            if normalize:
                depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min() + 1e-8)
                depth_map = depth_map * 255
            
            # Инверсия если нужно
            if invert:
                depth_map = 255 - depth_map
            
            # Усиление контраста
            depth_map = np.clip(depth_map * contrast_enhancement, 0, 255)
            
            # Гауссово размытие для сглаживания
            if gaussian_blur > 0:
                depth_map = cv2.GaussianBlur(depth_map, (gaussian_blur, gaussian_blur), 0)
            
            # Конвертация в RGB
            depth_map = depth_map.astype(np.uint8)
            return Image.fromarray(depth_map, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error in stroke thickness depth: {e}")
            return await self._create_emergency_fallback(image)
    
    async def _distance_transform_depth(
        self, 
        image: Image.Image,
        distance_type: str = "euclidean",
        normalize: bool = True,
        smooth_factor: float = 1.0,
        **kwargs
    ) -> Image.Image:
        """Depth map на основе distance transform."""
        try:
            # Конвертация в numpy
            img_array = np.array(image)
            
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Создаем бинарную маску (объекты vs фон)
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
            
            # Distance transform
            if distance_type == "euclidean":
                dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
            elif distance_type == "manhattan":
                dist_transform = cv2.distanceTransform(binary, cv2.DIST_L1, 3)
            elif distance_type == "chessboard":
                dist_transform = cv2.distanceTransform(binary, cv2.DIST_C, 3)
            else:
                dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
            
            # Сглаживание
            if smooth_factor > 0:
                kernel_size = int(smooth_factor * 2) * 2 + 1  # Нечетное число
                dist_transform = cv2.GaussianBlur(dist_transform, (kernel_size, kernel_size), smooth_factor)
            
            # Нормализация
            if normalize:
                dist_transform = (dist_transform - dist_transform.min()) / (dist_transform.max() - dist_transform.min() + 1e-8)
                dist_transform = dist_transform * 255
            
            # Конвертация в RGB
            depth_map = dist_transform.astype(np.uint8)
            return Image.fromarray(depth_map, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error in distance transform depth: {e}")
            return None
    
    async def _multi_layer_depth(
        self, 
        image: Image.Image,
        layers: List[str] = ["stroke", "radical", "background"],
        layer_separation: float = 0.3,
        blend_mode: str = "linear",
        **kwargs
    ) -> Image.Image:
        """Многослойная depth карта для сложных композиций."""
        try:
            # Используем комбинацию разных методов для разных слоев
            stroke_depth = await self._stroke_thickness_depth(image, **kwargs)
            distance_depth = await self._distance_transform_depth(image, **kwargs)
            
            if stroke_depth is None:
                stroke_depth = await self._simple_depth(image, **kwargs)
            if distance_depth is None:
                distance_depth = await self._simple_depth(image, **kwargs)
            
            # Конвертация в numpy для комбинирования
            stroke_array = np.array(stroke_depth.convert('L')).astype(np.float32)
            distance_array = np.array(distance_depth.convert('L')).astype(np.float32)
            
            # Комбинирование слоев
            if blend_mode == "linear":
                combined = stroke_array * 0.6 + distance_array * 0.4
            elif blend_mode == "exponential":
                combined = np.power(stroke_array / 255.0, 0.8) * np.power(distance_array / 255.0, 1.2) * 255
            elif blend_mode == "sigmoid":
                # Сигмоидное смешивание для плавных переходов
                weight = 1 / (1 + np.exp(-layer_separation * (stroke_array - 128)))
                combined = weight * stroke_array + (1 - weight) * distance_array
            else:
                combined = stroke_array * 0.6 + distance_array * 0.4
            
            # Нормализация
            combined = np.clip(combined, 0, 255).astype(np.uint8)
            
            return Image.fromarray(combined, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error in multi layer depth: {e}")
            return None
    
    def _create_shadow_map(
        self, 
        depth_map: np.ndarray, 
        light_direction: str, 
        intensity: float
    ) -> np.ndarray:
        """Создает карту теней на основе направления света."""
        h, w = depth_map.shape
        shadow_map = np.zeros_like(depth_map)
        
        # Определяем направление света
        if light_direction == "top_left":
            light_vector = (-1, -1)
        elif light_direction == "top_right":
            light_vector = (1, -1)
        elif light_direction == "center":
            light_vector = (0, -1)
        else:
            light_vector = (-1, -1)
        
        # Вычисляем градиенты depth карты
        grad_y, grad_x = np.gradient(depth_map)
        
        # Вычисляем dot product с направлением света
        dot_product = grad_x * light_vector[0] + grad_y * light_vector[1]
        
        # Создаем карту теней
        shadow_map = np.maximum(0, -dot_product) * intensity
        
        return shadow_map
    
    async def _morphological_depth(
        self, 
        image: Image.Image,
        erosion_iterations: int = 3,
        dilation_iterations: int = 2,
        kernel_size: int = 5,
        depth_levels: int = 8,
        **kwargs
    ) -> Image.Image:
        """Depth map с использованием морфологических операций."""
        try:
            # Конвертация в numpy
            img_array = np.array(image)
            
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Инвертируем для работы с черными объектами
            gray = 255 - gray
            
            # Создаем карту глубины с несколькими уровнями
            depth_map = np.zeros_like(gray, dtype=np.float32)
            
            # Структурирующий элемент
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            
            current_image = gray.copy()
            
            for level in range(depth_levels):
                # Эрозия для получения более глубоких слоев
                for _ in range(erosion_iterations):
                    current_image = cv2.erode(current_image, kernel, iterations=1)
                
                # Дилатация для сглаживания
                for _ in range(dilation_iterations):
                    current_image = cv2.dilate(current_image, kernel, iterations=1)
                
                # Добавляем к карте глубины
                depth_value = (depth_levels - level) / depth_levels * 255
                mask = current_image > 50  # Порог для определения присутствия объекта
                depth_map[mask] = depth_value
                
                # Уменьшаем интенсивность для следующего уровня
                current_image = current_image * 0.8
                current_image = current_image.astype(np.uint8)
            
            # Сглаживание переходов между уровнями
            depth_map = cv2.GaussianBlur(depth_map, (7, 7), 2)
            
            # Конвертация в RGB
            depth_map = depth_map.astype(np.uint8)
            return Image.fromarray(depth_map, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error in morphological depth: {e}")
            return None
        