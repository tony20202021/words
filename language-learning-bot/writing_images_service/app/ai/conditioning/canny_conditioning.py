"""
Canny edge detection conditioning generation.
Генерация conditioning на основе детекции границ Canny.
"""

import time
from typing import Dict, Any, Optional, List
import numpy as np
import cv2
from PIL import Image

from .base_conditioning import BaseConditioning, ConditioningResult, ConditioningConfig
from app.utils.logger import get_module_logger

logger = get_module_logger(__name__)


class CannyConditioning(BaseConditioning):
    """
    Генерация Canny edge conditioning с поддержкой различных методов детекции границ.
    """
    
    def __init__(self, config: Optional[ConditioningConfig] = None):
        """
        Инициализация Canny conditioning.
        
        Args:
            config: Конфигурация conditioning
        """
        super().__init__(config)
        
        # Инициализация AI моделей (если доступны)
        self._structured_edge_model = None
        self._model_loading_attempted = False
        
        logger.debug("CannyConditioning initialized")
    
    async def generate_from_image(
        self, 
        image: Image.Image, 
        method: str = "simple_canny",
        **kwargs
    ) -> ConditioningResult:
        """
        Генерирует Canny edges из изображения.
        
        Args:
            image: Входное изображение
            method: Метод детекции ("simple_canny", "opencv_canny", "hed_canny", etc.)
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
            if method == "simple_canny":
                result_image = await self._simple_canny(processed_data['image'], **kwargs)
            elif method == "opencv_canny":
                result_image = await self._opencv_canny(processed_data['image'], **kwargs)
            elif method == "structured_edge_detection":
                result_image = await self._structured_edge_detection(processed_data['image'], **kwargs)
            elif method == "multi_scale_canny":
                result_image = await self._multi_scale_canny(processed_data['image'], **kwargs)
            elif method == "adaptive_canny":
                result_image = await self._adaptive_canny(processed_data['image'], **kwargs)
            else:
                return ConditioningResult(
                    success=False,
                    error_message=f"Unknown method: {method}"
                )
            
            result_image = self.wave_distort(result_image, amplitude=5, wavelength=100)
            # result_image = self.blur_image(result_image, radius=10)
            result_image = self.add_noise_to_mask(result_image, noise_level=10, mask_threshold=50, mask_is_less_than=False)
            
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
            logger.error(f"Error in Canny generation from image: {e}", exc_info=True)
            return ConditioningResult(
                success=False,
                error_message=str(e),
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def generate_from_text(
        self, 
        character: str, 
        method: str = "simple_canny",
        width: int = 512, 
        height: int = 512,
        **kwargs
    ) -> ConditioningResult:
        """
        Генерирует Canny edges из текста (иероглифа).
        
        Args:
            character: Китайский иероглиф
            method: Метод детекции
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
            
            # Генерация Canny edges из отрендеренного изображения
            result = await self.generate_from_image(rendered_image, method, **kwargs)
            
            # Обновление метаданных
            if result.metadata:
                result.metadata['source_character'] = character
                result.metadata['rendered_size'] = (width, height)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Canny generation from text: {e}", exc_info=True)
            return ConditioningResult(
                success=False,
                error_message=str(e)
            )
    
    def get_available_methods(self) -> List[str]:
        """Возвращает список доступных методов Canny детекции."""
        return [
            "simple_canny",
            "opencv_canny",
            "structured_edge_detection", 
            "multi_scale_canny",
            "adaptive_canny"
        ]
    
    def get_method_info(self, method: str) -> Dict[str, Any]:
        """Возвращает информацию о конкретном методе."""
        method_info = {
            "simple_canny": {
                "description": "Простая детекция границ OpenCV с базовыми параметрами",
                "parameters": {
                    "low_threshold": {"type": "int", "default": 50, "range": [0, 255]},
                    "high_threshold": {"type": "int", "default": 150, "range": [0, 255]}
                },
                "speed": "very_fast",
                "quality": "good",
                "memory_usage": "very_low",
                "is_fallback": True
            },
            
            "opencv_canny": {
                "description": "Классический алгоритм детекции границ OpenCV",
                "parameters": {
                    "low_threshold": {"type": "int", "default": 50, "range": [0, 255]},
                    "high_threshold": {"type": "int", "default": 150, "range": [0, 255]},
                    "kernel_size": {"type": "int", "default": 3, "range": [3, 7]},
                    "gaussian_blur": {"type": "int", "default": 0, "range": [0, 15]}
                },
                "speed": "fast",
                "quality": "good",
                "memory_usage": "low"
            },
            
            "structured_edge_detection": {
                "description": "Microsoft Structured Edge Detection",
                "parameters": {
                    "threshold": {"type": "float", "default": 0.3, "range": [0.0, 1.0]},
                    "edge_density": {"type": "float", "default": 0.1, "range": [0.0, 1.0]}
                },
                "speed": "medium",
                "quality": "very_good",
                "memory_usage": "medium"
            },
            
            "multi_scale_canny": {
                "description": "Multi-scale Canny с комбинированием результатов",
                "parameters": {
                    "scales": {"type": "list", "default": [0.5, 1.0, 1.5], "range": [0.1, 3.0]},
                    "combine_method": {"type": "str", "default": "max", "options": ["max", "mean", "weighted"]},
                    "base_low_threshold": {"type": "int", "default": 50, "range": [0, 255]},
                    "base_high_threshold": {"type": "int", "default": 150, "range": [0, 255]}
                },
                "speed": "slow",
                "quality": "very_good", 
                "memory_usage": "medium"
            },
            
            "adaptive_canny": {
                "description": "Adaptive Canny с автоматическим подбором порогов",
                "parameters": {
                    "block_size": {"type": "int", "default": 3, "range": [3, 15]},
                    "c_constant": {"type": "float", "default": 2.0, "range": [0.0, 10.0]},
                    "sigma": {"type": "float", "default": 0.33, "range": [0.1, 1.0]}
                },
                "speed": "medium",
                "quality": "good",
                "memory_usage": "low"
            }
        }
        
        return method_info.get(method, {})
    
    # Реализация конкретных методов
    
    async def _simple_canny(
        self, 
        image: Image.Image,
        low_threshold: int = 50,
        high_threshold: int = 150,
        **kwargs
    ) -> Image.Image:
        """
        Простая детекция границ Canny (базовый fallback метод).
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
            
            # Простая детекция границ
            edges = cv2.Canny(gray, low_threshold, high_threshold)
            
            # Конвертация обратно в PIL
            return Image.fromarray(edges, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error in simple canny: {e}")
            return None

    async def _opencv_canny(
        self, 
        image: Image.Image,
        low_threshold: int = 50,
        high_threshold: int = 150,
        kernel_size: int = 3,
        gaussian_blur: int = 0,
        **kwargs
    ) -> Image.Image:
        """OpenCV Canny edge detection."""
        try:
            # Конвертация в numpy
            img_array = np.array(image)
            
            # Конвертация в grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Опциональное размытие
            if gaussian_blur > 0:
                gray = cv2.GaussianBlur(gray, (gaussian_blur, gaussian_blur), 0)
            
            # Canny edge detection
            edges = cv2.Canny(gray, low_threshold, high_threshold, apertureSize=kernel_size)
            
            # Конвертация обратно в PIL
            return Image.fromarray(edges, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error in OpenCV Canny: {e}")
            return None
        
    async def _structured_edge_detection(
        self, 
        image: Image.Image,
        threshold: float = 0.3,
        edge_density: float = 0.1,
        **kwargs
    ) -> Image.Image:
        """Structured Edge Detection method."""
        try:
            # Реализация упрощенной версии structured edges
            img_array = np.array(image)
            
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Применяем несколько фильтров для структурного анализа
            # Sobel в разных направлениях
            sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            
            # Магнитуда градиента
            magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
            
            # Нормализация и пороговая фильтрация
            magnitude = (magnitude / magnitude.max() * 255).astype(np.uint8)
            
            # Адаптивная пороговая фильтрация
            threshold_value = int(threshold * 255)
            _, edges = cv2.threshold(magnitude, threshold_value, 255, cv2.THRESH_BINARY)
            
            # Морфологические операции для структурности
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
            
            return Image.fromarray(edges, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error in Structured Edge Detection: {e}")
            return None
    
    async def _multi_scale_canny(
        self, 
        image: Image.Image,
        scales: List[float] = [0.5, 1.0, 1.5],
        combine_method: str = "max",
        base_low_threshold: int = 50,
        base_high_threshold: int = 150,
        **kwargs
    ) -> Image.Image:
        """Multi-scale Canny edge detection."""
        try:
            img_array = np.array(image)
            original_size = img_array.shape[:2]
            
            # Генерируем edges на разных масштабах
            scale_results = []
            
            for scale in scales:
                # Масштабирование изображения
                if scale != 1.0:
                    new_size = (int(original_size[1] * scale), int(original_size[0] * scale))
                    scaled_img = cv2.resize(img_array, new_size)
                else:
                    scaled_img = img_array
                
                # Конвертация в grayscale
                if len(scaled_img.shape) == 3:
                    gray = cv2.cvtColor(scaled_img, cv2.COLOR_RGB2GRAY)
                else:
                    gray = scaled_img
                
                # Canny detection с адаптированными порогами
                scale_factor = 1.0 / scale
                low_thresh = int(base_low_threshold * scale_factor)
                high_thresh = int(base_high_threshold * scale_factor)
                
                edges = cv2.Canny(gray, low_thresh, high_thresh)
                
                # Возвращаем к оригинальному размеру
                if scale != 1.0:
                    edges = cv2.resize(edges, (original_size[1], original_size[0]))
                
                scale_results.append(edges.astype(np.float32) / 255.0)
            
            # Комбинируем результаты
            if combine_method == "max":
                combined = np.maximum.reduce(scale_results)
            elif combine_method == "mean":
                combined = np.mean(scale_results, axis=0)
            elif combine_method == "weighted":
                # Больший вес для средних масштабов
                weights = np.array([0.25, 0.5, 0.25])[:len(scales)]
                weights = weights / weights.sum()
                combined = np.average(scale_results, axis=0, weights=weights)
            else:
                combined = np.maximum.reduce(scale_results)
            
            # Конвертация обратно в uint8
            combined = (combined * 255).astype(np.uint8)
            
            return Image.fromarray(combined, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error in Multi-scale Canny: {e}")
            return None
    
    async def _adaptive_canny(
        self, 
        image: Image.Image,
        block_size: int = 3,
        c_constant: float = 2.0,
        sigma: float = 0.33,
        **kwargs
    ) -> Image.Image:
        """Adaptive Canny with automatic threshold selection."""
        try:
            img_array = np.array(image)
            
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Вычисляем медиану для автоматического выбора порогов
            median_val = np.median(gray)
            
            # Автоматический расчет порогов на основе медианы
            lower_threshold = int(max(0, (1.0 - sigma) * median_val))
            upper_threshold = int(min(255, (1.0 + sigma) * median_val))
            
            # Адаптивная коррекция порогов на основе локальной статистики
            # Разделяем изображение на блоки и анализируем локальную контрастность
            h, w = gray.shape
            block_h, block_w = max(h // 4, 1), max(w // 4, 1)
            
            local_adjustments = []
            for i in range(0, h, block_h):
                for j in range(0, w, block_w):
                    block = gray[i:i+block_h, j:j+block_w]
                    if block.size > 0:
                        block_std = np.std(block)
                        local_adjustments.append(block_std)
            
            if local_adjustments:
                avg_contrast = np.mean(local_adjustments)
                contrast_factor = avg_contrast / 50.0  # Нормализация
                
                lower_threshold = int(lower_threshold * (1 + contrast_factor * c_constant))
                upper_threshold = int(upper_threshold * (1 + contrast_factor * c_constant))
            
            # Ограничиваем пороги разумными пределами
            lower_threshold = max(10, min(lower_threshold, 100))
            upper_threshold = max(lower_threshold + 50, min(upper_threshold, 255))
            
            # Применяем Canny с вычисленными порогами
            edges = cv2.Canny(gray, lower_threshold, upper_threshold)
            
            return Image.fromarray(edges, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error in Adaptive Canny: {e}")
            return None
