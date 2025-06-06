"""
Tests for writing_image_service module.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import io
import base64

from app.services.writing_image_service import WritingImageService, GenerationResult
from app.api.models.requests import WritingImageRequest


class TestGenerationResult:
    
    def test_generation_result_success(self):
        """Test successful GenerationResult creation."""
        # Setup
        image_data = b"test_image_data"
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Execute
        result = GenerationResult(
            success=True,
            image_data=image_data,
            image_data_base64=image_base64,
            format="png"
        )
        
        # Verify
        assert result.success is True
        assert result.image_data == image_data
        assert result.image_data_base64 == image_base64
        assert result.format == "png"
        assert result.metadata is None
        assert result.error is None
    
    def test_generation_result_error(self):
        """Test error GenerationResult creation."""
        # Setup
        error_message = "Test error"
        
        # Execute
        result = GenerationResult(
            success=False,
            error=error_message
        )
        
        # Verify
        assert result.success is False
        assert result.image_data is None
        assert result.image_data_base64 is None
        assert result.format == "png"
        assert result.metadata is None
        assert result.error == error_message


class TestWritingImageService:
    
    def test_init(self):
        """Test WritingImageService initialization."""
        # Execute
        with patch('app.services.writing_image_service.config_holder'):
            service = WritingImageService()
        
        # Verify
        assert service.generation_count == 0
        assert service.start_time is not None
        assert isinstance(service.default_width, int)
        assert isinstance(service.default_height, int)
    
    @pytest.mark.asyncio
    async def test_generate_image_success(self):
        """Test successful image generation."""
        # Setup
        request = WritingImageRequest(
            word="test",
            language="english",
            style="print",
            width=400,
            height=400
        )
        
        mock_image_buffer = io.BytesIO(b"test_image_data")
        
        with patch('app.services.writing_image_service.config_holder'), \
             patch.object(WritingImageService, '_generate_stub_image', 
                         return_value=mock_image_buffer) as mock_generate:
            
            service = WritingImageService()
            
            # Execute
            result = await service.generate_image(request)
            
            # Verify
            assert result.success is True
            assert result.image_data is not None
            assert result.image_data_base64 is not None
            assert result.format == "png"
            assert result.metadata is not None
            assert result.metadata.word == "test"
            assert result.metadata.language == "english"
            assert result.error is None
            
            mock_generate.assert_called_once_with(
                word="test",
                language="english", 
                style="print",
                width=400,
                height=400
            )
    
    @pytest.mark.asyncio
    async def test_generate_image_error(self):
        """Test image generation error handling."""
        # Setup
        request = WritingImageRequest(word="test")
        
        with patch('app.services.writing_image_service.config_holder'), \
             patch.object(WritingImageService, '_generate_stub_image',
                         side_effect=Exception("Test error")):
            
            service = WritingImageService()
            
            # Execute
            result = await service.generate_image(request)
            
            # Verify
            assert result.success is False
            assert result.image_data is None
            assert result.image_data_base64 is None
            assert result.metadata is None
            assert "Test error" in result.error
    
    @pytest.mark.asyncio
    async def test_generate_stub_image(self):
        """Test stub image generation."""
        # Setup
        mock_image = MagicMock()
        mock_draw = MagicMock()
        mock_font = MagicMock()
        mock_buffer = io.BytesIO(b"test_image")
        
        with patch('app.services.writing_image_service.config_holder'), \
             patch('app.services.writing_image_service.Image') as mock_image_class, \
             patch('app.services.writing_image_service.ImageDraw') as mock_draw_class, \
             patch('app.services.writing_image_service.ImageFont') as mock_font_class, \
             patch('io.BytesIO', return_value=mock_buffer):
            
            # Setup mocks
            mock_image_class.new.return_value = mock_image
            mock_draw_class.Draw.return_value = mock_draw
            mock_font_class.load_default.return_value = mock_font
            mock_draw.textbbox.return_value = (0, 0, 100, 20)
            
            service = WritingImageService()
            
            # Execute
            result = await service._generate_stub_image(
                word="test",
                language="english",
                style="print", 
                width=400,
                height=400
            )
            
            # Verify
            assert result == mock_buffer
            mock_image_class.new.assert_called_once_with('RGB', (400, 400), service.bg_color)
            mock_draw_class.Draw.assert_called_once_with(mock_image)
            mock_image.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_service_status(self):
        """Test service status retrieval."""
        # Setup
        with patch('app.services.writing_image_service.config_holder'):
            service = WritingImageService()
            service.generation_count = 5
        
        # Execute
        status = await service.get_service_status()
        
        # Verify
        assert status["service"] == "writing_image_service"
        assert status["status"] == "healthy"
        assert status["total_generations"] == 5
        assert "supported_languages" in status
        assert "supported_formats" in status
    
    @pytest.mark.asyncio
    async def test_get_supported_languages(self):
        """Test supported languages retrieval."""
        # Setup
        with patch('app.services.writing_image_service.config_holder'):
            service = WritingImageService()
        
        # Execute
        languages = await service.get_supported_languages()
        
        # Verify
        assert "chinese" in languages
        assert "japanese" in languages
        assert "korean" in languages
        assert "english" in languages
        assert languages["chinese"]["name"] == "Chinese"
        assert "traditional" in languages["chinese"]["styles"]
        