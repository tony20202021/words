"""
Conditioning Manager
Менеджер для генерации conditioning изображений.
"""

import time
import asyncio
import random
from typing import Dict, Any, Optional
from PIL import Image

from app.utils.logger import get_module_logger
from app.ai.core.generation_config import AIGenerationConfig
from app.ai.conditioning.canny_conditioning import CannyConditioning
from app.ai.conditioning.depth_conditioning import DepthConditioning
from app.ai.conditioning.segmentation_conditioning import SegmentationConditioning
from app.ai.conditioning.scribble_conditioning import ScribbleConditioning

logger = get_module_logger(__name__)


class ConditioningManager:
    """
    Менеджер для генерации всех типов conditioning изображений.
    """
    
    def __init__(self, config: AIGenerationConfig):
        """
        Инициализация Conditioning Manager.
        
        Args:
            config: Конфигурация AI генерации
        """
        self.config = config
        
        # Инициализация conditioning генераторов
        self.conditioning_generators = {
            "canny": CannyConditioning(),
            "depth": DepthConditioning(),
            "segmentation": SegmentationConditioning(),
            "scribble": ScribbleConditioning()
        }
        
        # Статистика
        self.conditioning_count = 0
        self.total_conditioning_time = 0
        self.start_time = time.time()
        
        logger.info("ConditioningManager initialized")
    
    async def ensure_conditioning_ready(self):
        """Обеспечивает готовность conditioning генераторов"""
        # Для базовых conditioning генераторов специальная инициализация не нужна
        # Они готовы к работе сразу
        logger.debug("✓ Conditioning generators ready")
    
    async def generate_all_conditioning(
        self,
        base_image: Image.Image,
        character: str,
        conditioning_methods: Optional[Dict[str, str]] = None
    ) -> Dict[str, Dict[str, Image.Image]]:
        """
        Генерирует все типы conditioning изображений.
        
        Args:
            base_image: Базовое изображение иероглифа
            character: Исходный иероглиф
            conditioning_methods: Методы для разных типов conditioning (опционально)
            
        Returns:
            Dict[str, Dict[str, Image.Image]]: Conditioning изображения
        """
        start_time = time.time()
        
        try:
            # Выбираем случайный тип conditioning для разнообразия
            # В реальности можно генерировать несколько типов параллельно
            conditioning_type = random.choice(list(self.conditioning_generators.keys()))
            generator = self.conditioning_generators[conditioning_type]
            
            # Выбираем метод
            if conditioning_methods and conditioning_type in conditioning_methods:
                method = conditioning_methods[conditioning_type]
            else:
                method = random.choice(generator.get_available_methods())

            conditioning_images = {
                conditioning_type: {
                    method: None
                }
            }
            
            logger.debug(f"Generating {conditioning_type} conditioning with method: {method}")
            
            try:
                result = await generator.generate_from_image(base_image, method=method)
                if result.success and result.image:
                    conditioning_images[conditioning_type][method] = result.image
                    logger.debug(f"✓ Generated {conditioning_type} conditioning "
                               f"(method: {result.method_used}, "
                               f"time: {result.processing_time_ms}ms)")
                else:
                    logger.warning(f"Failed to generate {conditioning_type} conditioning {method}: "
                                 f"{result.error_message}")
                    conditioning_images[conditioning_type][method] = None
                    
            except Exception as e:
                logger.error(f"Error generating {conditioning_type} conditioning {method}: {e}")
                conditioning_images[conditioning_type][method] = None
            
            # Проверяем что хотя бы один conditioning тип сгенерирован
            valid_conditioning = {
                k: v for k, v in conditioning_images.items() 
                if any(img is not None for img in v.values())
            }
            
            if not valid_conditioning:
                raise RuntimeError("No conditioning images could be generated")
            
            # Обновляем статистику
            conditioning_time = time.time() - start_time
            self.conditioning_count += 1
            self.total_conditioning_time += conditioning_time
            
            logger.info(f"✓ Generated conditioning images for: {list(valid_conditioning.keys())} "
                       f"in {conditioning_time:.2f}s")
            
            return conditioning_images
            
        except Exception as e:
            logger.error(f"Error in conditioning generation: {e}")
            raise RuntimeError(f"Conditioning generation failed: {e}")
    
    async def generate_specific_conditioning(
        self,
        base_image: Image.Image,
        conditioning_type: str,
        method: str
    ) -> Optional[Image.Image]:
        """
        Генерирует конкретный тип conditioning.
        
        Args:
            base_image: Базовое изображение
            conditioning_type: Тип conditioning (canny, depth, segmentation, scribble)
            method: Метод генерации
            
        Returns:
            Optional[Image.Image]: Conditioning изображение или None если ошибка
        """
        if conditioning_type not in self.conditioning_generators:
            logger.error(f"Unknown conditioning type: {conditioning_type}")
            return None
        
        try:
            generator = self.conditioning_generators[conditioning_type]
            result = await generator.generate_from_image(base_image, method=method)
            
            if result.success and result.image:
                logger.debug(f"✓ Generated {conditioning_type} conditioning with {method}")
                return result.image
            else:
                logger.warning(f"Failed to generate {conditioning_type} conditioning: {result.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating {conditioning_type} conditioning: {e}")
            return None
    
    def get_available_conditioning_types(self) -> Dict[str, list]:
        """Возвращает доступные типы conditioning и их методы"""
        return {
            conditioning_type: generator.get_available_methods()
            for conditioning_type, generator in self.conditioning_generators.items()
        }
    
    async def get_status(self) -> Dict[str, Any]:
        """Возвращает статус Conditioning Manager"""
        uptime_seconds = int(time.time() - self.start_time)
        avg_conditioning_time = (
            self.total_conditioning_time / self.conditioning_count 
            if self.conditioning_count > 0 else 0
        )
        
        return {
            "conditioning_count": self.conditioning_count,
            "total_conditioning_time_seconds": self.total_conditioning_time,
            "average_conditioning_time_seconds": avg_conditioning_time,
            "uptime_seconds": uptime_seconds,
            "available_conditioning_types": list(self.conditioning_generators.keys()),
            "available_methods": self.get_available_conditioning_types()
        }
    
    async def cleanup(self):
        """Очищает ресурсы Conditioning Manager"""
        try:
            logger.info("Cleaning up Conditioning Manager...")
            
            # Conditioning генераторы не требуют специальной очистки
            # Они работают с базовыми библиотеками OpenCV/PIL
            
            logger.info("✓ Conditioning Manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during conditioning manager cleanup: {e}")
            