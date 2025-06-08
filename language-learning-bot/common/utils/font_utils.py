"""
Utilities for working with fonts in image generation.
Утилиты для работы со шрифтами при генерации изображений.
"""

import os
import asyncio
import logging
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class FontManager:
    """
    Font management utilities with Unicode support.
    Утилиты управления шрифтами с поддержкой Unicode.
    """
    
    def __init__(self):
        """Initialize font manager."""
        self._font_cache: Dict[Tuple[str, int], ImageFont.ImageFont] = {}
        self._font_paths_cache: Optional[List[str]] = None
        self._default_font: Optional[ImageFont.ImageFont] = None
        
    def get_unicode_font_paths(self) -> List[str]:
        """
        Get list of available Unicode font paths.
        Получает список путей к Unicode шрифтам.
        
        Returns:
            List of font file paths with Unicode support
        """
        if self._font_paths_cache is not None:
            return self._font_paths_cache
        
        # Comprehensive list of Unicode font paths for different OS
        unicode_font_paths = [
            # Windows - Unicode шрифты
            "C:/Windows/Fonts/msyh.ttc",           # Microsoft YaHei
            "C:/Windows/Fonts/simsun.ttc",         # SimSun
            "C:/Windows/Fonts/NotoSansCJK-Regular.ttc",  # Noto Sans CJK
            "C:/Windows/Fonts/arial.ttf",          # Arial (частичная поддержка)
            "C:/Windows/Fonts/calibri.ttf",        # Calibri
            
            # macOS - Unicode шрифты  
            "/System/Library/Fonts/PingFang.ttc",  # PingFang SC
            "/System/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/Library/Fonts/Arial.ttf",
            
            # Linux - Noto шрифты (отличная поддержка Unicode)
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto/NotoSans-Regular.ttf",
            
            # Linux - дополнительные Unicode шрифты
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
            "/usr/share/fonts/truetype/droid/DroidSansFallback.ttf",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            
            # Linux - системные пути
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/arial.ttf",
            "/usr/local/share/fonts/arial.ttf",
            "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
            
            # Дополнительные пути для азиатских шрифтов
            "/usr/share/fonts/chinese/TrueType/uming.ttf",
            "/usr/share/fonts/truetype/arphic/uming.ttf",
            "/usr/share/fonts/truetype/arphic/ukai.ttc",
            "/usr/share/fonts/opentype/source-han-sans/SourceHanSans-Regular.otf",
            
            # Flatpak fonts
            "/var/lib/flatpak/runtime/org.freedesktop.Platform/*/active/files/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        ]
        
        # Filter existing paths
        existing_paths = [path for path in unicode_font_paths if os.path.exists(path)]
        
        # Cache the result
        self._font_paths_cache = existing_paths
        
        logger.info(f"Found {len(existing_paths)} Unicode font files")
        if existing_paths:
            logger.debug(f"Available fonts: {existing_paths[:3]}...")  # Show first 3
        
        return existing_paths
    
    def get_font(self, size: int, font_path: Optional[str] = None) -> ImageFont.ImageFont:
        """
        Get font with Unicode support.
        Получает шрифт с поддержкой Unicode.
        
        Args:
            size: Font size
            font_path: Specific font file path (optional)
            
        Returns:
            ImageFont object with Unicode support
        """
        cache_key = (font_path or "auto", size)
        
        # Check cache first
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]
        
        font = None
        
        try:
            if font_path and os.path.exists(font_path):
                # Use specific font
                font = self._load_and_test_font(font_path, size)
                if font:
                    logger.debug(f"Using specified font: {font_path} (size: {size})")
            
            if not font:
                # Try Unicode fonts
                for font_path_candidate in self.get_unicode_font_paths():
                    font = self._load_and_test_font(font_path_candidate, size)
                    if font:
                        logger.debug(f"Using Unicode font: {font_path_candidate} (size: {size})")
                        break
            
            if not font:
                # Fallback to default font
                logger.warning(f"No Unicode fonts found, using default font (size: {size})")
                font = ImageFont.load_default()
                
        except Exception as e:
            logger.error(f"Error loading font: {e}")
            font = ImageFont.load_default()
        
        # Cache the result
        self._font_cache[cache_key] = font
        
        return font
    
    def _load_and_test_font(self, font_path: str, size: int) -> Optional[ImageFont.ImageFont]:
        """
        Load font and test Unicode support.
        Загружает шрифт и тестирует поддержку Unicode.
        
        Args:
            font_path: Path to font file
            size: Font size
            
        Returns:
            ImageFont object if Unicode is supported, None otherwise
        """
        try:
            font = ImageFont.truetype(font_path, size)
            
            # Test Unicode support with various characters
            test_chars = ["得", "あ", "한", "ا", "य", "А", "ñ", "ü"]
            
            temp_img = Image.new('RGB', (100, 100), (255, 255, 255))
            temp_draw = ImageDraw.Draw(temp_img)
            
            unicode_support_count = 0
            for test_char in test_chars:
                try:
                    bbox = temp_draw.textbbox((0, 0), test_char, font=font)
                    # If bbox has non-zero dimensions, font supports the character
                    if bbox[2] > bbox[0] and bbox[3] > bbox[1]:
                        unicode_support_count += 1
                except Exception:
                    continue
            
            # Consider font good if it supports at least 3 out of 8 test characters
            if unicode_support_count >= 3:
                return font
            else:
                logger.debug(f"Font {font_path} supports only {unicode_support_count}/{len(test_chars)} test characters")
                return None
                
        except Exception as e:
            logger.debug(f"Could not load font {font_path}: {e}")
            return None
    
    async def get_font_async(self, size: int, font_path: Optional[str] = None) -> ImageFont.ImageFont:
        """
        Asynchronously get font with Unicode support.
        Асинхронно получает шрифт с поддержкой Unicode.
        
        Args:
            size: Font size
            font_path: Specific font file path (optional)
            
        Returns:
            ImageFont object with Unicode support
        """
        def _load_font():
            return self.get_font(size, font_path)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _load_font)
    
    async def calculate_text_size_async(
        self,
        text: str,
        font_size: int = 24,
        font_path: Optional[str] = None
    ) -> Tuple[int, int]:
        """
        Asynchronously calculate text size with Unicode support.
        Асинхронно вычисляет размер текста с поддержкой Unicode.
        
        Args:
            text: Text to measure
            font_size: Font size
            font_path: Specific font file path (optional)
            
        Returns:
            (width, height) of rendered text
        """
        def _calculate_size():
            font = self.get_font(font_size, font_path)
            
            # Create temporary image to measure text
            temp_image = Image.new('RGB', (1, 1))
            draw = ImageDraw.Draw(temp_image)
            
            bbox = draw.textbbox((0, 0), text, font=font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            
            return (width, height)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _calculate_size)
    
    async def auto_fit_font_size(
        self,
        text: str,
        max_width: int,
        max_height: int,
        initial_font_size: int = 80,
        min_font_size: int = 12,
        font_path: Optional[str] = None
    ) -> Tuple[ImageFont.ImageFont, int, int, int]:
        """
        Automatically fit font size to given dimensions.
        Автоматически подбирает размер шрифта под заданные размеры.
        
        Args:
            text: Text to fit
            max_width: Maximum width
            max_height: Maximum height
            initial_font_size: Starting font size
            min_font_size: Minimum font size
            font_path: Specific font file path (optional)
            
        Returns:
            Tuple of (font, final_font_size, text_width, text_height)
        """
        def _fit_font():
            current_font_size = initial_font_size
            
            while current_font_size >= min_font_size:
                font = self.get_font(current_font_size, font_path)
                
                # Create temporary image to measure text
                temp_image = Image.new('RGB', (1, 1))
                draw = ImageDraw.Draw(temp_image)
                
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                if text_width <= max_width and text_height <= max_height:
                    return font, current_font_size, text_width, text_height
                
                # Reduce font size by 10%
                current_font_size = int(current_font_size * 0.9)
            
            # Return minimum size if nothing fits
            font = self.get_font(min_font_size, font_path)
            temp_image = Image.new('RGB', (1, 1))
            draw = ImageDraw.Draw(temp_image)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            return font, min_font_size, text_width, text_height
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _fit_font)
    
    def clear_cache(self):
        """Clear font cache."""
        self._font_cache.clear()
        logger.debug("Font cache cleared")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get font cache information."""
        return {
            "cached_fonts": len(self._font_cache),
            "available_font_files": len(self.get_unicode_font_paths()),
            "cache_keys": list(self._font_cache.keys())
        }


# Global font manager instance
_font_manager_instance: Optional[FontManager] = None


def get_font_manager() -> FontManager:
    """
    Get global font manager instance.
    Получает глобальный экземпляр менеджера шрифтов.
    
    Returns:
        FontManager instance
    """
    global _font_manager_instance
    if _font_manager_instance is None:
        _font_manager_instance = FontManager()
    return _font_manager_instance


# Convenience functions
async def get_unicode_font_async(size: int, font_path: Optional[str] = None) -> ImageFont.ImageFont:
    """
    Convenience function to get Unicode font asynchronously.
    Удобная функция для асинхронного получения Unicode шрифта.
    """
    manager = get_font_manager()
    return await manager.get_font_async(size, font_path)


async def auto_fit_text_async(
    text: str,
    max_width: int,
    max_height: int,
    initial_font_size: int = 80,
    min_font_size: int = 12
) -> Tuple[ImageFont.ImageFont, int, int, int]:
    """
    Convenience function to auto-fit text asynchronously.
    Удобная функция для автоматического подбора размера текста.
    """
    manager = get_font_manager()
    return await manager.auto_fit_font_size(
        text, max_width, max_height, initial_font_size, min_font_size
    )
