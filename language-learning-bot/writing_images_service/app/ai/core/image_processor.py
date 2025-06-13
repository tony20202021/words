"""
Image Processor
Менеджер для обработки изображений иероглифов.
"""

import time
from typing import Dict, Any, Optional
from PIL import Image

from app.utils.logger import get_module_logger
from app.utils.image_utils import get_image_processor
from app.ai.core.generation_config import AIGenerationConfig

logger = get_module_logger(__name__)


class ImageProcessor:
    """
    Менеджер для предобработки изображений иероглифов.
    """
    
    def __init__(self, config: AIGenerationConfig):
        """
        Инициализация Image Processor.
        
        Args:
            config: Конфигурация AI генерации
        """
        self.config = config
        self.image_processor = get_image_processor()
        
        # Статистика
        self.processing_count = 0
        self.total_processing_time = 0
        self.start_time = time.time()
        
        logger.info("ImageProcessor initialized")
    
    async def preprocess_character(
        self, 
        character: str, 
        width: int, 
        height: int
    ) -> Image.Image:
        """
        Предобработка иероглифа - рендеринг в изображение.
        
        Args:
            character: Иероглиф для рендеринга
            width: Ширина изображения
            height: Высота изображения
            
        Returns:
            Image.Image: Отрендеренное изображение иероглифа
        """
        start_time = time.time()
        
        try:
            # Используем ImageProcessor для рендеринга с автоподбором шрифта
            image = await self.image_processor.create_image(width, height, (255, 255, 255))
            
            # Добавляем иероглиф с автоподбором размера
            margin = min(width, height) // 10
            max_text_width = width - 2 * margin
            max_text_height = height - 2 * margin
            
            image, font_size = await self.image_processor.add_auto_fit_text(
                image=image,
                text=character,
                max_width=max_text_width,
                max_height=max_text_height,
                initial_font_size=min(width, height),
                text_color=(0, 0, 0),
                center_horizontal=True,
                center_vertical=True
            )
            
            # Обновляем статистику
            processing_time = time.time() - start_time
            self.processing_count += 1
            self.total_processing_time += processing_time
            
            logger.info(f"Rendered character '{character}' with font size {font_size} "
                       f"in {processing_time:.3f}s")
            
            return image
            
        except Exception as e:
            logger.error(f"Error preprocessing character {character}: {e}")
            raise RuntimeError(f"Character preprocessing failed: {e}")
    
    async def resize_image(
        self,
        image: Image.Image,
        target_width: int,
        target_height: int,
        maintain_aspect_ratio: bool = True
    ) -> Image.Image:
        """
        Изменяет размер изображения.
        
        Args:
            image: Исходное изображение
            target_width: Целевая ширина
            target_height: Целевая высота
            maintain_aspect_ratio: Сохранять ли пропорции
            
        Returns:
            Image.Image: Изображение с измененным размером
        """
        try:
            if maintain_aspect_ratio:
                # Сохраняем пропорции
                image.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
                
                # Создаем новое изображение с целевыми размерами и центрируем
                new_image = Image.new('RGB', (target_width, target_height), (255, 255, 255))
                
                # Вычисляем позицию для центрирования
                x = (target_width - image.width) // 2
                y = (target_height - image.height) // 2
                
                new_image.paste(image, (x, y))
                return new_image
            else:
                # Просто изменяем размер без сохранения пропорций
                return image.resize((target_width, target_height), Image.Resampling.LANCZOS)
                
        except Exception as e:
            logger.error(f"Error resizing image: {e}")
            raise RuntimeError(f"Image resizing failed: {e}")
    
    async def normalize_image(
        self,
        image: Image.Image,
        target_format: str = "RGB"
    ) -> Image.Image:
        """
        Нормализует изображение (формат, размер, etc).
        
        Args:
            image: Исходное изображение
            target_format: Целевой формат (RGB, RGBA, L)
            
        Returns:
            Image.Image: Нормализованное изображение
        """
        try:
            # Конвертируем в целевой формат если нужно
            if image.mode != target_format:
                if target_format == "RGB" and image.mode == "RGBA":
                    # Создаем белый фон для RGBA -> RGB конверсии
                    background = Image.new("RGB", image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1])  # Используем alpha канал как маску
                    image = background
                else:
                    image = image.convert(target_format)
            
            return image
            
        except Exception as e:
            logger.error(f"Error normalizing image: {e}")
            raise RuntimeError(f"Image normalization failed: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Возвращает статус Image Processor"""
        uptime_seconds = int(time.time() - self.start_time)
        avg_processing_time = (
            self.total_processing_time / self.processing_count 
            if self.processing_count > 0 else 0
        )
        
        return {
            "processing_count": self.processing_count,
            "total_processing_time_seconds": self.total_processing_time,
            "average_processing_time_seconds": avg_processing_time,
            "uptime_seconds": uptime_seconds,
            "default_image_size": (self.config.width, self.config.height),
            "image_processor_ready": self.image_processor is not None
        }
    
    async def cleanup(self):
        """Очищает ресурсы Image Processor"""
        try:
            logger.info("Cleaning up Image Processor...")
            
            # Image Processor не требует специальной очистки
            # Работает с базовыми PIL операциями
            
            logger.info("✓ Image Processor cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during image processor cleanup: {e}")
            