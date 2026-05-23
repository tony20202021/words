"""
Models for writing image generation requests and responses.
Модели данных для запросов и ответов сервиса генерации картинок написания.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class WritingImageRequest(BaseModel):
    """
    Request model for writing image generation.
    Модель запроса для генерации картинки написания.
    """
    word: str = Field(..., description="Word to generate image for")
    language: str = Field(default="chinese", description="Language code")
    style: str = Field(default="traditional", description="Writing style")
    width: int = Field(default=600, ge=100, le=2000, description="Image width in pixels")
    height: int = Field(default=600, ge=100, le=2000, description="Image height in pixels")
    show_guidelines: bool = Field(default=True, description="Whether to show guide lines")
    quality: int = Field(default=90, ge=1, le=100, description="Image quality (1-100)")
    
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


class WritingImageMetadata(BaseModel):
    """
    Metadata for generated writing image.
    Метаданные для сгенерированной картинки написания.
    """
    word: str = Field(..., description="Original word")
    language: str = Field(..., description="Language code")
    style: str = Field(..., description="Writing style used")
    width: int = Field(..., description="Image width")
    height: int = Field(..., description="Image height")
    format: str = Field(..., description="Image format (png, jpg)")
    size_bytes: int = Field(..., description="Image size in bytes")
    generation_time_ms: Optional[int] = Field(None, description="Generation time in milliseconds")
    stroke_count: Optional[int] = Field(None, description="Number of strokes in the character")
    complexity_level: Optional[str] = Field(None, description="Character complexity (simple, medium, complex)")


class WritingImageResponse(BaseModel):
    """
    Response model for writing image generation.
    Модель ответа для генерации картинки написания.
    """
    success: bool = Field(..., description="Whether generation was successful")
    image_data: Optional[str] = Field(None, description="Base64 encoded image data")
    format: str = Field(default="png", description="Image format")
    metadata: Optional[WritingImageMetadata] = Field(None, description="Image metadata")
    error: Optional[str] = Field(None, description="Error message if generation failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "image_data": "iVBORw0KGgoAAAANSUhEUgAA...",
                "format": "png",
                "metadata": {
                    "word": "你好",
                    "language": "chinese",
                    "style": "traditional",
                    "width": 600,
                    "height": 600,
                    "format": "png",
                    "size_bytes": 15234,
                    "generation_time_ms": 1500,
                    "stroke_count": 15,
                    "complexity_level": "medium"
                },
                "error": None
            }
        }


class ServiceHealthResponse(BaseModel):
    """
    Service health check response.
    Ответ проверки здоровья сервиса.
    """
    status: str = Field(..., description="Service status")
    version: Optional[str] = Field(None, description="Service version")
    uptime_seconds: Optional[int] = Field(None, description="Service uptime in seconds")
    supported_languages: Optional[List[str]] = Field(None, description="List of supported languages")
    max_image_size: Optional[Dict[str, int]] = Field(None, description="Maximum image dimensions")


class SupportedLanguage(BaseModel):
    """
    Model for supported language information.
    Модель информации о поддерживаемом языке.
    """
    code: str = Field(..., description="Language code")
    name: str = Field(..., description="Language name")
    native_name: str = Field(..., description="Native language name")
    writing_systems: List[str] = Field(..., description="Supported writing systems")
    styles: List[str] = Field(..., description="Available writing styles")
    complexity_levels: Optional[List[str]] = Field(None, description="Character complexity levels")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "chinese",
                "name": "Chinese",
                "native_name": "中文",
                "writing_systems": ["simplified", "traditional"],
                "styles": ["traditional", "simplified", "calligraphy"],
                "complexity_levels": ["simple", "medium", "complex"]
            }
        }


class LanguagesResponse(BaseModel):
    """
    Response model for supported languages.
    Модель ответа со списком поддерживаемых языков.
    """
    success: bool = Field(..., description="Whether request was successful")
    languages: List[SupportedLanguage] = Field(..., description="List of supported languages")
    total_count: int = Field(..., description="Total number of supported languages")
    error: Optional[str] = Field(None, description="Error message if request failed")


class WritingImageError(BaseModel):
    """
    Model for writing image generation errors.
    Модель для ошибок генерации картинок написания.
    """
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    word: Optional[str] = Field(None, description="Word that caused the error")
    language: Optional[str] = Field(None, description="Language that caused the error")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "UNSUPPORTED_CHARACTER",
                "message": "Character not supported in the selected writing system",
                "details": {
                    "supported_characters": ["你", "好", "世", "界"],
                    "unsupported_character": "ä"
                },
                "word": "bäd",
                "language": "chinese"
            }
        }


# Common response wrapper
class APIResponse(BaseModel):
    """
    Generic API response wrapper.
    Общая обертка для ответов API.
    """
    success: bool = Field(..., description="Whether request was successful")
    status: int = Field(..., description="HTTP status code")
    result: Optional[Any] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message")
    timestamp: Optional[str] = Field(None, description="Response timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status": 200,
                "result": {"message": "Operation completed successfully"},
                "error": None,
                "timestamp": "2025-06-05T12:00:00Z"
            }
        }
        