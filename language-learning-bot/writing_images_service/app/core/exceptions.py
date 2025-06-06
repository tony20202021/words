"""
Custom exceptions for writing image service.
Кастомные исключения для сервиса генерации картинок написания.
"""

from typing import Optional, Dict, Any


class WritingServiceException(Exception):
    """
    Base exception for writing image service.
    Базовое исключение для сервиса картинок написания.
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "exception_type": self.__class__.__name__
        }


class ValidationError(WritingServiceException):
    """
    Exception raised when request validation fails.
    Исключение при ошибке валидации запроса.
    """
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None,
        value: Optional[Any] = None,
        constraint: Optional[str] = None
    ):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = value
        if constraint:
            details["constraint"] = constraint
            
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details
        )
        self.field = field
        self.value = value
        self.constraint = constraint


class GenerationError(WritingServiceException):
    """
    Exception raised when image generation fails.
    Исключение при ошибке генерации изображения.
    """
    
    def __init__(
        self, 
        message: str, 
        word: Optional[str] = None,
        language: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        details = {}
        if word:
            details["word"] = word
        if language:
            details["language"] = language
        if cause:
            details["cause"] = str(cause)
            details["cause_type"] = type(cause).__name__
            
        super().__init__(
            message=message,
            error_code="GENERATION_ERROR",
            details=details
        )
        self.word = word
        self.language = language
        self.cause = cause


class ConfigurationError(WritingServiceException):
    """
    Exception raised when configuration is invalid.
    Исключение при ошибке конфигурации.
    """
    
    def __init__(
        self, 
        message: str, 
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None
    ):
        details = {}
        if config_key:
            details["config_key"] = config_key
        if config_value is not None:
            details["config_value"] = config_value
            
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=details
        )
        self.config_key = config_key
        self.config_value = config_value


class ResourceError(WritingServiceException):
    """
    Exception raised when resource access fails.
    Исключение при ошибке доступа к ресурсу.
    """
    
    def __init__(
        self, 
        message: str, 
        resource_type: Optional[str] = None,
        resource_path: Optional[str] = None
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_path:
            details["resource_path"] = resource_path
            
        super().__init__(
            message=message,
            error_code="RESOURCE_ERROR",
            details=details
        )
        self.resource_type = resource_type
        self.resource_path = resource_path


class FontError(WritingServiceException):
    """
    Exception raised when font loading or processing fails.
    Исключение при ошибке загрузки или обработки шрифта.
    """
    
    def __init__(
        self, 
        message: str, 
        font_path: Optional[str] = None,
        font_size: Optional[int] = None
    ):
        details = {}
        if font_path:
            details["font_path"] = font_path
        if font_size:
            details["font_size"] = font_size
            
        super().__init__(
            message=message,
            error_code="FONT_ERROR",
            details=details
        )
        self.font_path = font_path
        self.font_size = font_size


class ImageProcessingError(WritingServiceException):
    """
    Exception raised when image processing fails.
    Исключение при ошибке обработки изображения.
    """
    
    def __init__(
        self, 
        message: str, 
        operation: Optional[str] = None,
        image_format: Optional[str] = None,
        dimensions: Optional[tuple] = None
    ):
        details = {}
        if operation:
            details["operation"] = operation
        if image_format:
            details["image_format"] = image_format
        if dimensions:
            details["dimensions"] = dimensions
            
        super().__init__(
            message=message,
            error_code="IMAGE_PROCESSING_ERROR",
            details=details
        )
        self.operation = operation
        self.image_format = image_format
        self.dimensions = dimensions


class ServiceUnavailableError(WritingServiceException):
    """
    Exception raised when service is temporarily unavailable.
    Исключение при временной недоступности сервиса.
    """
    
    def __init__(
        self, 
        message: str, 
        retry_after: Optional[int] = None,
        reason: Optional[str] = None
    ):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        if reason:
            details["reason"] = reason
            
        super().__init__(
            message=message,
            error_code="SERVICE_UNAVAILABLE",
            details=details
        )
        self.retry_after = retry_after
        self.reason = reason


class RateLimitError(WritingServiceException):
    """
    Exception raised when rate limit is exceeded.
    Исключение при превышении лимита запросов.
    """
    
    def __init__(
        self, 
        message: str, 
        limit: Optional[int] = None,
        window: Optional[int] = None,
        retry_after: Optional[int] = None
    ):
        details = {}
        if limit:
            details["limit"] = limit
        if window:
            details["window"] = window
        if retry_after:
            details["retry_after"] = retry_after
            
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            details=details
        )
        self.limit = limit
        self.window = window
        self.retry_after = retry_after


class UnsupportedLanguageError(ValidationError):
    """
    Exception raised when language is not supported.
    Исключение при неподдерживаемом языке.
    """
    
    def __init__(
        self, 
        language: str,
        supported_languages: Optional[list] = None
    ):
        details = {
            "language": language,
            "supported_languages": supported_languages or []
        }
        
        message = f"Language '{language}' is not supported"
        if supported_languages:
            message += f". Supported languages: {', '.join(supported_languages)}"
            
        super().__init__(
            message=message,
            field="language",
            value=language,
            constraint="supported_language"
        )
        self.error_code = "UNSUPPORTED_LANGUAGE"
        self.details.update(details)


class UnsupportedStyleError(ValidationError):
    """
    Exception raised when writing style is not supported.
    Исключение при неподдерживаемом стиле написания.
    """
    
    def __init__(
        self, 
        style: str,
        language: Optional[str] = None,
        supported_styles: Optional[list] = None
    ):
        details = {
            "style": style,
            "language": language,
            "supported_styles": supported_styles or []
        }
        
        message = f"Style '{style}' is not supported"
        if language:
            message += f" for language '{language}'"
        if supported_styles:
            message += f". Supported styles: {', '.join(supported_styles)}"
            
        super().__init__(
            message=message,
            field="style",
            value=style,
            constraint="supported_style"
        )
        self.error_code = "UNSUPPORTED_STYLE"
        self.details.update(details)


class InvalidDimensionsError(ValidationError):
    """
    Exception raised when image dimensions are invalid.
    Исключение при некорректных размерах изображения.
    """
    
    def __init__(
        self, 
        width: int,
        height: int,
        min_width: int = 100,
        max_width: int = 2048,
        min_height: int = 100,
        max_height: int = 2048
    ):
        details = {
            "width": width,
            "height": height,
            "min_width": min_width,
            "max_width": max_width,
            "min_height": min_height,
            "max_height": max_height
        }
        
        message = f"Invalid dimensions {width}x{height}. "
        message += f"Width must be {min_width}-{max_width}, height must be {min_height}-{max_height}"
        
        super().__init__(
            message=message,
            field="dimensions",
            value=f"{width}x{height}",
            constraint="valid_dimensions"
        )
        self.error_code = "INVALID_DIMENSIONS"
        self.details.update(details)


# Exception mapping for HTTP status codes
EXCEPTION_STATUS_MAP = {
    ValidationError: 400,
    UnsupportedLanguageError: 400,
    UnsupportedStyleError: 400,
    InvalidDimensionsError: 400,
    ConfigurationError: 500,
    GenerationError: 500,
    ResourceError: 500,
    FontError: 500,
    ImageProcessingError: 500,
    ServiceUnavailableError: 503,
    RateLimitError: 429,
    WritingServiceException: 500
}


def get_http_status_for_exception(exception: Exception) -> int:
    """
    Get appropriate HTTP status code for exception.
    Получает подходящий HTTP статус код для исключения.
    
    Args:
        exception: Exception instance
        
    Returns:
        HTTP status code
    """
    exception_type = type(exception)
    return EXCEPTION_STATUS_MAP.get(exception_type, 500)
