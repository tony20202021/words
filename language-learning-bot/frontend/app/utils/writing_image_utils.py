"""
Utilities for working with writing images.
Утилиты для работы с картинками написания.
"""

import io
import hashlib
import asyncio
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta

from app.utils.logger import setup_logger
from app.utils import config_holder

logger = setup_logger(__name__)


def validate_writing_image_request(
    word: str, 
    language: str, 
    width: int = 600, 
    height: int = 600
) -> Dict[str, Any]:
    """
    Validate writing image generation request.
    Валидирует запрос на генерацию картинки написания.
    
    Args:
        word: Word to validate
        language: Language code
        width: Image width
        height: Image height
        
    Returns:
        Dict with validation results
    """
    errors = []
    warnings = []
    
    # Validate word
    if not word or not word.strip():
        errors.append("Word cannot be empty")
    elif len(word.strip()) > 50:
        errors.append("Word is too long (max 50 characters)")
    
    # Validate language
    supported_languages = ["chinese", "japanese", "korean", "english"]  # Stub list
    if language not in supported_languages:
        warnings.append(f"Language '{language}' may not be fully supported")
    
    # Validate dimensions
    if width < 100 or width > 2000:
        errors.append("Width must be between 100 and 2000 pixels")
    
    if height < 100 or height > 2000:
        errors.append("Height must be between 100 and 2000 pixels")
    
    # Validate aspect ratio
    aspect_ratio = width / height
    if aspect_ratio < 0.5 or aspect_ratio > 2.0:
        warnings.append("Unusual aspect ratio may affect image quality")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "word": word.strip() if word else "",
        "language": language,
        "dimensions": {"width": width, "height": height}
    }
