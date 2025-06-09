"""
Writing image generation service.
Сервис генерации картинок написания.
STUB IMPLEMENTATION - returns placeholder images for development.
"""

import base64
import time
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.api.routes.models.requests import AIImageRequest
from app.api.routes.models.responses import AIGenerationMetadata
from app.utils.image_utils import get_image_processor, ImageProcessor
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
        metadata: Optional[AIGenerationMetadata] = None,
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
        self.image_processor = get_image_processor()
        
        # Load configuration
        self._load_config()
        
        logger.info("WritingImageService initialized")
    
    def _load_config(self):
        """Load configuration from Hydra config."""
        # Default values
        self.default_width = 600
        self.default_height = 600
        self.bg_color = (240, 240, 240)
        self.border_color = (180, 180, 180)
        self.text_color = (120, 120, 120)
        self.font_size = 24
        self.show_guidelines_default = True
        
        try:
            if hasattr(config_holder, 'cfg') and hasattr(config_holder.cfg, 'generation'):
                gen_config = config_holder.cfg.generation
                
                # Default settings
                if hasattr(gen_config, 'generation_defaults'):
                    defaults = gen_config.generation_defaults
                    self.default_width = defaults.get('width', self.default_width)
                    self.default_height = defaults.get('height', self.default_height)
                    self.show_guidelines_default = defaults.get('show_guidelines', self.show_guidelines_default)
                
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
    
    async def generate_image(self, request: AIImageRequest) -> GenerationResult:
        """
        Generate writing image for the given request.
        STUB IMPLEMENTATION - generates placeholder image using ImageProcessor.
        
        Args:
            request: Writing image generation request
            
        Returns:
            GenerationResult: Result of generation
        """
        start_time = time.time()
        
        try:
            logger.info(f"Generating writing image stub for word: '{request.word}', translation: '{request.translation}'")
            
            # Use requested dimensions or defaults
            width = request.width if request.width else self.default_width
            height = request.height if request.height else self.default_height
            
            # Generate stub image using ImageProcessor
            image = await self._generate_stub_image_with_processor(
                word=request.word,
                translation=request.translation,
                width=width,
                height=height,
            )
            
            # Convert to bytes and base64
            image_data = await self.image_processor.image_to_bytes(
                image, 
                format="PNG", 
            )
            image_data_base64 = await self.image_processor.image_to_base64(
                image, 
                format="PNG", 
            )
            
            # Calculate generation time
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            # Create metadata
            metadata = AIGenerationMetadata(
                generation_time_ms=generation_time_ms,
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
    
    async def _generate_stub_image_with_processor(
        self, 
        word: str, 
        translation: str,
        width: int,
        height: int,
    ):
        """
        Generate stub image using ImageProcessor.
        Генерирует заглушку изображения используя ImageProcessor.
        
        Args:
            word: Word to display
            translation: Translation
            width: Image width
            height: Image height
            
        Returns:
            PIL.Image: Generated image
        """
        # Create base image
        image = await self.image_processor.create_image(width, height, self.bg_color)
        
        # Add border
        image = await self.image_processor.add_border_to_image(
            image, 
            border_width=2, 
            border_color=self.border_color
        )
        
        # Add title text
        title_text = "Writing Image"
        title_pos = await self.image_processor.center_text_position(
            width, height, title_text, self.font_size, offset_y=-60
        )
        image = await self.image_processor.add_text_to_image(
            image, title_text, title_pos, self.font_size, self.text_color
        )
        
        # Add word text
        word_text = f"Word: {word}"
        word_pos = await self.image_processor.center_text_position(
            width, height, word_text, self.font_size, offset_y=-20
        )
        image = await self.image_processor.add_text_to_image(
            image, word_text, word_pos, self.font_size, self.text_color
        )
        
        # Add translation text
        lang_text = f"Translation: {translation}"
        lang_pos = await self.image_processor.center_text_position(
            width, height, lang_text, self.font_size, offset_y=20
        )
        image = await self.image_processor.add_text_to_image(
            image, lang_text, lang_pos, self.font_size, self.text_color
        )
        
        # Add stub indicator
        stub_text = "(Development Stub)"
        stub_pos = await self.image_processor.center_text_position(
            width, height, stub_text, int(self.font_size * 0.8), offset_y=100
        )
        image = await self.image_processor.add_text_to_image(
            image, stub_text, stub_pos, int(self.font_size * 0.8), 
            (160, 160, 160)  # Lighter color for stub indicator
        )
        
        return image
    
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
            "implementation": "stub_with_image_processor",
            "supported_formats": ["png"],
            "max_image_size": {"width": 2048, "height": 2048},
            "default_image_size": {"width": self.default_width, "height": self.default_height},
            "features": {
                "guidelines": True,
                "borders": True,
                "text_centering": True,
                "async_processing": True,
                "universal_language_support": True
            }
        }
    