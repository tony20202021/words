"""
Utilities for working with images in writing service.
Утилиты для работы с изображениями в сервисе картинок написания.
"""

import io
import os
import base64
import asyncio
import logging
from typing import Tuple, Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

from common.utils.font_utils import get_font_manager, FontManager

logger = logging.getLogger(__name__)


class ImageProcessor:
    """
    Image processing utilities for writing images.
    Утилиты обработки изображений для картинок написания.
    """
    
    def __init__(self):
        """Initialize image processor."""
        self.temp_dir = "./temp/generated_images"
        self.font_manager = get_font_manager()
        self._ensure_temp_dir()
    
    def _ensure_temp_dir(self):
        """Ensure temporary directory exists."""
        try:
            os.makedirs(self.temp_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create temp directory: {e}")
    
    async def create_image(
        self, 
        width: int, 
        height: int, 
        background_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> Image.Image:
        """
        Create a new image with specified dimensions.
        Создает новое изображение с указанными размерами.
        
        Args:
            width: Image width
            height: Image height
            background_color: RGB background color
            
        Returns:
            PIL Image object
        """
        return Image.new('RGB', (width, height), background_color)
    
    async def add_text_to_image(
        self,
        image: Image.Image,
        text: str,
        position: Tuple[int, int],
        font_size: int = 24,
        text_color: Tuple[int, int, int] = (0, 0, 0),
        font_path: Optional[str] = None
    ) -> Image.Image:
        """
        Add text to an image with Unicode support.
        Добавляет текст к изображению с поддержкой Unicode.
        
        Args:
            image: PIL Image object
            text: Text to add
            position: (x, y) position for text
            font_size: Font size
            text_color: RGB text color
            font_path: Path to font file (optional)
            
        Returns:
            Modified PIL Image object
        """
        draw = ImageDraw.Draw(image)
        
        # Get Unicode font
        font = await self.font_manager.get_font_async(font_size, font_path)
        
        # Draw text
        draw.text(position, text, fill=text_color, font=font)
        
        return image
    
    async def add_auto_fit_text(
        self,
        image: Image.Image,
        text: str,
        max_width: int,
        max_height: int,
        initial_font_size: int = 80,
        min_font_size: int = 12,
        text_color: Tuple[int, int, int] = (0, 0, 0),
        font_path: Optional[str] = None,
        center_horizontal: bool = True,
        center_vertical: bool = True,
        offset_x: int = 0,
        offset_y: int = 0
    ) -> Tuple[Image.Image, int]:
        """
        Add text with automatic font size fitting.
        Добавляет текст с автоматическим подбором размера шрифта.
        
        Args:
            image: PIL Image object
            text: Text to add
            max_width: Maximum text width
            max_height: Maximum text height
            initial_font_size: Starting font size
            min_font_size: Minimum font size
            text_color: RGB text color
            font_path: Path to font file (optional)
            center_horizontal: Center text horizontally
            center_vertical: Center text vertically
            offset_x: X offset from center
            offset_y: Y offset from center
            
        Returns:
            Tuple of (modified image, final font size)
        """
        # Auto-fit font size
        font, final_font_size, text_width, text_height = await self.font_manager.auto_fit_font_size(
            text, max_width, max_height, initial_font_size, min_font_size, font_path
        )
        
        # Calculate position
        image_width, image_height = image.size
        
        if center_horizontal:
            x = (image_width - text_width) // 2 + offset_x
        else:
            x = offset_x
            
        if center_vertical:
            y = (image_height - text_height) // 2 + offset_y
        else:
            y = offset_y
        
        # Draw text
        draw = ImageDraw.Draw(image)
        draw.text((x, y), text, fill=text_color, font=font)
        
        return image, final_font_size
    
    async def add_border_to_image(
        self,
        image: Image.Image,
        border_width: int = 2,
        border_color: Tuple[int, int, int] = (128, 128, 128)
    ) -> Image.Image:
        """
        Add border to an image.
        Добавляет рамку к изображению.
        
        Args:
            image: PIL Image object
            border_width: Width of border in pixels
            border_color: RGB border color
            
        Returns:
            Modified PIL Image object
        """
        draw = ImageDraw.Draw(image)
        width, height = image.size
        
        # Draw border rectangle
        draw.rectangle(
            [0, 0, width - 1, height - 1],
            outline=border_color,
            width=border_width
        )
        
        return image
    
    async def add_guidelines_to_image(
        self,
        image: Image.Image,
        guideline_color: Tuple[int, int, int] = (200, 200, 200),
        guideline_width: int = 1
    ) -> Image.Image:
        """
        Add writing guidelines to an image.
        Добавляет направляющие линии для письма.
        
        Args:
            image: PIL Image object
            guideline_color: RGB color for guidelines
            guideline_width: Width of guideline in pixels
            
        Returns:
            Modified PIL Image object
        """
        draw = ImageDraw.Draw(image)
        width, height = image.size
        
        # Add horizontal center line
        center_y = height // 2
        draw.line(
            [(0, center_y), (width, center_y)],
            fill=guideline_color,
            width=guideline_width
        )
        
        # Add vertical center line
        center_x = width // 2
        draw.line(
            [(center_x, 0), (center_x, height)],
            fill=guideline_color,
            width=guideline_width
        )
        
        # Add quarter lines for better guidance
        quarter_x = width // 4
        three_quarter_x = 3 * width // 4
        quarter_y = height // 4
        three_quarter_y = 3 * height // 4
        
        # Vertical quarter lines
        draw.line(
            [(quarter_x, 0), (quarter_x, height)],
            fill=guideline_color,
            width=max(1, guideline_width // 2)
        )
        draw.line(
            [(three_quarter_x, 0), (three_quarter_x, height)],
            fill=guideline_color,
            width=max(1, guideline_width // 2)
        )
        
        # Horizontal quarter lines
        draw.line(
            [(0, quarter_y), (width, quarter_y)],
            fill=guideline_color,
            width=max(1, guideline_width // 2)
        )
        draw.line(
            [(0, three_quarter_y), (width, three_quarter_y)],
            fill=guideline_color,
            width=max(1, guideline_width // 2)
        )
        
        return image
    
    async def image_to_bytes(
        self,
        image: Image.Image,
        format: str = "PNG",
        quality: int = 90
    ) -> bytes:
        """
        Convert PIL Image to bytes.
        Преобразует PIL Image в байты.
        
        Args:
            image: PIL Image object
            format: Image format (PNG, JPEG, etc.)
            quality: Image quality (1-100, for JPEG)
            
        Returns:
            Image as bytes
        """
        buffer = io.BytesIO()
        
        # Save parameters
        save_kwargs = {"format": format, "optimize": True}
        if format.upper() == "JPEG":
            save_kwargs["quality"] = quality
        
        image.save(buffer, **save_kwargs)
        buffer.seek(0)
        
        return buffer.getvalue()
    
    async def image_to_base64(
        self,
        image: Image.Image,
        format: str = "PNG",
        quality: int = 90
    ) -> str:
        """
        Convert PIL Image to base64 string.
        Преобразует PIL Image в base64 строку.
        
        Args:
            image: PIL Image object
            format: Image format (PNG, JPEG, etc.)
            quality: Image quality (1-100, for JPEG)
            
        Returns:
            Base64 encoded image string
        """
        image_bytes = await self.image_to_bytes(image, format, quality)
        return base64.b64encode(image_bytes).decode('utf-8')
    
    async def calculate_text_size(
        self,
        text: str,
        font_size: int = 24,
        font_path: Optional[str] = None
    ) -> Tuple[int, int]:
        """
        Calculate the size of text when rendered with Unicode support.
        Вычисляет размер текста при отображении с поддержкой Unicode.
        
        Args:
            text: Text to measure
            font_size: Font size
            font_path: Path to font file (optional)
            
        Returns:
            (width, height) of rendered text
        """
        return await self.font_manager.calculate_text_size_async(text, font_size, font_path)
    
    async def center_text_position(
        self,
        image_width: int,
        image_height: int,
        text: str,
        font_size: int = 24,
        font_path: Optional[str] = None,
        offset_x: int = 0,
        offset_y: int = 0
    ) -> Tuple[int, int]:
        """
        Calculate position to center text in an image with Unicode support.
        Вычисляет позицию для центрирования текста в изображении с поддержкой Unicode.
        
        Args:
            image_width: Width of image
            image_height: Height of image
            text: Text to center
            font_size: Font size
            font_path: Path to font file (optional)
            offset_x: X offset from center
            offset_y: Y offset from center
            
        Returns:
            (x, y) position for centered text
        """
        text_width, text_height = await self.calculate_text_size(text, font_size, font_path)
        
        x = (image_width - text_width) // 2 + offset_x
        y = (image_height - text_height) // 2 + offset_y
        
        return (x, y)
    
    async def cleanup_temp_files(self, max_age_hours: int = 24):
        """
        Clean up old temporary files.
        Очищает старые временные файлы.
        
        Args:
            max_age_hours: Maximum age of files to keep in hours
        """
        try:
            if not os.path.exists(self.temp_dir):
                return
            
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            for filename in os.listdir(self.temp_dir):
                filepath = os.path.join(self.temp_dir, filename)
                
                if os.path.isfile(filepath):
                    file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                    
                    if file_time < cutoff_time:
                        os.remove(filepath)
                        logger.debug(f"Cleaned up temp file: {filename}")
        
        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")


# Global processor instance
_processor_instance: Optional[ImageProcessor] = None


def get_image_processor() -> ImageProcessor:
    """
    Get global image processor instance.
    Получает глобальный экземпляр процессора изображений.
    
    Returns:
        ImageProcessor instance
    """
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = ImageProcessor()
    return _processor_instance


async def create_placeholder_image(
    width: int,
    height: int,
    text: str,
    background_color: Tuple[int, int, int] = (240, 240, 240),
    text_color: Tuple[int, int, int] = (120, 120, 120),
    border_color: Tuple[int, int, int] = (180, 180, 180)
) -> bytes:
    """
    Create a placeholder image with text and Unicode support.
    Создает изображение-заглушку с текстом и поддержкой Unicode.
    
    Args:
        width: Image width
        height: Image height
        text: Text to display
        background_color: RGB background color
        text_color: RGB text color
        border_color: RGB border color
        
    Returns:
        Image as bytes
    """
    processor = get_image_processor()
    
    # Create image
    image = await processor.create_image(width, height, background_color)
    
    # Add border
    image = await processor.add_border_to_image(image, 2, border_color)
    
    # Add text with auto-fit
    margin = 20
    image, _ = await processor.add_auto_fit_text(
        image, 
        text, 
        width - 2 * margin, 
        height - 2 * margin,
        initial_font_size=min(width, height) // 10,
        text_color=text_color
    )
    
    # Convert to bytes
    return await processor.image_to_bytes(image)
