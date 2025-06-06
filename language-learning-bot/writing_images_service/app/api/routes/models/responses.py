"""
Response models for writing image generation service.
Модели ответов для сервиса генерации картинок написания.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


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
    quality: Optional[int] = Field(None, description="Image quality used")
    show_guidelines: Optional[bool] = Field(None, description="Whether guidelines were shown")
    
    class Config:
        json_schema_extra = {
            "example": {
                "word": "你好",
                "language": "chinese",
                "style": "traditional",
                "width": 600,
                "height": 600,
                "format": "png",
                "size_bytes": 15234,
                "generation_time_ms": 1500,
                "quality": 90,
                "show_guidelines": True
            }
        }


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
                    "quality": 90,
                    "show_guidelines": True
                },
                "error": None
            }
        }


class BatchWritingImageResponse(BaseModel):
    """
    Response model for batch writing image generation.
    Модель ответа для пакетной генерации картинок написания.
    """
    success: bool = Field(..., description="Whether batch generation was successful")
    total_requested: int = Field(..., description="Total number of images requested")
    total_generated: int = Field(..., description="Total number of images successfully generated")
    images: List[WritingImageResponse] = Field(..., description="List of generated images")
    failed_words: List[str] = Field(default_factory=list, description="Words that failed to generate")
    error: Optional[str] = Field(None, description="General error message if any")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "total_requested": 3,
                "total_generated": 2,
                "images": [
                    {
                        "success": True,
                        "image_data": "iVBORw0KGgoAAAANSUhEUgAA...",
                        "format": "png",
                        "metadata": {"word": "你好", "language": "chinese"}
                    }
                ],
                "failed_words": ["invalid_word"],
                "error": None
            }
        }


class ServiceStatusResponse(BaseModel):
    """
    Response model for service status.
    Модель ответа для статуса сервиса.
    """
    status: str = Field(..., description="Service status")
    version: Optional[str] = Field(None, description="Service version")
    uptime_seconds: Optional[int] = Field(None, description="Service uptime in seconds")
    supported_languages: Optional[List[str]] = Field(None, description="List of supported languages")
    supported_styles: Optional[Dict[str, List[str]]] = Field(None, description="Supported styles per language")
    max_image_size: Optional[Dict[str, int]] = Field(None, description="Maximum image dimensions")
    current_load: Optional[Dict[str, Any]] = Field(None, description="Current service load")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "uptime_seconds": 3600,
                "supported_languages": ["chinese", "japanese", "korean"],
                "supported_styles": {
                    "chinese": ["traditional", "simplified", "calligraphy"]
                },
                "max_image_size": {"width": 2048, "height": 2048},
                "current_load": {"active_generations": 2, "queue_size": 0}
            }
        }


class GenerationOptionsResponse(BaseModel):
    """
    Response model for generation options.
    Модель ответа для опций генерации.
    """
    success: bool = Field(..., description="Whether request was successful")
    languages: List[Dict[str, Any]] = Field(..., description="Available languages and their options")
    default_settings: Dict[str, Any] = Field(..., description="Default generation settings")
    limits: Dict[str, Any] = Field(..., description="Generation limits")
    error: Optional[str] = Field(None, description="Error message if any")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "languages": [
                    {
                        "code": "chinese",
                        "name": "Chinese",
                        "styles": ["traditional", "simplified", "calligraphy"],
                        "default_style": "traditional"
                    }
                ],
                "default_settings": {
                    "width": 600,
                    "height": 600,
                    "quality": 90,
                    "show_guidelines": True
                },
                "limits": {
                    "max_width": 2048,
                    "max_height": 2048,
                    "max_word_length": 50
                },
                "error": None
            }
        }


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


class ErrorResponse(BaseModel):
    """
    Error response model.
    Модель ответа с ошибкой.
    """
    success: bool = Field(False, description="Always false for error responses")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: str = Field(..., description="Error timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "error_message": "Invalid word format",
                "details": {
                    "field": "word",
                    "value": "",
                    "constraint": "min_length"
                },
                "timestamp": "2025-06-05T12:00:00Z"
            }
        }
        