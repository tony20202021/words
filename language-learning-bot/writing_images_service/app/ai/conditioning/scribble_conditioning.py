"""
Scribble conditioning generation.
Генерация conditioning на основе набросков и упрощенных изображений.
"""

import time
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import cv2
from PIL import Image
from skimage import morphology
from scipy import interpolate
from scipy.ndimage import gaussian_filter

from .base_conditioning import BaseConditioning, ConditioningResult, ConditioningConfig
from app.utils.logger import get_module_logger

logger = get_module_logger(__name__)


class ScribbleConditioning(BaseConditioning):
    """
    Генерация scribble conditioning с различными алгоритмами создания набросков.
    """
    
    def __init__(self, config: Optional[ConditioningConfig] = None):
        """
        Инициализация Scribble conditioning.
        
        Args:
            config: Конфигурация conditioning
        """
        super().__init__(config)
        
        logger.debug("ScribbleConditioning initialized")
    
    async def generate_from_image(
        self, 
        image: Image.Image, 
        method: str = "simple_scribble",
        **kwargs
    ) -> ConditioningResult:
        """
        Генерирует scribble из изображения.
        
        Args:
            image: Входное изображение
            method: Метод генерации scribble
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
            if method == "simple_scribble":
                result_image = await self._simple_scribble(processed_data['image'], **kwargs)
            elif method == "skeletonization_scribble":
                result_image = await self._skeletonization_scribble(processed_data['image'], **kwargs)
            elif method == "morphological_simplification":
                result_image = await self._morphological_simplification(processed_data['image'], **kwargs)
            elif method == "vectorization_simplification":
                result_image = await self._vectorization_simplification(processed_data['image'], **kwargs)
            elif method == "hand_drawn_simulation":
                result_image = await self._hand_drawn_simulation(processed_data['image'], **kwargs)
            elif method == "multi_level_abstraction":
                result_image = await self._multi_level_abstraction(processed_data['image'], **kwargs)
            elif method == "style_aware_scribble":
                result_image = await self._style_aware_scribble(processed_data['image'], **kwargs)
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
            result_image = self.add_noise_to_mask(result_image, noise_level=30, mask_threshold=50, mask_is_less_than=True)
            
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
            logger.error(f"Error in Scribble generation from image: {e}", exc_info=True)
            return ConditioningResult(
                success=False,
                error_message=str(e),
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def generate_from_text(
        self, 
        character: str, 
        method: str = "simple_scribble",
        width: int = 512, 
        height: int = 512,
        **kwargs
    ) -> ConditioningResult:
        """
        Генерирует scribble из текста (иероглифа).
        
        Args:
            character: Китайский иероглиф
            method: Метод генерации scribble
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
            
            # Генерация scribble из отрендеренного изображения
            result = await self.generate_from_image(rendered_image, method, **kwargs)
            
            # Обновление метаданных
            if result.metadata:
                result.metadata['source_character'] = character
                result.metadata['rendered_size'] = (width, height)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Scribble generation from text: {e}", exc_info=True)
            return ConditioningResult(
                success=False,
                error_message=str(e),
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def get_available_methods(self) -> List[str]:
        """Возвращает список доступных методов scribble generation."""
        return [
            "simple_scribble",
            "skeletonization_scribble",
            "morphological_simplification",
            "vectorization_simplification",
            "hand_drawn_simulation",
            "multi_level_abstraction",
            "style_aware_scribble"
        ]
    
    def get_method_info(self, method: str) -> Dict[str, Any]:
        """Возвращает информацию о конкретном методе."""
        method_info = {
            "simple_scribble": {
                "description": "Простая скелетизация для создания базовых набросков (fallback)",
                "parameters": {
                    "algorithm": {"type": "str", "default": "zhang_suen", "options": ["zhang_suen", "medial_axis"]},
                    "preprocessing": {"type": "bool", "default": True}
                },
                "speed": "very_fast",
                "quality": "basic",
                "memory_usage": "very_low",
                "is_fallback": True
            },
            
            "skeletonization_scribble": {
                "description": "Скелетизация изображения для создания тонких линий",
                "parameters": {
                    "algorithm": {"type": "str", "default": "zhang_suen", "options": ["zhang_suen", "medial_axis"]},
                    "preprocessing": {"type": "bool", "default": True},
                    "noise_reduction": {"type": "int", "default": 2, "range": [0, 5]}
                },
                "speed": "fast",
                "quality": "good",
                "memory_usage": "low"
            },
            
            "morphological_simplification": {
                "description": "Морфологическое упрощение для создания грубых набросков",
                "parameters": {
                    "kernel_size": {"type": "int", "default": 3, "range": [3, 15]},
                    "iterations": {"type": "int", "default": 2, "range": [1, 10]},
                    "operation": {"type": "str", "default": "opening", "options": ["opening", "closing", "erosion"]}
                },
                "speed": "fast",
                "quality": "medium",
                "memory_usage": "low"
            },
            
            "vectorization_simplification": {
                "description": "Векторизация и упрощение путей",
                "parameters": {
                    "epsilon_factor": {"type": "float", "default": 0.02, "range": [0.001, 0.1]},
                    "min_area": {"type": "int", "default": 50, "range": [10, 500]},
                    "curve_smoothing": {"type": "bool", "default": True}
                },
                "speed": "medium",
                "quality": "very_good",
                "memory_usage": "medium"
            },
            
            "hand_drawn_simulation": {
                "description": "Имитация рисования от руки с дрожанием и неточностями",
                "parameters": {
                    "noise_level": {"type": "float", "default": 1.5, "range": [0.5, 5.0]},
                    "line_variation": {"type": "float", "default": 0.8, "range": [0.1, 2.0]},
                    "pressure_simulation": {"type": "bool", "default": True}
                },
                "speed": "medium",
                "quality": "good",
                "memory_usage": "low"
            },
            
            "multi_level_abstraction": {
                "description": "Многоуровневая абстракция с разными степенями детализации",
                "parameters": {
                    "levels": {"type": "list", "default": ["precise", "medium", "loose"]},
                    "default_level": {"type": "str", "default": "medium", "options": ["precise", "medium", "loose"]},
                    "blend_levels": {"type": "bool", "default": False}
                },
                "speed": "slow",
                "quality": "very_good",
                "memory_usage": "medium"
            },
            
            "style_aware_scribble": {
                "description": "Стиль-адаптивные наброски под конкретные стили генерации",
                "parameters": {
                    "target_style": {"type": "str", "default": "comic", "options": ["comic", "watercolor", "realistic", "anime"]},
                    "style_intensity": {"type": "float", "default": 0.7, "range": [0.1, 1.0]},
                    "adaptive_thickness": {"type": "bool", "default": True}
                },
                "speed": "medium",
                "quality": "very_good",
                "memory_usage": "medium"
            }
        }
        
        return method_info.get(method, {})
    
    # Реализация конкретных методов
    
    async def _simple_scribble(
        self, 
        image: Image.Image,
        algorithm: str = "zhang_suen",
        preprocessing: bool = True,
        **kwargs
    ) -> Optional[Image.Image]:
        """
        Простая скелетизация для создания базовых набросков (fallback метод).
        """
        try:
            # Конвертация в numpy
            img_array = np.array(image)
            
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Предобработка
            if preprocessing:
                # Размытие для удаления шума
                gray = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # Бинаризация
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
            
            # Простая скелетизация
            skeleton = morphology.medial_axis(binary > 0).astype(np.uint8) * 255
            
            # Инвертируем обратно (черные линии на белом фоне)
            skeleton = 255 - skeleton
            
            # Конвертация в RGB
            return Image.fromarray(skeleton, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error in simple scribble: {e}")
            return None

    async def _skeletonization_scribble(
        self, 
        image: Image.Image,
        algorithm: str = "zhang_suen",
        preprocessing: bool = True,
        noise_reduction: int = 2,
        **kwargs
    ) -> Optional[Image.Image]:
        """Скелетизация изображения для создания тонких линий."""
        try:
            # Конвертация в numpy
            img_array = np.array(image)
            
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Предобработка
            if preprocessing:
                # Размытие для удаления шума
                gray = cv2.GaussianBlur(gray, (3, 3), 0)
                
                # Адаптивная пороговая обработка
                binary = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
                )
            else:
                _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
            
            # Удаление шума
            if noise_reduction > 0:
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (noise_reduction, noise_reduction))
                binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
            
            # Скелетизация
            skeleton = morphology.medial_axis(binary > 0).astype(np.uint8) * 255
            
            # Инвертируем обратно (черные линии на белом фоне)
            skeleton = 255 - skeleton
            
            # Конвертация в RGB
            return Image.fromarray(skeleton, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error in skeletonization scribble: {e}")
            return None
    
    async def _morphological_simplification(
        self, 
        image: Image.Image,
        kernel_size: int = 3,
        iterations: int = 2,
        operation: str = "opening",
        **kwargs
    ) -> Optional[Image.Image]:
        """Морфологическое упрощение для создания грубых набросков."""
        try:
            # Конвертация в numpy
            img_array = np.array(image)
            
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Бинаризация
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
            
            # Создаем структурирующий элемент
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            
            # Применяем морфологические операции
            if operation == "opening":
                result = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=iterations)
            elif operation == "closing":
                result = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=iterations)
            elif operation == "erosion":
                result = cv2.erode(binary, kernel, iterations=iterations)
            else:
                result = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=iterations)
            
            # Находим контуры для создания линий
            contours, _ = cv2.findContours(result, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Создаем изображение с контурами
            scribble = np.ones_like(gray) * 255
            for contour in contours:
                cv2.drawContours(scribble, [contour], -1, 0, 2)
            
            # Конвертация в RGB
            return Image.fromarray(scribble, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error in morphological simplification: {e}")
            return None
    
    async def _vectorization_simplification(
        self, 
        image: Image.Image,
        epsilon_factor: float = 0.02,
        min_area: int = 50,
        curve_smoothing: bool = True,
        **kwargs
    ) -> Optional[Image.Image]:
        """Векторизация и упрощение путей."""
        try:
            # Конвертация в numpy
            img_array = np.array(image)
            
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Бинаризация
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
            
            # Находим контуры
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Создаем упрощенное изображение
            scribble = np.ones_like(gray) * 255
            
            for contour in contours:
                # Фильтруем маленькие контуры
                area = cv2.contourArea(contour)
                if area < min_area:
                    continue
                
                # Упрощаем контур
                epsilon = epsilon_factor * cv2.arcLength(contour, True)
                simplified = cv2.approxPolyDP(contour, epsilon, True)
                
                # Рисуем упрощенный контур
                if curve_smoothing and len(simplified) > 4:
                    # Сглаживаем кривую
                    simplified_smooth = self._smooth_contour(simplified)
                    cv2.drawContours(scribble, [simplified_smooth], -1, 0, 2)
                else:
                    cv2.drawContours(scribble, [simplified], -1, 0, 2)
            
            # Конвертация в RGB
            return Image.fromarray(scribble, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error in vectorization simplification: {e}")
            return None
    
    async def _hand_drawn_simulation(
        self, 
        image: Image.Image,
        noise_level: float = 1.5,
        line_variation: float = 0.8,
        pressure_simulation: bool = True,
        **kwargs
    ) -> Optional[Image.Image]:
        """Имитация рисования от руки с дрожанием и неточностями."""
        try:
            # Сначала получаем базовый scribble
            base_scribble = await self._skeletonization_scribble(image)
            if base_scribble is None:
                base_scribble = await self._simple_scribble(image)
            
            if base_scribble is None:
                return None
            
            # Конвертируем в numpy для обработки
            scribble_array = np.array(base_scribble.convert('L'))
            
            # Находим контуры базового scribble
            _, binary = cv2.threshold(scribble_array, 127, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Создаем hand-drawn версию
            hand_drawn = np.ones_like(scribble_array) * 255
            
            for contour in contours:
                if len(contour) < 3:
                    continue
                
                # Добавляем дрожание к точкам контура
                noisy_contour = self._add_hand_tremor(contour, noise_level)
                
                # Рисуем с вариацией толщины линии
                if pressure_simulation:
                    self._draw_pressure_sensitive_line(hand_drawn, noisy_contour, line_variation)
                else:
                    cv2.drawContours(hand_drawn, [noisy_contour], -1, 0, 2)
            
            # Добавляем общий шум для имитации текстуры карандаша
            texture_noise = np.random.normal(0, 5, hand_drawn.shape)
            hand_drawn = hand_drawn + texture_noise
            hand_drawn = np.clip(hand_drawn, 0, 255).astype(np.uint8)
            
            # Конвертация в RGB
            return Image.fromarray(hand_drawn, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error in hand drawn simulation: {e}")
            return None
    
    async def _multi_level_abstraction(
        self, 
        image: Image.Image,
        levels: List[str] = ["precise", "medium", "loose"],
        default_level: str = "medium",
        blend_levels: bool = False,
        **kwargs
    ) -> Optional[Image.Image]:
        """Многоуровневая абстракция с разными степенями детализации."""
        try:
            # Генерируем scribbles разного уровня абстракции
            level_results = {}
            
            if "precise" in levels:
                level_results["precise"] = await self._skeletonization_scribble(
                    image, algorithm="medial_axis", noise_reduction=1
                )
            
            if "medium" in levels:
                level_results["medium"] = await self._morphological_simplification(
                    image, kernel_size=3, iterations=2
                )
            
            if "loose" in levels:
                level_results["loose"] = await self._morphological_simplification(
                    image, kernel_size=5, iterations=3
                )
            
            # Убираем None результаты
            level_results = {k: v for k, v in level_results.items() if v is not None}
            
            if not level_results:
                return None
            
            # Если нужно смешивание уровней
            if blend_levels and len(level_results) > 1:
                return self._blend_abstraction_levels(level_results)
            
            # Возвращаем уровень по умолчанию
            if default_level in level_results:
                return level_results[default_level]
            else:
                # Fallback к любому доступному уровню
                return list(level_results.values())[0]
                
        except Exception as e:
            logger.error(f"Error in multi level abstraction: {e}")
            return None
    
    async def _style_aware_scribble(
        self, 
        image: Image.Image,
        target_style: str = "comic",
        style_intensity: float = 0.7,
        adaptive_thickness: bool = True,
        **kwargs
    ) -> Optional[Image.Image]:
        """Стиль-адаптивные наброски под конкретные стили генерации."""
        try:
            # Параметры для разных стилей
            style_params = {
                "comic": {
                    "method": "vectorization_simplification",
                    "epsilon_factor": 0.03,
                    "line_thickness": 3,
                    "contrast_boost": 1.2
                },
                "watercolor": {
                    "method": "hand_drawn_simulation",
                    "noise_level": 2.0,
                    "line_variation": 1.2,
                    "softness": True
                },
                "realistic": {
                    "method": "skeletonization_scribble",
                    "algorithm": "medial_axis",
                    "precision": "high"
                },
                "anime": {
                    "method": "morphological_simplification",
                    "kernel_size": 2,
                    "clean_lines": True
                }
            }
            
            # Получаем параметры для целевого стиля
            params = style_params.get(target_style, style_params["comic"])
            
            # Генерируем base scribble в зависимости от стиля
            if params["method"] == "vectorization_simplification":
                base_scribble = await self._vectorization_simplification(
                    image, 
                    epsilon_factor=params.get("epsilon_factor", 0.02)
                )
            elif params["method"] == "hand_drawn_simulation":
                base_scribble = await self._hand_drawn_simulation(
                    image,
                    noise_level=params.get("noise_level", 1.5),
                    line_variation=params.get("line_variation", 0.8)
                )
            elif params["method"] == "skeletonization_scribble":
                base_scribble = await self._skeletonization_scribble(
                    image,
                    algorithm=params.get("algorithm", "zhang_suen")
                )
            else:  # morphological_simplification
                base_scribble = await self._morphological_simplification(
                    image,
                    kernel_size=params.get("kernel_size", 3)
                )
            
            if base_scribble is None:
                return None
            
            # Применяем стиль-специфичные модификации
            styled_scribble = self._apply_style_modifications(
                base_scribble, target_style, style_intensity, adaptive_thickness
            )
            
            return styled_scribble
            
        except Exception as e:
            logger.error(f"Error in style aware scribble: {e}")
            return None
    
    # Вспомогательные методы (реализация отсутствующих методов)
    
    def _smooth_contour(self, contour: np.ndarray) -> np.ndarray:
        """
        Сглаживает контур используя сплайн интерполяцию.
        
        Args:
            contour: Контур для сглаживания
            
        Returns:
            Сглаженный контур
        """
        try:
            if len(contour) < 4:
                return contour
            
            # Извлекаем точки
            points = contour.reshape(-1, 2)
            
            # Параметризация по длине дуги
            distances = np.zeros(len(points))
            for i in range(1, len(points)):
                distances[i] = distances[i-1] + np.linalg.norm(points[i] - points[i-1])
            
            # Создаем сплайны для x и y координат
            if len(np.unique(distances)) < 4:  # Недостаточно уникальных точек
                return contour
            
            # Используем кубическую интерполяцию
            cs_x = interpolate.CubicSpline(distances, points[:, 0], bc_type='natural')
            cs_y = interpolate.CubicSpline(distances, points[:, 1], bc_type='natural')
            
            # Генерируем сглаженные точки
            smooth_distances = np.linspace(0, distances[-1], len(points))
            smooth_x = cs_x(smooth_distances)
            smooth_y = cs_y(smooth_distances)
            
            # Формируем результат в формате контура OpenCV
            smooth_points = np.column_stack([smooth_x, smooth_y]).astype(np.int32)
            smooth_contour = smooth_points.reshape(-1, 1, 2)
            
            return smooth_contour
            
        except Exception as e:
            logger.warning(f"Error smoothing contour: {e}")
            return contour
    
    def _add_hand_tremor(self, contour: np.ndarray, noise_level: float) -> np.ndarray:
        """
        Добавляет дрожание руки к контуру.
        
        Args:
            contour: Исходный контур
            noise_level: Уровень шума
            
        Returns:
            Контур с добавленным дрожанием
        """
        try:
            if len(contour) == 0:
                return contour
            
            # Извлекаем точки
            points = contour.reshape(-1, 2).astype(np.float32)
            
            # Генерируем шум
            noise_x = np.random.normal(0, noise_level, len(points))
            noise_y = np.random.normal(0, noise_level, len(points))
            
            # Применяем сглаживание к шуму для более естественного дрожания
            noise_x = gaussian_filter(noise_x, sigma=1.0)
            noise_y = gaussian_filter(noise_y, sigma=1.0)
            
            # Добавляем шум к точкам
            noisy_points = points.copy()
            noisy_points[:, 0] += noise_x
            noisy_points[:, 1] += noise_y
            
            # Ограничиваем координаты в разумных пределах
            noisy_points = np.clip(noisy_points, 0, 2048).astype(np.int32)
            
            # Формируем результат в формате контура OpenCV
            noisy_contour = noisy_points.reshape(-1, 1, 2)
            
            return noisy_contour
            
        except Exception as e:
            logger.warning(f"Error adding hand tremor: {e}")
            return contour
    
    def _draw_pressure_sensitive_line(
        self, 
        image: np.ndarray, 
        contour: np.ndarray, 
        line_variation: float
    ) -> None:
        """
        Рисует линию с имитацией изменения нажима.
        
        Args:
            image: Изображение для рисования
            contour: Контур для рисования
            line_variation: Вариация толщины линии
        """
        try:
            if len(contour) < 2:
                return
            
            points = contour.reshape(-1, 2)
            
            # Вычисляем толщину для каждого сегмента
            base_thickness = 2
            
            for i in range(len(points) - 1):
                # Симулируем изменение нажима (больше нажим в середине штриха)
                t = i / max(len(points) - 1, 1)
                pressure = np.sin(t * np.pi)  # Синусоидальное изменение нажима
                
                # Добавляем случайную вариацию
                pressure += np.random.normal(0, line_variation * 0.1)
                pressure = np.clip(pressure, 0.1, 1.0)
                
                # Вычисляем толщину линии
                thickness = int(base_thickness * pressure * line_variation)
                thickness = max(1, min(thickness, 8))  # Ограничиваем толщину
                
                # Рисуем сегмент
                pt1 = tuple(points[i])
                pt2 = tuple(points[i + 1])
                cv2.line(image, pt1, pt2, 0, thickness)
                
        except Exception as e:
            logger.warning(f"Error drawing pressure sensitive line: {e}")
    
    def _blend_abstraction_levels(self, level_results: Dict[str, Image.Image]) -> Optional[Image.Image]:
        """
        Смешивает результаты разных уровней абстракции.
        
        Args:
            level_results: Словарь с результатами разных уровней
            
        Returns:
            Смешанное изображение
        """
        try:
            if not level_results:
                return None
            
            # Получаем первое изображение как основу
            base_image = list(level_results.values())[0]
            if base_image is None:
                return None
            
            # Конвертируем в numpy для смешивания
            base_array = np.array(base_image.convert('L')).astype(np.float32)
            result_array = base_array.copy()
            
            # Веса для разных уровней
            weights = {
                "precise": 0.4,
                "medium": 0.4,
                "loose": 0.2
            }
            
            total_weight = 0
            
            # Смешиваем изображения
            for level, image in level_results.items():
                if image is None:
                    continue
                    
                weight = weights.get(level, 0.3)
                img_array = np.array(image.convert('L')).astype(np.float32)
                
                if total_weight == 0:
                    result_array = img_array * weight
                else:
                    result_array = result_array + img_array * weight
                
                total_weight += weight
            
            # Нормализуем результат
            if total_weight > 0:
                result_array = result_array / total_weight
            
            result_array = np.clip(result_array, 0, 255).astype(np.uint8)
            
            # Конвертация обратно в PIL
            return Image.fromarray(result_array, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error blending abstraction levels: {e}")
            return list(level_results.values())[0]  # Fallback к первому доступному
    
    def _apply_style_modifications(
        self, 
        image: Image.Image, 
        target_style: str, 
        style_intensity: float, 
        adaptive_thickness: bool
    ) -> Optional[Image.Image]:
        """
        Применяет стиль-специфичные модификации к изображению.
        
        Args:
            image: Базовое изображение
            target_style: Целевой стиль
            style_intensity: Интенсивность применения стиля
            adaptive_thickness: Использовать ли адаптивную толщину
            
        Returns:
            Модифицированное изображение
        """
        try:
            if image is None:
                return None
            
            # Конвертируем в numpy для обработки
            img_array = np.array(image.convert('L'))
            
            # Применяем модификации в зависимости от стиля
            if target_style == "comic":
                # Увеличиваем контраст, делаем линии более четкими
                img_array = self._enhance_contrast(img_array, 1.2 * style_intensity)
                img_array = self._thicken_lines(img_array, adaptive_thickness)
                
            elif target_style == "watercolor":
                # Размываем края, делаем линии более мягкими
                img_array = self._soften_edges(img_array, style_intensity)
                img_array = self._add_texture_noise(img_array, 0.1 * style_intensity)
                
            elif target_style == "realistic":
                # Минимальные изменения, сохраняем детали
                img_array = self._preserve_details(img_array)
                
            elif target_style == "anime":
                # Четкие линии, высокий контраст
                img_array = self._enhance_contrast(img_array, 1.5 * style_intensity)
                img_array = self._clean_lines(img_array)
            
            # Применяем общие модификации с учетом интенсивности
            img_array = self._apply_intensity_scaling(img_array, style_intensity)
            
            # Конвертация обратно в PIL
            return Image.fromarray(img_array, mode='L').convert('RGB')
            
        except Exception as e:
            logger.error(f"Error applying style modifications: {e}")
            return image  # Возвращаем оригинал при ошибке
    
    def _enhance_contrast(self, image: np.ndarray, factor: float) -> np.ndarray:
        """Увеличивает контраст изображения."""
        try:
            # Нормализуем к [0, 1]
            normalized = image.astype(np.float32) / 255.0
            
            # Применяем контрастное преобразование
            mean = np.mean(normalized)
            enhanced = (normalized - mean) * factor + mean
            
            # Возвращаем к [0, 255]
            enhanced = np.clip(enhanced * 255, 0, 255).astype(np.uint8)
            return enhanced
        except Exception:
            return image
    
    def _thicken_lines(self, image: np.ndarray, adaptive: bool) -> np.ndarray:
        """Утолщает линии на изображении."""
        try:
            # Морфологическое утолщение
            kernel_size = 3 if adaptive else 2
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            
            # Инвертируем для обработки
            inverted = 255 - image
            
            # Применяем дилатацию
            thickened = cv2.dilate(inverted, kernel, iterations=1)
            
            # Инвертируем обратно
            return 255 - thickened
        except Exception:
            return image
    
    def _soften_edges(self, image: np.ndarray, intensity: float) -> np.ndarray:
        """Смягчает края на изображении."""
        try:
            # Применяем Gaussian blur
            kernel_size = int(3 + 4 * intensity)
            if kernel_size % 2 == 0:
                kernel_size += 1
            
            blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), intensity)
            return blurred
        except Exception:
            return image
    
    def _add_texture_noise(self, image: np.ndarray, intensity: float) -> np.ndarray:
        """Добавляет текстурный шум."""
        try:
            noise = np.random.normal(0, 255 * intensity, image.shape)
            noisy = image.astype(np.float32) + noise
            return np.clip(noisy, 0, 255).astype(np.uint8)
        except Exception:
            return image
    
    def _preserve_details(self, image: np.ndarray) -> np.ndarray:
        """Сохраняет детали изображения (минимальная обработка)."""
        try:
            # Легкое сглаживание для удаления артефактов
            return cv2.bilateralFilter(image, 5, 80, 80)
        except Exception:
            return image
    
    def _clean_lines(self, image: np.ndarray) -> np.ndarray:
        """Очищает линии, убирает артефакты."""
        try:
            # Морфологическое закрытие для соединения разрывов
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            
            # Инвертируем для обработки
            inverted = 255 - image
            
            # Применяем закрытие
            cleaned = cv2.morphologyEx(inverted, cv2.MORPH_CLOSE, kernel)
            
            # Инвертируем обратно
            return 255 - cleaned
        except Exception:
            return image
    
    def _apply_intensity_scaling(self, image: np.ndarray, intensity: float) -> np.ndarray:
        """Применяет масштабирование интенсивности."""
        try:
            if intensity == 1.0:
                return image
            
            # Смешиваем оригинал с обработанным изображением
            original = image.astype(np.float32)
            
            # Простое масштабирование контраста
            mean = np.mean(original)
            scaled = (original - mean) * intensity + mean
            
            # Смешиваем с оригиналом
            result = original * (1 - intensity) + scaled * intensity
            
            return np.clip(result, 0, 255).astype(np.uint8)
        except Exception:
            return image
        