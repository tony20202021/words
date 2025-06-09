"""
Scribble conditioning generation.
Генерация conditioning на основе набросков и упрощенных изображений.
"""

import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import cv2
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage import morphology, measure
import logging
import random

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
        
        # Инициализация AI моделей для sketch generation
        self._anime2sketch_model = None
        self._photo2sketch_model = None
        self._model_loading_attempted = False
        
        logger.info("ScribbleConditioning initialized")
    
    async def generate_from_image(
        self, 
        image: Image.Image, 
        method: str = "skeletonization_scribble",
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
                    error_message=error_msg
                )
            
            # Выбор метода генерации
            # TODO - добавить базовый простой метод, как метод по умолчанию, из модуля words/language-learning-bot/writing_images_service/app/ai/ai_image_generator.py, где он описан как fallback
            if method == "skeletonization_scribble":
                result_image = await self._skeletonization_scribble(processed_data['image'], **kwargs)
            elif method == "morphological_simplification":
                result_image = await self._morphological_simplification(processed_data['image'], **kwargs)
            elif method == "vectorization_simplification":
                result_image = await self._vectorization_simplification(processed_data['image'], **kwargs)
            elif method == "ai_sketch_generation":
                result_image = await self._ai_sketch_generation(processed_data['image'], **kwargs)
            elif method == "hand_drawn_simulation":
                result_image = await self._hand_drawn_simulation(processed_data['image'], **kwargs)
            elif method == "multi_level_abstraction":
                result_image = await self._multi_level_abstraction(processed_data['image'], **kwargs)
            elif method == "style_aware_scribble":
                result_image = await self._style_aware_scribble(processed_data['image'], **kwargs)
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
                    'scribble_stats': self._analyze_scribble_characteristics(result_image)
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
        method: str = "skeletonization_scribble",
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
                error_message=str(e)
            )
    
    def get_available_methods(self) -> List[str]:
        """Возвращает список доступных методов scribble generation."""
        return [
            # TODO - добавить базовый простой метод, как метод по умолчанию, из модуля words/language-learning-bot/writing_images_service/app/ai/ai_image_generator.py, где он описан как fallback
            "skeletonization_scribble",
            "morphological_simplification",
            "vectorization_simplification",
            "ai_sketch_generation",
            "hand_drawn_simulation",
            "multi_level_abstraction",
            "style_aware_scribble"
        ]
    
    def get_method_info(self, method: str) -> Dict[str, Any]:
        """Возвращает информацию о конкретном методе."""
        method_info = {
            # TODO - добавить базовый простой метод, как метод по умолчанию, из модуля words/language-learning-bot/writing_images_service/app/ai/ai_image_generator.py, где он описан как fallback
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
            
            "ai_sketch_generation": {
                "description": "AI генерация набросков с Anime2Sketch или Photo2Sketch",
                "parameters": {
                    "model_type": {"type": "str", "default": "anime2sketch", "options": ["anime2sketch", "photo2sketch"]},
                    "sketch_intensity": {"type": "float", "default": 0.8, "range": [0.1, 1.0]}
                },
                "speed": "slow",
                "quality": "excellent",
                "memory_usage": "high",
                "requires_gpu": True
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
    # TODO - добавить базовый простой метод, как метод по умолчанию, из модуля words/language-learning-bot/writing_images_service/app/ai/ai_image_generator.py, где он описан как fallback
    async def _skeletonization_scribble(
        self, 
        image: Image.Image,
        algorithm: str = "zhang_suen",
        preprocessing: bool = True,
        noise_reduction: int = 2,
        **kwargs
    ) -> Image.Image:
        """Скелетизация изображения для создания тонких линий."""
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
        if algorithm == "zhang_suen":
            skeleton = self._zhang_suen_skeletonization(binary)
        elif algorithm == "medial_axis":
            skeleton = morphology.medial_axis(binary > 0).astype(np.uint8) * 255
        else:
            # Fallback к морфологической скелетизации
            skeleton = self._morphological_skeletonization(binary)
        
        # Инвертируем обратно (черные линии на белом фоне)
        skeleton = 255 - skeleton
        
        # Конвертация в RGB
        return Image.fromarray(skeleton, mode='L').convert('RGB')
    
    async def _morphological_simplification(
        self, 
        image: Image.Image,
        kernel_size: int = 3,
        iterations: int = 2,
        operation: str = "opening",
        **kwargs
    ) -> Image.Image:
        """Морфологическое упрощение для создания грубых набросков."""
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
    
    async def _vectorization_simplification(
        self, 
        image: Image.Image,
        epsilon_factor: float = 0.02,
        min_area: int = 50,
        curve_smoothing: bool = True,
        **kwargs
    ) -> Image.Image:
        """Векторизация и упрощение путей."""
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
                # Сглаживаем кривую через B-spline аппроксимацию
                simplified_smooth = self._smooth_contour(simplified)
                cv2.drawContours(scribble, [simplified_smooth], -1, 0, 2)
            else:
                cv2.drawContours(scribble, [simplified], -1, 0, 2)
        
        # Конвертация в RGB
        return Image.fromarray(scribble, mode='L').convert('RGB')
    
    async def _ai_sketch_generation(
        self, 
        image: Image.Image,
        model_type: str = "anime2sketch",
        sketch_intensity: float = 0.8,
        **kwargs
    ) -> Image.Image:
        """AI генерация набросков с использованием предобученных моделей."""
        try:
            # Попытка загрузки модели
            if not self._model_loading_attempted:
                await self._load_sketch_models()
            
            if self._anime2sketch_model is None:
                logger.warning("AI sketch models not available, falling back to skeletonization")
                return await self._skeletonization_scribble(image, **kwargs)
            
            # TODO: Реализация AI sketch generation
            # Пример с anime2sketch:
            # import torch
            # import torchvision.transforms as transforms
            # 
            # # Предобработка
            # transform = transforms.Compose([
            #     transforms.Resize((512, 512)),
            #     transforms.ToTensor(),
            #     transforms.Normalize(mean=[0.5], std=[0.5])
            # ])
            # 
            # input_tensor = transform(image.convert('L')).unsqueeze(0)
            # 
            # # Инференс
            # with torch.no_grad():
            #     if model_type == "anime2sketch":
            #         sketch_output = self._anime2sketch_model(input_tensor)
            #     else:
            #         sketch_output = self._photo2sketch_model(input_tensor)
            # 
            # # Постобработка
            # sketch_array = sketch_output.squeeze().cpu().numpy()
            # sketch_array = (sketch_array * 255).astype(np.uint8)
            # sketch_array = cv2.resize(sketch_array, image.size)
            # 
            # # Применяем интенсивность
            # sketch_array = sketch_array * sketch_intensity + (1 - sketch_intensity) * 255
            # sketch_array = np.clip(sketch_array, 0, 255).astype(np.uint8)
            # 
            # return Image.fromarray(sketch_array, mode='L').convert('RGB')
            
            # Пока используем fallback
            logger.info("AI sketch generation not implemented yet, using skeletonization")
            return await self._skeletonization_scribble(image, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in AI sketch generation: {e}")
            return await self._skeletonization_scribble(image, **kwargs)
    
    async def _hand_drawn_simulation(
        self, 
        image: Image.Image,
        noise_level: float = 1.5,
        line_variation: float = 0.8,
        pressure_simulation: bool = True,
        **kwargs
    ) -> Image.Image:
        """Имитация рисования от руки с дрожанием и неточностями."""
        # Сначала получаем базовый scribble
        base_scribble = await self._skeletonization_scribble(image)
        
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
    
    async def _multi_level_abstraction(
        self, 
        image: Image.Image,
        levels: List[str] = ["precise", "medium", "loose"],
        default_level: str = "medium",
        blend_levels: bool = False,
        **kwargs
    ) -> Image.Image:
        """Многоуровневая абстракция с разными степенями детализации."""
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
        
        # Если нужно смешивание уровней
        if blend_levels and len(level_results) > 1:
            return self._blend_abstraction_levels(level_results)
        
        # Возвращаем уровень по умолчанию
        if default_level in level_results:
            return level_results[default_level]
        else:
            # Fallback к любому доступному уровню
            return list(level_results.values())[0]
    
    async def _style_aware_scribble(
        self, 
        image: Image.Image,
        target_style: str = "comic",
        style_intensity: float = 0.7,
        adaptive_thickness: bool = True,
        **kwargs
    ) -> Image.Image:
        """Стиль-адаптивные наброски под конкретные стили генерации."""
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
        
        # Применяем стиль-специфичные модификации
        styled_scribble = self._apply_style_modifications(
            base_scribble, target_style, style_intensity, adaptive_thickness
        )
        
        return styled_scribble
    
    # Вспомогательные методы
    
    def _zhang_suen_skeletonization(self, binary: np.ndarray) -> np.ndarray:
        """Алгоритм скелетизации Zhang-Suen."""
        def _neighbours(x, y, image):
            """Возвращает 8 соседей пикселя в определенном порядке."""
            img = image
            x1, y1, x2, y2 = x-1, y-1, x+1, y+1
            return [img[x1,y], img[x1,y1], img[x,y1], img[x2,y1],
                   img[x2,y], img[x2,y2], img[x,y2], img[x1,y2]]
        
        def _transitions(neighbours):
            """Подсчитывает переходы от 0 к 1."""
            n = neighbours + neighbours[0:1]
            return sum((n1, n2) == (0, 1) for n1, n2 in zip(n, n[1:]))
        
        def _zhang_suen_step(image, step):
            """Один шаг алгоритма Zhang-Suen."""
            height, width = image.shape
            changing1 = changing2 = []
            
            if step == 1:
                changing1 = [(x, y) for x in range(1, height-1) for y in range(1, width-1)
                           if image[x,y] == 1 and
                           2 <= sum(_neighbours(x, y, image)) <= 6 and
                           _transitions(_neighbours(x, y, image)) == 1 and
                           _neighbours(x, y, image)[0] * _neighbours(x, y, image)[2] * _neighbours(x, y, image)[4] == 0 and
                           _neighbours(x, y, image)[2] * _neighbours(x, y, image)[4] * _neighbours(x, y, image)[6] == 0]
            else:
                changing2 = [(x, y) for x in range(1, height-1) for y in range(1, width-1)
                           if image[x,y] == 1 and
                           2 <= sum(_neighbours(x, y, image)) <= 6 and
                           _transitions(_neighbours(x, y, image)) == 1 and
                           _neighbours(x, y, image)[0] * _neighbours(x, y, image)[2] * _neighbours(x, y, image)[6] == 0 and
                           _neighbours(x, y, image)[0] * _neighbours(x, y, image)[4] * _neighbours(x, y, image)[6] == 0]
                