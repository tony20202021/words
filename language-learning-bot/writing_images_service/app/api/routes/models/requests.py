"""
Request models for writing image generation service.
Модели запросов для сервиса генерации картинок написания.
"""

from typing import Optional
from pydantic import BaseModel, Field, validator


class WritingImageRequest(BaseModel):
    """
    Request model for writing image generation.
    Модель запроса для генерации картинки написания.
    """
    word: str = Field(..., description="Word to generate image for", min_length=1, max_length=50)
    language: str = Field(default="chinese", description="Language code")
    style: str = Field(default="traditional", description="Writing style")
    width: int = Field(default=600, ge=100, le=2048, description="Image width in pixels")
    height: int = Field(default=600, ge=100, le=2048, description="Image height in pixels")
    show_guidelines: bool = Field(default=True, description="Whether to show guide lines")
    quality: int = Field(default=90, ge=1, le=100, description="Image quality (1-100)")
    
    @validator('word')
    def validate_word(cls, v):
        """Validate word input."""
        if not v or not v.strip():
            raise ValueError('Word cannot be empty')
        return v.strip()
    
    @validator('language')
    def validate_language(cls, v):
        """Validate language code."""
        allowed_languages = ['chinese', 'japanese', 'korean', 'english', 'russian', 'arabic', 'hindi']
        if v.lower() not in allowed_languages:
            # Don't raise error, just log warning - support any language
            pass
        return v.lower()
    
    @validator('style')
    def validate_style(cls, v):
        """Validate writing style."""
        allowed_styles = ['traditional', 'simplified', 'calligraphy', 'print', 'cursive', 'hiragana', 'katakana', 'kanji', 'hangul']
        if v.lower() not in allowed_styles:
            # Default to traditional if unknown style
            return 'traditional'
        return v.lower()
    
    @validator('width', 'height')
    def validate_dimensions(cls, v):
        """Validate image dimensions."""
        if v < 100:
            return 100
        elif v > 2048:
            return 2048
        return v
    
    @validator('quality')
    def validate_quality(cls, v):
        """Validate image quality."""
        if v < 1:
            return 1
        elif v > 100:
            return 100
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "word": "你好",
                "language": "chinese",
                "style": "traditional",
                "width": 600,
                "height": 600,
                "show_guidelines": True,
                "quality": 90
            }
        }


class BatchWritingImageRequest(BaseModel):
    """
    Request model for batch writing image generation.
    Модель запроса для пакетной генерации картинок написания.
    """
    words: list[str] = Field(..., description="List of words to generate images for", min_items=1, max_items=10)
    language: str = Field(default="chinese", description="Language code")
    style: str = Field(default="traditional", description="Writing style")
    width: int = Field(default=600, ge=100, le=2048, description="Image width in pixels")
    height: int = Field(default=600, ge=100, le=2048, description="Image height in pixels")
    show_guidelines: bool = Field(default=True, description="Whether to show guide lines")
    quality: int = Field(default=90, ge=1, le=100, description="Image quality (1-100)")
    
    @validator('words')
    def validate_words(cls, v):
        """Validate words list."""
        if not v:
            raise ValueError('Words list cannot be empty')
        
        # Filter out empty words and validate length
        valid_words = []
        for word in v:
            if word and word.strip() and len(word.strip()) <= 50:
                valid_words.append(word.strip())
        
        if not valid_words:
            raise ValueError('No valid words in the list')
        
        return valid_words
    
    class Config:
        json_schema_extra = {
            "example": {
                "words": ["你好", "世界", "学习"],
                "language": "chinese",
                "style": "traditional",
                "width": 600,
                "height": 600,
                "show_guidelines": True,
                "quality": 90
            }
        }


class GenerationOptionsRequest(BaseModel):
    """
    Request model for getting generation options.
    Модель запроса для получения опций генерации.
    """
    language: Optional[str] = Field(None, description="Language code to get specific options")
    
    class Config:
        json_schema_extra = {
            "example": {
                "language": "chinese"
            }
        }
        