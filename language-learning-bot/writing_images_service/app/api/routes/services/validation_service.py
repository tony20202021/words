"""
Validation service for writing image generation requests.
Сервис валидации запросов на генерацию картинок написания.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.api.routes.models.requests import WritingImageRequest, BatchWritingImageRequest
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
        logger.info("ValidationService initialized")
    
    def _load_config(self):
        """Load validation configuration."""
        # Default limits
        self.max_word_length = 50
        self.min_width = 100
        self.max_width = 2048
        self.min_height = 100
        self.max_height = 2048
        self.min_quality = 1
        self.max_quality = 100
        
        # Supported languages and styles
        self.supported_languages = {
            'chinese', 'japanese', 'korean', 'english', 'russian', 
            'arabic', 'hindi', 'spanish', 'french', 'german', 'italian'
        }
        
        self.supported_styles = {
            'traditional', 'simplified', 'calligraphy', 'print', 'cursive',
            'hiragana', 'katakana', 'kanji', 'hangul'
        }
        
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
                
                # Load supported languages from config
                if hasattr(gen_config, 'languages'):
                    config_languages = set(gen_config.languages.keys())
                    self.supported_languages.update(config_languages)
                    
        except Exception as e:
            logger.warning(f"Could not load validation config, using defaults: {e}")
    
    async def validate_request(self, request: WritingImageRequest) -> ValidationResult:
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
        
        # Validate language
        language_validation = self._validate_language(request.language)
        errors.extend(language_validation['errors'])
        warnings.extend(language_validation['warnings'])
        
        # Validate style
        style_validation = self._validate_style(request.style)
        errors.extend(style_validation['errors'])
        warnings.extend(style_validation['warnings'])
        
        # Validate dimensions
        dimensions_validation = self._validate_dimensions(request.width, request.height)
        errors.extend(dimensions_validation['errors'])
        warnings.extend(dimensions_validation['warnings'])
        
        # Validate quality
        quality_validation = self._validate_quality(request.quality)
        errors.extend(quality_validation['errors'])
        warnings.extend(quality_validation['warnings'])
        
        # Check language-style compatibility
        compatibility_validation = self._validate_language_style_compatibility(
            request.language, request.style
        )
        warnings.extend(compatibility_validation['warnings'])
        
        # Create sanitized data
        sanitized_data = {
            'word': request.word.strip(),
            'language': request.language.lower(),
            'style': request.style.lower(),
            'width': max(self.min_width, min(self.max_width, request.width)),
            'height': max(self.min_height, min(self.max_height, request.height)),
            'quality': max(self.min_quality, min(self.max_quality, request.quality)),
            'show_guidelines': request.show_guidelines
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
    
    async def validate_batch_request(self, request: BatchWritingImageRequest) -> ValidationResult:
        """
        Validate batch writing image generation request.
        Валидирует пакетный запрос на генерацию картинок написания.
        
        Args:
            request: Batch writing image generation request
            
        Returns:
            ValidationResult: Validation result
        """
        errors = []
        warnings = []
        
        # Validate words list
        if not request.words:
            errors.append("Words list cannot be empty")
        elif len(request.words) > 10:
            errors.append("Maximum 10 words allowed in batch request")
        else:
            valid_words = []
            for i, word in enumerate(request.words):
                word_validation = self._validate_word(word)
                if word_validation['errors']:
                    errors.extend([f"Word {i+1}: {error}" for error in word_validation['errors']])
                else:
                    valid_words.append(word.strip())
                warnings.extend([f"Word {i+1}: {warning}" for warning in word_validation['warnings']])
            
            if not valid_words:
                errors.append("No valid words in the batch")
        
        # Validate other parameters (same as single request)
        language_validation = self._validate_language(request.language)
        errors.extend(language_validation['errors'])
        warnings.extend(language_validation['warnings'])
        
        style_validation = self._validate_style(request.style)
        errors.extend(style_validation['errors'])
        warnings.extend(style_validation['warnings'])
        
        dimensions_validation = self._validate_dimensions(request.width, request.height)
        errors.extend(dimensions_validation['errors'])
        warnings.extend(dimensions_validation['warnings'])
        
        quality_validation = self._validate_quality(request.quality)
        errors.extend(quality_validation['errors'])
        warnings.extend(quality_validation['warnings'])
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
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
    
    def _validate_language(self, language: str) -> Dict[str, List[str]]:
        """Validate language parameter."""
        errors = []
        warnings = []
        
        if not language:
            errors.append("Language cannot be empty")
            return {'errors': errors, 'warnings': warnings}
        
        language_lower = language.lower()
        
        if language_lower not in self.supported_languages:
            warnings.append(f"Language '{language}' may not be fully supported")
        
        # Check for valid language code format
        if not re.match(r'^[a-z]{2,10}$', language_lower):
            warnings.append("Language code should contain only lowercase letters")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_style(self, style: str) -> Dict[str, List[str]]:
        """Validate style parameter."""
        errors = []
        warnings = []
        
        if not style:
            warnings.append("Style not specified, using default")
            return {'errors': errors, 'warnings': warnings}
        
        style_lower = style.lower()
        
        if style_lower not in self.supported_styles:
            warnings.append(f"Style '{style}' may not be supported, will use default")
        
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
    
    def _validate_quality(self, quality: int) -> Dict[str, List[str]]:
        """Validate image quality parameter."""
        errors = []
        warnings = []
        
        if quality < self.min_quality:
            errors.append(f"Quality must be at least {self.min_quality}")
        elif quality > self.max_quality:
            errors.append(f"Quality cannot exceed {self.max_quality}")
        
        if quality < 50:
            warnings.append("Low quality setting may result in poor image quality")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_language_style_compatibility(self, language: str, style: str) -> Dict[str, List[str]]:
        """Validate language and style compatibility."""
        errors = []
        warnings = []
        
        # Define incompatible combinations
        incompatible_combinations = {
            'english': ['traditional', 'simplified', 'kanji', 'hiragana', 'katakana', 'hangul'],
            'chinese': ['hiragana', 'katakana', 'hangul'],
            'japanese': ['traditional', 'simplified', 'hangul'],
            'korean': ['traditional', 'simplified', 'kanji', 'hiragana', 'katakana']
        }
        
        language_lower = language.lower()
        style_lower = style.lower()
        
        if language_lower in incompatible_combinations:
            if style_lower in incompatible_combinations[language_lower]:
                warnings.append(f"Style '{style}' may not be appropriate for language '{language}'")
        
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
                'min_quality': self.min_quality,
                'max_quality': self.max_quality
            },
            'supported_languages': sorted(list(self.supported_languages)),
            'supported_styles': sorted(list(self.supported_styles)),
            'requirements': {
                'word': 'Non-empty string, max 50 characters, no control characters',
                'language': 'Lowercase language code',
                'style': 'Supported writing style',
                'dimensions': f'{self.min_width}-{self.max_width}x{self.min_height}-{self.max_height} pixels',
                'quality': f'{self.min_quality}-{self.max_quality}'
            }
        }
    