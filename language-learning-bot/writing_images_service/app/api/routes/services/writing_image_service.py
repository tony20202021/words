"""
Writing image generation service.
Сервис генерации картинок написания.
STUB IMPLEMENTATION - returns placeholder images for development.
"""

import io
import base64
import time
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

from app.api.models.requests import WritingImageRequest
from app.api.models.responses import WritingImageMetadata
from app.utils import config_holder

logger = logging.getLogger(__name__)


class GenerationResult:
    """
    Result of image generation operation.
    Результат операции генерации изображения.
    """
    
    def __init__(
        self, 
        success: bool, 
        image_data: Optional[bytes] = None,
        image_data_base64: Optional[str] = None,
        format: str = "png",
        metadata: Optional[WritingImageMetadata] = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.image_data = image_data
        self.image_data_base64 = image_data_base64
        self.format = format
        self.metadata = metadata
        self.error = error


class WritingImageService:
    """
    Service for generating writing images.
    Сервис для генерации картинок написания.
    """
    
    def __init__(self):
        """Initialize the writing image service."""
        self.generation_count = 0
        self.start_time = time.time()
        
        # Load configuration
        self._load_config()
        
        logger.info("WritingImageService initialized")
    
    def _load_config(self):
        """Load configuration from Hydra config."""
        # Default values
        self.default_width = 400
        self.default_height = 400
        self.bg_color = (240, 240, 240)
        self.border_color = (180, 180, 180)
        self.text_color = (120, 120, 120)
        self.font_size = 24
        
        try:
            if hasattr(config_holder, 'cfg') and hasattr(config_holder.cfg, 'generation'):
                gen_config = config_holder.cfg.generation
                
                # Default settings
                if hasattr(gen_config, 'defaults'):
                    defaults = gen_config.defaults
                    self.default_width = defaults.get('width', self.default_width)
                    self.default_height = defaults.get('height', self.default_height)
                
                # Stub settings
                if hasattr(gen_config, 'stub'):
                    stub_config = gen_config.stub
                    self.default_width = stub_config.get('width', self.default_width)
                    self.default_height = stub_config.get('height', self.default_height)
                    
                    # Colors
                    self.bg_color = tuple(stub_config.get('background', self.bg_color))
                    self.border_color = tuple(stub_config.get('border', self.border_color))
                    self.text_color = tuple(stub_config.get('text', self.text_color))
                    
                    # Font
                    self.font_size = stub_config.get('font_size', self.font_size)
                    
        except Exception as e:
            logger.warning(f"Could not load generation config, using defaults: {e}")
    
    async def generate_image(self, request: WritingImageRequest) -> GenerationResult:
        """
        Generate writing image for the given request.
        STUB IMPLEMENTATION - generates placeholder image.
        
        Args:
            request: Writing image generation request
            
        Returns:
            GenerationResult: Result of generation
        """
        start_time = time.time()
        
        try:
            logger.info(f"Generating writing image stub for word: '{request.word}', language: '{request.language}'")
            
            # Simulate some processing time
            await asyncio.sleep(0.1)
            
            # Generate stub image
            image_buffer = await self._generate_stub_image(
                word=request.word,
                language=request.language,
                style=request.style,
                width=request.width,
                height=request.height
            )
            
            # Convert to base64
            image_buffer.seek(0)
            image_data = image_buffer.read()
            image_data_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Calculate generation time
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            # Create metadata
            metadata = WritingImageMetadata(
                word=request.word,
                language=request.language,
                style=request.style,
                width=request.width,
                height=request.height,
                format="png",
                size_bytes=len(image_data),
                generation_time_ms=generation_time_ms,
                quality=request.quality,
                show_guidelines=request.show_guidelines
            )
            
            # Update statistics
            self.generation_count += 1
            
            logger.info(f"Generated writing image stub for word: {request.word} "
                       f"(size: {len(image_data)} bytes, time: {generation_time_ms}ms)")
            
            return GenerationResult(
                success=True,
                image_data=image_data,
                image_data_base64=image_data_base64,
                format="png",
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error generating writing image stub: {e}", exc_info=True)
            return GenerationResult(
                success=False,
                error=f"Generation failed: {str(e)}"
            )
    
    async def _generate_stub_image(
        self, 
        word: str, 
        language: str,
        style: str,
        width: int,
        height: int
    ) -> io.BytesIO:
        """
        Generate stub image for development.
        Генерирует заглушку изображения для разработки.
        
        Args:
            word: Word to display
            language: Language code
            style: Writing style
            width: Image width
            height: Image height
            
        Returns:
            io.BytesIO: Image buffer
        """
        # Use requested dimensions or defaults
        img_width = width if width else self.default_width
        img_height = height if height else self.default_height
        
        # Create image
        image = Image.new('RGB', (img_width, img_height), self.bg_color)
        draw = ImageDraw.Draw(image)
        
        # Draw border
        border_width = 2
        draw.rectangle(
            [border_width, border_width, img_width-border_width, img_height-border_width],
            outline=self.border_color,
            width=border_width
        )
        
        # Load font
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        
        # Main title
        title_text = "Writing Image"
        if font:
            bbox = draw.textbbox((0, 0), title_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width, text_height = len(title_text) * 8, 20
        
        title_x = (img_width - text_width) // 2
        title_y = (img_height - text_height) // 2 - 60
        
        draw.text(
            (title_x, title_y),
            title_text,
            fill=self.text_color,
            font=font
        )
        
        # Word text
        word_text = f"Word: {word}"
        if font:
            bbox = draw.textbbox((0, 0), word_text, font=font)
            text_width = bbox[2] - bbox[0]
        else:
            text_width = len(word_text) * 8
        
        word_x = (img_width - text_width) // 2
        word_y = title_y + 40
        
        draw.text(
            (word_x, word_y),
            word_text,
            fill=self.text_color,
            font=font
        )
        
        # Language and style
        lang_text = f"Language: {language}"
        if font:
            bbox = draw.textbbox((0, 0), lang_text, font=font)
            text_width = bbox[2] - bbox[0]
        else:
            text_width = len(lang_text) * 8
        
        lang_x = (img_width - text_width) // 2
        lang_y = word_y + 30
        
        draw.text(
            (lang_x, lang_y),
            lang_text,
            fill=self.text_color,
            font=font
        )
        
        # Style text
        style_text = f"Style: {style}"
        if font:
            bbox = draw.textbbox((0, 0), style_text, font=font)
            text_width = bbox[2] - bbox[0]
        else:
            text_width = len(style_text) * 8
        
        style_x = (img_width - text_width) // 2
        style_y = lang_y + 30
        
        draw.text(
            (style_x, style_y),
            style_text,
            fill=self.text_color,
            font=font
        )
        
        # Stub indicator
        stub_text = "(Development Stub)"
        if font:
            bbox = draw.textbbox((0, 0), stub_text, font=font)
            text_width = bbox[2] - bbox[0]
        else:
            text_width = len(stub_text) * 6
        
        stub_x = (img_width - text_width) // 2
        stub_y = style_y + 40
        
        draw.text(
            (stub_x, stub_y),
            stub_text,
            fill=self.text_color,
            font=font
        )
        
        # Save to buffer
        image_buffer = io.BytesIO()
        image.save(image_buffer, format='PNG', quality=95, optimize=True)
        image_buffer.seek(0)
        
        return image_buffer
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get service status information.
        Получает информацию о статусе сервиса.
        
        Returns:
            Dict with service status
        """
        uptime_seconds = int(time.time() - self.start_time)
        
        return {
            "service": "writing_image_service",
            "status": "healthy",
            "version": "1.0.0",
            "uptime_seconds": uptime_seconds,
            "total_generations": self.generation_count,
            "implementation": "stub",
            "supported_languages": [
                "chinese", "japanese", "korean", "english", 
                "russian", "arabic", "hindi", "spanish", "french"
            ],
            "supported_formats": ["png"],
            "max_image_size": {"width": 2048, "height": 2048},
            "default_image_size": {"width": 600, "height": 600}
        }
    
    async def get_supported_languages(self) -> Dict[str, Any]:
        """
        Get supported languages and their options.
        Получает поддерживаемые языки и их параметры.
        
        Returns:
            Dict with language information
        """
        return {
            "chinese": {
                "name": "Chinese",
                "styles": ["traditional", "simplified", "calligraphy"],
                "default_style": "traditional"
            },
            "japanese": {
                "name": "Japanese", 
                "styles": ["hiragana", "katakana", "kanji"],
                "default_style": "kanji"
            },
            "korean": {
                "name": "Korean",
                "styles": ["hangul"],
                "default_style": "hangul"
            },
            "english": {
                "name": "English",
                "styles": ["print", "cursive"],
                "default_style": "print"
            }
        }
    