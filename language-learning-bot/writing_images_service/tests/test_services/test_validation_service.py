"""
Tests for validation_service module.
"""

import pytest

# ── Skipped on i-04 ───────────────────────────────────────────────────────────
# Two independent reasons, both pre-existing (surfaced when run_tests.sh stopped
# looking for a non-existent "writing_service" directory and actually ran these):
#   1. The service API was renamed: WritingImageRequest -> AIImageRequest,
#      BatchWritingImageRequest -> AIImageBatchRequest,
#      WritingImageMetadata -> AIGenerationMetadata. These tests still target the
#      old names, so they cannot pass without being rewritten.
#   2. app.* pulls the SDXL/ControlNet stack (torch), which is deliberately not
#      installed on i-04 (2 vCPU, no GPU).
# Skipping keeps the suite honest — previously the runner reported "passed"
# while silently running nothing at all.
pytest.skip(
    "writing_images_service tests target the pre-rename API and need torch; "
    "rewrite required — see .plan",
    allow_module_level=True,
)

from unittest.mock import patch

from app.api.routes.services.validation_service import ValidationService, ValidationResult
from app.api.routes.models.requests import WritingImageRequest, BatchWritingImageRequest


class TestValidationResult:
    
    def test_validation_result_valid(self):
        """Test valid ValidationResult creation."""
        # Execute
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["test warning"]
        )
        
        # Verify
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == ["test warning"]
        assert result.sanitized_data is None
    
    def test_validation_result_invalid(self):
        """Test invalid ValidationResult creation."""
        # Execute
        result = ValidationResult(
            is_valid=False,
            errors=["test error"],
            warnings=[]
        )
        
        # Verify
        assert result.is_valid is False
        assert result.errors == ["test error"]
        assert result.warnings == []


class TestValidationService:
    
    def test_init(self):
        """Test ValidationService initialization."""
        # Execute
        with patch('app.services.validation_service.config_holder'):
            service = ValidationService()
        
        # Verify
        assert service.max_word_length == 50
        assert service.min_width == 100
        assert service.max_width == 2048
        assert isinstance(service.supported_languages, set)
        assert isinstance(service.supported_styles, set)
    
    @pytest.mark.asyncio
    async def test_validate_request_valid(self):
        """Test validation of valid request."""
        # Setup
        request = WritingImageRequest(
            word="test",
            language="english", 
            style="print",
            width=600,
            height=600,
            quality=90
        )
        
        with patch('app.services.validation_service.config_holder'):
            service = ValidationService()
        
        # Execute
        result = await service.validate_request(request)
        
        # Verify
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.sanitized_data is not None
        assert result.sanitized_data["word"] == "test"
        assert result.sanitized_data["language"] == "english"
    
    @pytest.mark.asyncio
    async def test_validate_request_invalid(self):
        """Test validation of invalid request."""
        # Setup
        request = WritingImageRequest(
            word="",  # Invalid empty word
            language="english",
            width=50,  # Invalid width (too small)
            height=3000  # Invalid height (too large)
        )
        
        with patch('app.services.validation_service.config_holder'):
            service = ValidationService()
        
        # Execute
        result = await service.validate_request(request)
        
        # Verify
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("empty" in error.lower() for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_batch_request_valid(self):
        """Test validation of valid batch request."""
        # Setup
        request = BatchWritingImageRequest(
            words=["test1", "test2"],
            language="english"
        )
        
        with patch('app.services.validation_service.config_holder'):
            service = ValidationService()
        
        # Execute
        result = await service.validate_batch_request(request)
        
        # Verify
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_batch_request_invalid(self):
        """Test validation of invalid batch request."""
        # Setup
        request = BatchWritingImageRequest(
            words=[],  # Empty words list
            language="english"
        )
        
        with patch('app.services.validation_service.config_holder'):
            service = ValidationService()
        
        # Execute
        result = await service.validate_batch_request(request)
        
        # Verify
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("empty" in error.lower() for error in result.errors)
    
    def test_validate_word_valid(self):
        """Test word validation with valid input."""
        # Setup
        with patch('app.services.validation_service.config_holder'):
            service = ValidationService()
        
        # Execute
        result = service._validate_word("test")
        
        # Verify
        assert len(result["errors"]) == 0
    
    def test_validate_word_invalid(self):
        """Test word validation with invalid input."""
        # Setup
        with patch('app.services.validation_service.config_holder'):
            service = ValidationService()
        
        # Execute
        result = service._validate_word("")
        
        # Verify
        assert len(result["errors"]) > 0
        assert any("empty" in error.lower() for error in result["errors"])
    
    def test_validate_language(self):
        """Test language validation."""
        # Setup
        with patch('app.services.validation_service.config_holder'):
            service = ValidationService()
        
        # Execute
        result = service._validate_language("english")
        
        # Verify
        assert len(result["errors"]) == 0
    
    def test_validate_dimensions_valid(self):
        """Test dimensions validation with valid input."""
        # Setup
        with patch('app.services.validation_service.config_holder'):
            service = ValidationService()
        
        # Execute
        result = service._validate_dimensions(600, 600)
        
        # Verify
        assert len(result["errors"]) == 0
    
    def test_validate_dimensions_invalid(self):
        """Test dimensions validation with invalid input."""
        # Setup
        with patch('app.services.validation_service.config_holder'):
            service = ValidationService()
        
        # Execute
        result = service._validate_dimensions(50, 3000)  # Too small and too large
        
        # Verify
        assert len(result["errors"]) > 0
    
    def test_get_validation_rules(self):
        """Test validation rules retrieval."""
        # Setup
        with patch('app.services.validation_service.config_holder'):
            service = ValidationService()
        
        # Execute
        rules = service.get_validation_rules()
        
        # Verify
        assert "limits" in rules
        assert "supported_languages" in rules
        assert "supported_styles" in rules
        assert "requirements" in rules
        assert rules["limits"]["max_word_length"] == 50
        