"""
Tests for writing_images API routes.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.routes.writing_images import router
from app.services.writing_image_service import GenerationResult
from app.services.validation_service import ValidationResult
from app.api.models.responses import WritingImageMetadata


# Create test app
app = FastAPI()
app.include_router(router, prefix="/api/writing")

client = TestClient(app)


class TestWritingImagesRoutes:
    
    @patch('app.api.routes.writing_images.get_writing_image_service')
    @patch('app.api.routes.writing_images.get_validation_service')
    def test_generate_writing_image_success(self, mock_validation_service, mock_writing_service):
        """Test successful writing image generation."""
        # Setup
        mock_validation = AsyncMock()
        mock_validation.validate_request.return_value = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )
        mock_validation_service.return_value = mock_validation
        
        mock_service = AsyncMock()
        mock_metadata = WritingImageMetadata(
            word="test",
            language="english",
            style="print",
            width=600,
            height=600,
            format="png",
            size_bytes=1000
        )
        mock_service.generate_image.return_value = GenerationResult(
            success=True,
            image_data=b"test_image",
            image_data_base64="dGVzdF9pbWFnZQ==",
            format="png",
            metadata=mock_metadata
        )
        mock_writing_service.return_value = mock_service
        
        # Execute
        response = client.post(
            "/api/writing/generate-writing-image",
            json={
                "word": "test",
                "language": "english",
                "style": "print",
                "width": 600,
                "height": 600
            }
        )
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["image_data"] == "dGVzdF9pbWFnZQ=="
        assert data["format"] == "png"
        assert data["metadata"]["word"] == "test"
    
    @patch('app.api.routes.writing_images.get_writing_image_service')
    @patch('app.api.routes.writing_images.get_validation_service')
    def test_generate_writing_image_validation_error(self, mock_validation_service, mock_writing_service):
        """Test writing image generation with validation error."""
        # Setup
        mock_validation = AsyncMock()
        mock_validation.validate_request.return_value = ValidationResult(
            is_valid=False,
            errors=["Word cannot be empty"],
            warnings=[]
        )
        mock_validation_service.return_value = mock_validation
        
        # Execute
        response = client.post(
            "/api/writing/generate-writing-image",
            json={
                "word": "",
                "language": "english"
            }
        )
        
        # Verify
        assert response.status_code == 400
        data = response.json()
        assert "Validation failed" in data["detail"]
    
    @patch('app.api.routes.writing_images.get_writing_image_service')
    @patch('app.api.routes.writing_images.get_validation_service')
    def test_generate_writing_image_generation_error(self, mock_validation_service, mock_writing_service):
        """Test writing image generation with generation error."""
        # Setup
        mock_validation = AsyncMock()
        mock_validation.validate_request.return_value = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )
        mock_validation_service.return_value = mock_validation
        
        mock_service = AsyncMock()
        mock_service.generate_image.return_value = GenerationResult(
            success=False,
            error="Generation failed"
        )
        mock_writing_service.return_value = mock_service
        
        # Execute
        response = client.post(
            "/api/writing/generate-writing-image",
            json={
                "word": "test",
                "language": "english"
            }
        )
        
        # Verify
        assert response.status_code == 500
        data = response.json()
        assert "Generation failed" in data["detail"]
    
    @patch('app.api.routes.writing_images.get_writing_image_service')
    @patch('app.api.routes.writing_images.get_validation_service')
    def test_generate_writing_image_binary_success(self, mock_validation_service, mock_writing_service):
        """Test successful binary writing image generation."""
        # Setup
        mock_validation = AsyncMock()
        mock_validation.validate_request.return_value = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )
        mock_validation_service.return_value = mock_validation
        
        mock_service = AsyncMock()
        mock_service.generate_image.return_value = GenerationResult(
            success=True,
            image_data=b"test_image",
            format="png"
        )
        mock_writing_service.return_value = mock_service
        
        # Execute
        response = client.post(
            "/api/writing/generate-writing-image-binary",
            json={
                "word": "test",
                "language": "english"
            }
        )
        
        # Verify
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert response.content == b"test_image"
    
    @patch('app.api.routes.writing_images.WritingImageService')
    def test_get_generation_status_success(self, mock_service_class):
        """Test successful status retrieval."""
        # Setup
        mock_service = AsyncMock()
        mock_service.get_service_status.return_value = {
            "status": "healthy",
            "total_generations": 5
        }
        mock_service_class.return_value = mock_service
        
        # Execute
        response = client.get("/api/writing/status")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["status"] == "healthy"
    
    @patch('app.api.routes.writing_images.WritingImageService')
    def test_get_generation_status_error(self, mock_service_class):
        """Test status retrieval with error."""
        # Setup
        mock_service = AsyncMock()
        mock_service.get_service_status.side_effect = Exception("Service error")
        mock_service_class.return_value = mock_service
        
        # Execute
        response = client.get("/api/writing/status")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Service error" in data["error"]
        