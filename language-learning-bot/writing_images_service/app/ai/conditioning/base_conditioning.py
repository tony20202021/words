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


@dataclass
class ConditioningResult:
    """Результат генерации conditioning"""
    success: bool
    image: Optional[Image.Image] = None
    method_used: str = ""
    processing_time_ms: int = 0
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
    