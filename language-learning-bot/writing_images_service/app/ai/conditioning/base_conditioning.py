"""
Base class for conditioning generation.
Базовый класс для генерации conditioning изображений.
"""

import time
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass
from PIL import Image
import numpy as np
import logging

from app.utils.logger import get_module_logger
from app.utils.image_utils import get_image_processor
from common.utils.font_utils import get_font_manager

logger = get_module_logger(__name__)


@dataclass
class ConditioningConfig:
    """Конфигурация для генерации conditioning"""
    method: str
    parameters: Dict[str, Any]
    quality_threshold: float = 0.5
    timeout_seconds: int = 30
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600


@dataclass
class ConditioningResult:
    """Результат генерации conditioning"""
    success: bool
    image: Optional[Image.Image] = None
    method_used: str = ""
    processing_time_ms: int = 0
    quality_score: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Инициализация после создания"""
        if self.metadata is None:
            self.metadata = {}
    
    def to_base64(self) -> Optional[str]:
        """Конвертирует изображение в base64"""
        if not self.image:
            return None
        
        import io
        import base64
        
        buffer = io.BytesIO()
        self.image.save(buffer, format='PNG')
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')


class BaseConditioning(ABC):
    """
    Базовый класс для всех типов conditioning генерации.
    Определяет общий интерфейс и предоставляет общие утилиты.
    """
    
    def __init__(self, config: Optional[ConditioningConfig] = None):
        """
        Инициализация базового conditioning.
        
        Args:
            config: Конфигурация conditioning
        """
        self.config = config or ConditioningConfig(method="base", parameters={})
        self.font_manager = get_font_manager()
        self.image_processor = get_image_processor()
        self.cache: Dict[str, ConditioningResult] = {}
        self.performance_stats: Dict[str, List[float]] = {}
        
        logger.info(f"Initialized {self.__class__.__name__} conditioning")
    
    @abstractmethod
    async def generate_from_image(
        self, 
        image: Image.Image, 
        method: str = None,
        **kwargs
    ) -> ConditioningResult:
        """
        Генерирует conditioning из изображения.
        
        Args:
            image: Входное изображение
            method: Конкретный метод генерации
            **kwargs: Дополнительные параметры
            
        Returns:
            ConditioningResult: Результат генерации
        """
        pass
    
    @abstractmethod
    async def generate_from_text(
        self, 
        character: str, 
        method: str = None,
        width: int = 512, 
        height: int = 512,
        **kwargs
    ) -> ConditioningResult:
        """
        Генерирует conditioning из текста (иероглифа).
        
        Args:
            character: Китайский иероглиф
            method: Конкретный метод генерации
            width: Ширина результата
            height: Высота результата
            **kwargs: Дополнительные параметры
            
        Returns:
            ConditioningResult: Результат генерации
        """
        pass
    
    @abstractmethod
    def get_available_methods(self) -> List[str]:
        """
        Возвращает список доступных методов генерации.
        
        Returns:
            List[str]: Список названий методов
        """
        pass
    
    @abstractmethod
    def get_method_info(self, method: str) -> Dict[str, Any]:
        """
        Возвращает информацию о конкретном методе.
        
        Args:
            method: Название метода
            
        Returns:
            Dict: Информация о методе (параметры, описание, etc.)
        """
        pass
    
    # Общие утилиты
    
    async def render_character(
        self, 
        character: str, 
        width: int = 512, 
        height: int = 512,
        background_color: Tuple[int, int, int] = (255, 255, 255),
        text_color: Tuple[int, int, int] = (0, 0, 0)
    ) -> Image.Image:
        """
        Рендерит иероглиф в изображение используя ImageProcessor.
        
        Args:
            character: Иероглиф для рендеринга
            width: Ширина изображения
            height: Высота изображения
            background_color: Цвет фона (RGB)
            text_color: Цвет текста (RGB)
            
        Returns:
            Image.Image: Отрендеренное изображение
        """
        try:
            # Создаем изображение через ImageProcessor
            image = await self.image_processor.create_image(width, height, background_color)
            
            # Добавляем текст с автоподбором размера через ImageProcessor
            margin = min(width, height) // 10
            max_text_width = width - 2 * margin
            max_text_height = height - 2 * margin
            
            # Используем ImageProcessor для автоподбора текста
            image, final_font_size = await self.image_processor.add_auto_fit_text(
                image=image,
                text=character,
                max_width=max_text_width,
                max_height=max_text_height,
                initial_font_size=min(width, height) // 2,
                text_color=text_color,
                center_horizontal=True,
                center_vertical=True
            )
            
            logger.debug(f"Rendered character '{character}' with font size {final_font_size}")
            return image
            
        except Exception as e:
            logger.error(f"Error rendering character {character}: {e}")
            # Возвращаем пустое изображение в случае ошибки
            return await self.image_processor.create_image(width, height, background_color)
    
    def validate_image(self, image: Image.Image) -> bool:
        """
        Валидирует входное изображение.
        
        Args:
            image: Изображение для валидации
            
        Returns:
            bool: True если изображение валидно
        """
        if not isinstance(image, Image.Image):
            logger.warning("Input is not a PIL Image")
            return False
        
        if image.size[0] == 0 or image.size[1] == 0:
            logger.warning("Image has zero dimensions")
            return False
        
        if image.mode not in ['RGB', 'RGBA', 'L']:
            logger.warning(f"Unsupported image mode: {image.mode}")
            return False
        
        return True
    
    def normalize_image(self, image: Image.Image) -> Image.Image:
        """
        Нормализует изображение для обработки.
        
        Args:
            image: Входное изображение
            
        Returns:
            Image.Image: Нормализованное изображение
        """
        # Конвертируем в RGB если нужно
        if image.mode != 'RGB':
            if image.mode == 'RGBA':
                # Создаем белый фон для RGBA
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])  # Используем альфа канал как маску
                image = background
            else:
                image = image.convert('RGB')
        
        return image
    
    def calculate_quality_score(
        self, 
        original: Image.Image, 
        result: Image.Image,
        method: str
    ) -> float:
        """
        Вычисляет оценку качества генерации.
        
        Args:
            original: Оригинальное изображение
            result: Результат обработки
            method: Использованный метод
            
        Returns:
            float: Оценка качества от 0.0 до 1.0
        """
        try:
            # Базовые проверки
            if not result or result.size != original.size:
                return 0.0
            
            # Конвертируем в numpy для анализа
            original_np = np.array(original.convert('L'))
            result_np = np.array(result.convert('L'))
            
            # Проверяем, что результат не пустой
            if np.all(result_np == result_np[0, 0]):
                return 0.1  # Полностью однородное изображение - очень низкое качество
            
            # Проверяем наличие деталей
            edges_original = np.gradient(original_np.astype(float))
            edges_result = np.gradient(result_np.astype(float))
            
            edge_density_original = np.mean(np.abs(edges_original[0]) + np.abs(edges_original[1]))
            edge_density_result = np.mean(np.abs(edges_result[0]) + np.abs(edges_result[1]))
            
            # Оценка сохранения деталей
            if edge_density_original > 0:
                detail_preservation = min(1.0, edge_density_result / edge_density_original)
            else:
                detail_preservation = 0.5
            
            # Базовая оценка качества
            base_score = detail_preservation * 0.7 + 0.3  # Минимум 0.3
            
            # Корректировка по методу
            method_bonuses = {
                'ai_': 0.1,      # AI методы обычно лучше
                'adaptive_': 0.05, # Адаптивные методы немного лучше
                'multi_': 0.05   # Мульти-масштабные методы
            }
            
            for method_prefix, bonus in method_bonuses.items():
                if method.startswith(method_prefix):
                    base_score += bonus
                    break
            
            return min(1.0, base_score)
            
        except Exception as e:
            logger.warning(f"Error calculating quality score: {e}")
            return 0.5  # Средняя оценка при ошибке
    
    def _generate_cache_key(
        self, 
        inputs: Dict[str, Any], 
        method: str
    ) -> str:
        """
        Генерирует ключ для кэширования.
        
        Args:
            inputs: Входные данные
            method: Метод генерации
            
        Returns:
            str: Ключ кэша
        """
        import hashlib
        
        # Создаем строку из входных параметров
        key_parts = [
            method,
            str(inputs.get('width', 512)),
            str(inputs.get('height', 512))
        ]
        
        # Добавляем хэш изображения если есть
        if 'image' in inputs:
            if isinstance(inputs['image'], np.ndarray):
                image_hash = hashlib.md5(inputs['image'].tobytes()).hexdigest()[:8]
            else:
                image_hash = hashlib.md5(np.array(inputs['image']).tobytes()).hexdigest()[:8]
            key_parts.append(image_hash)
        
        # Добавляем хэш текста если есть
        if 'character' in inputs:
            text_hash = hashlib.md5(inputs['character'].encode()).hexdigest()[:8]
            key_parts.append(text_hash)
        
        # Добавляем параметры метода
        method_params = inputs.get('method_params', {})
        if method_params:
            params_str = str(sorted(method_params.items()))
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            key_parts.append(params_hash)
        
        return '_'.join(key_parts)
    
    async def _get_from_cache(self, cache_key: str) -> Optional[ConditioningResult]:
        """
        Получает результат из кэша.
        
        Args:
            cache_key: Ключ кэша
            
        Returns:
            Optional[ConditioningResult]: Результат из кэша или None
        """
        if not self.config.enable_caching:
            return None
        
        if cache_key in self.cache:
            result = self.cache[cache_key]
            # Проверяем срок жизни кэша
            current_time = time.time()
            if hasattr(result, 'cached_at'):
                if current_time - result.cached_at < self.config.cache_ttl_seconds:
                    logger.debug(f"Cache hit for key: {cache_key}")
                    return result
                else:
                    # Удаляем устаревший результат
                    del self.cache[cache_key]
                    logger.debug(f"Cache expired for key: {cache_key}")
        
        return None
    
    async def _save_to_cache(self, cache_key: str, result: ConditioningResult):
        """
        Сохраняет результат в кэш.
        
        Args:
            cache_key: Ключ кэша
            result: Результат для сохранения
        """
        if not self.config.enable_caching or not result.success:
            return
        
        # Добавляем метку времени
        result.cached_at = time.time()
        self.cache[cache_key] = result
        
        # Ограничиваем размер кэша
        max_cache_size = 100
        if len(self.cache) > max_cache_size:
            # Удаляем самые старые записи
            sorted_items = sorted(
                self.cache.items(), 
                key=lambda x: getattr(x[1], 'cached_at', 0)
            )
            
            for key, _ in sorted_items[:len(self.cache) - max_cache_size]:
                del self.cache[key]
        
        logger.debug(f"Cached result for key: {cache_key}")
    
    def _record_performance(self, method: str, processing_time_ms: int):
        """
        Записывает статистику производительности.
        
        Args:
            method: Метод генерации
            processing_time_ms: Время обработки в миллисекундах
        """
        if method not in self.performance_stats:
            self.performance_stats[method] = []
        
        self.performance_stats[method].append(processing_time_ms)
        
        # Ограничиваем размер статистики
        max_stats_size = 1000
        if len(self.performance_stats[method]) > max_stats_size:
            self.performance_stats[method] = self.performance_stats[method][-max_stats_size:]
    
    def get_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Возвращает статистику производительности.
        
        Returns:
            Dict: Статистика по методам
        """
        stats = {}
        
        for method, times in self.performance_stats.items():
            if times:
                stats[method] = {
                    'avg_time_ms': sum(times) / len(times),
                    'min_time_ms': min(times),
                    'max_time_ms': max(times),
                    'total_calls': len(times)
                }
        
        return stats
    
    def clear_cache(self):
        """Очищает кэш результатов."""
        self.cache.clear()
        logger.info("Conditioning cache cleared")
    
    def clear_performance_stats(self):
        """Очищает статистику производительности."""
        self.performance_stats.clear()
        logger.info("Performance stats cleared")
    
    async def batch_generate(
        self, 
        inputs: List[Dict[str, Any]], 
        method: str = None
    ) -> List[ConditioningResult]:
        """
        Пакетная генерация conditioning.
        
        Args:
            inputs: Список входных данных
            method: Метод генерации
            
        Returns:
            List[ConditioningResult]: Список результатов
        """
        results = []
        
        for input_data in inputs:
            try:
                if 'image' in input_data:
                    result = await self.generate_from_image(
                        input_data['image'], 
                        method=method,
                        **{k: v for k, v in input_data.items() if k != 'image'}
                    )
                elif 'character' in input_data:
                    result = await self.generate_from_text(
                        input_data['character'],
                        method=method,
                        **{k: v for k, v in input_data.items() if k != 'character'}
                    )
                else:
                    result = ConditioningResult(
                        success=False,
                        error_message="No valid input found (image or character)"
                    )
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error in batch generation: {e}")
                results.append(ConditioningResult(
                    success=False,
                    error_message=str(e)
                ))
        
        return results
    
    async def validate_and_process_inputs(
        self,
        character: Optional[str] = None,
        image: Optional[Image.Image] = None,
        width: int = 512,
        height: int = 512,
        **kwargs
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Валидирует и обрабатывает входные данные.
        
        Args:
            character: Иероглиф для обработки
            image: Изображение для обработки
            width: Ширина результата
            height: Высота результата
            **kwargs: Дополнительные параметры
            
        Returns:
            Tuple[bool, str, Dict]: (валидно, сообщение об ошибке, обработанные данные)
        """
        processed_data = {
            'width': width,
            'height': height,
            'method_params': kwargs
        }
        
        # Проверяем входные данные
        if not character and not image:
            return False, "Either character or image must be provided", {}
        
        if character and image:
            return False, "Provide either character or image, not both", {}
        
        # Валидируем размеры
        if width < 100 or width > 2048 or height < 100 or height > 2048:
            return False, "Width and height must be between 100 and 2048 pixels", {}
        
        # Обрабатываем изображение если есть
        if image:
            if not self.validate_image(image):
                return False, "Invalid image provided", {}
            
            processed_data['image'] = self.normalize_image(image)
        
        # Обрабатываем иероглиф если есть
        if character:
            if not character.strip():
                return False, "Character cannot be empty", {}
            
            if len(character) > 10:  # Ограничение на длину
                return False, "Character too long (max 10 characters)", {}
            
            processed_data['character'] = character.strip()
        
        return True, "", processed_data
    