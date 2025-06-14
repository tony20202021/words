"""
Validation service for writing image generation requests.
Сервис валидации запросов на генерацию картинок написания.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.api.routes.models.requests import AIImageRequest
from app.utils import config_holder

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Result of validation operation.
    Результат операции валидации.
    """
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    sanitized_data: Optional[Dict[str, Any]] = None


class ValidationService:
    """
    Service for validating writing image generation requests.
    Сервис для валидации запросов на генерацию картинок написания.
    """
    
    def __init__(self):
        """Initialize validation service."""
        self._load_config()
        logger.info("ValidationService initialized with universal language support")
    
    def _load_config(self):
        """Load validation configuration."""
        # Default limits
        self.max_word_length = 50
        self.min_width = 100
        self.max_width = 2048
        self.min_height = 100
        self.max_height = 2048
        
        try:
            if hasattr(config_holder, 'cfg') and hasattr(config_holder.cfg, 'generation'):
                gen_config = config_holder.cfg.generation
                
                # Load limits from config
                if hasattr(gen_config, 'limits'):
                    limits = gen_config.limits
                    self.max_word_length = limits.get('max_word_length', self.max_word_length)
                    self.min_width = limits.get('min_width', self.min_width)
                    self.max_width = limits.get('max_width', self.max_width)
                    self.min_height = limits.get('min_height', self.min_height)
                    self.max_height = limits.get('max_height', self.max_height)
                    
        except Exception as e:
            logger.warning(f"Could not load validation config, using defaults: {e}")
    
    async def validate_request(self, request: AIImageRequest) -> ValidationResult:
        """
        Validate writing image generation request.
        Валидирует запрос на генерацию картинки написания.
        
        Args:
            request: Writing image generation request
            
        Returns:
            ValidationResult: Validation result
        """
        errors = []
        warnings = []
        
        # Validate word
        word_validation = self._validate_word(request.word)
        errors.extend(word_validation['errors'])
        warnings.extend(word_validation['warnings'])
        
        # Validate dimensions
        dimensions_validation = self._validate_dimensions(request.width, request.height)
        errors.extend(dimensions_validation['errors'])
        warnings.extend(dimensions_validation['warnings'])
        
        # Create sanitized data
        sanitized_data = {
            'word': request.word.strip(),
            'width': max(self.min_width, min(self.max_width, request.width)),
            'height': max(self.min_height, min(self.max_height, request.height)),
        }
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.warning(f"Validation failed for request: {errors}")
        elif warnings:
            logger.info(f"Validation warnings for request: {warnings}")
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            sanitized_data=sanitized_data
        )
    
    def _validate_word(self, word: str) -> Dict[str, List[str]]:
        """Validate word parameter."""
        errors = []
        warnings = []
        
        if not word or not word.strip():
            errors.append("Word cannot be empty")
            return {'errors': errors, 'warnings': warnings}
        
        word = word.strip()
        
        if len(word) > self.max_word_length:
            errors.append(f"Word length cannot exceed {self.max_word_length} characters")
        
        # Check for potentially problematic characters
        if re.search(r'[<>"\'/\\]', word):
            warnings.append("Word contains special characters that may affect rendering")
        
        # Check for control characters
        if re.search(r'[\x00-\x1f\x7f-\x9f]', word):
            errors.append("Word contains control characters")
        
        # Check for excessive whitespace
        if re.search(r'\s{2,}', word):
            warnings.append("Word contains multiple consecutive spaces")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_dimensions(self, width: int, height: int) -> Dict[str, List[str]]:
        """Validate image dimensions."""
        errors = []
        warnings = []
        
        if width < self.min_width:
            errors.append(f"Width must be at least {self.min_width} pixels")
        elif width > self.max_width:
            errors.append(f"Width cannot exceed {self.max_width} pixels")
        
        if height < self.min_height:
            errors.append(f"Height must be at least {self.min_height} pixels")
        elif height > self.max_height:
            errors.append(f"Height cannot exceed {self.max_height} pixels")
        
        # Check aspect ratio
        if width > 0 and height > 0:
            aspect_ratio = width / height
            if aspect_ratio < 0.1 or aspect_ratio > 10:
                warnings.append("Extreme aspect ratio may affect image quality")
        
        # Check for very large images
        if width * height > 2048 * 2048:
            warnings.append("Large image size may increase generation time")
        
        return {'errors': errors, 'warnings': warnings}
    
    def get_validation_rules(self) -> Dict[str, Any]:
        """
        Get current validation rules and limits.
        Получает текущие правила валидации и ограничения.
        
        Returns:
            Dict with validation rules
        """
        return {
            'limits': {
                'max_word_length': self.max_word_length,
                'min_width': self.min_width,
                'max_width': self.max_width,
                'min_height': self.min_height,
                'max_height': self.max_height,
            },
            'requirements': {
                'word': 'Non-empty string, max 50 characters, no control characters',
                'dimensions': f'{self.min_width}-{self.max_width}x{self.min_height}-{self.max_height} pixels',
            }
        }
    
    # TODO - сделать реализацию
    # hint_validation = await validation_service.validate_user_hint(request.hint_writing)
