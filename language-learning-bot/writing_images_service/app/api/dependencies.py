"""
FastAPI dependencies for writing image service.
Зависимости FastAPI для сервиса генерации картинок написания.
"""

import time
import logging
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.writing_image_service import WritingImageService
from app.services.validation_service import ValidationService
from app.core.exceptions import ServiceUnavailableError, RateLimitError
from app.utils import config_holder

logger = logging.getLogger(__name__)

# Rate limiting storage (in-memory for development)
_rate_limit_storage: Dict[str, Dict[str, Any]] = {}

# Security scheme for future authentication
security = HTTPBearer(auto_error=False)


async def get_writing_image_service() -> WritingImageService:
    """
    Get writing image service instance.
    Получает экземпляр сервиса генерации картинок.
    
    Returns:
        WritingImageService: Service instance
    """
    return WritingImageService()


async def get_validation_service() -> ValidationService:
    """
    Get validation service instance.
    Получает экземпляр сервиса валидации.
    
    Returns:
        ValidationService: Service instance
    """
    return ValidationService()


async def check_service_health() -> bool:
    """
    Check if the service is healthy and ready to process requests.
    Проверяет, здоров ли сервис и готов ли обрабатывать запросы.
    
    Returns:
        bool: True if service is healthy
        
    Raises:
        ServiceUnavailableError: If service is not available
    """
    try:
        # Check if temp directory is accessible
        import os
        temp_dir = "./temp/generated_images"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Simple write test
        test_file = os.path.join(temp_dir, ".health_check")
        with open(test_file, 'w') as f:
            f.write("health_check")
        os.remove(test_file)
        
        return True
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise ServiceUnavailableError(
            message="Service is currently unavailable",
            reason=str(e)
        )


async def get_client_id(request: Request) -> str:
    """
    Get client identifier for rate limiting.
    Получает идентификатор клиента для ограничения запросов.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Client identifier
    """
    # Use client IP as identifier for now
    client_ip = request.client.host if request.client else "unknown"
    
    # In production, might want to use authentication token or API key
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    return client_ip


async def check_rate_limit(
    request: Request,
    client_id: str = Depends(get_client_id)
) -> bool:
    """
    Check if client has exceeded rate limit.
    Проверяет, превысил ли клиент лимит запросов.
    
    Args:
        request: FastAPI request object
        client_id: Client identifier
        
    Returns:
        bool: True if request is allowed
        
    Raises:
        RateLimitError: If rate limit is exceeded
    """
    # Get rate limit settings
    enabled = False
    limit = 60
    window = 60
    
    try:
        if hasattr(config_holder, 'cfg') and hasattr(config_holder.cfg, 'api'):
            api_config = config_holder.cfg.api
            enabled = api_config.get('enable_rate_limit', False)
            limit = api_config.get('rate_limit_requests', 60)
            window = api_config.get('rate_limit_period', 60)
    except Exception as e:
        logger.warning(f"Could not load rate limit config: {e}")
    
    if not enabled:
        return True
    
    current_time = time.time()
    
    # Initialize client data if not exists
    if client_id not in _rate_limit_storage:
        _rate_limit_storage[client_id] = {
            'requests': [],
            'window_start': current_time
        }
    
    client_data = _rate_limit_storage[client_id]
    
    # Clean old requests outside the window
    client_data['requests'] = [
        req_time for req_time in client_data['requests']
        if current_time - req_time < window
    ]
    
    # Check if limit is exceeded
    if len(client_data['requests']) >= limit:
        retry_after = int(window - (current_time - min(client_data['requests'])))
        
        logger.warning(f"Rate limit exceeded for client {client_id}")
        
        raise RateLimitError(
            message=f"Rate limit exceeded. Maximum {limit} requests per {window} seconds",
            limit=limit,
            window=window,
            retry_after=retry_after
        )
    
    # Add current request
    client_data['requests'].append(current_time)
    
    return True


async def validate_content_type(request: Request) -> bool:
    """
    Validate request content type.
    Валидирует тип содержимого запроса.
    
    Args:
        request: FastAPI request object
        
    Returns:
        bool: True if content type is valid
        
    Raises:
        HTTPException: If content type is invalid
    """
    if request.method in ["POST", "PUT", "PATCH"]:
        content_type = request.headers.get("content-type", "")
        
        if not content_type.startswith("application/json"):
            raise HTTPException(
                status_code=415,
                detail="Unsupported Media Type. Expected application/json"
            )
    
    return True


async def get_request_context(
    request: Request,
    client_id: str = Depends(get_client_id)
) -> Dict[str, Any]:
    """
    Get request context information.
    Получает контекстную информацию запроса.
    
    Args:
        request: FastAPI request object
        client_id: Client identifier
        
    Returns:
        Dict with request context
    """
    return {
        "client_id": client_id,
        "method": request.method,
        "path": str(request.url.path),
        "query_params": dict(request.query_params),
        "headers": dict(request.headers),
        "timestamp": time.time()
    }


async def log_request(
    context: Dict[str, Any] = Depends(get_request_context)
) -> None:
    """
    Log incoming request information.
    Логирует информацию о входящем запросе.
    
    Args:
        context: Request context
    """
    logger.info(
        f"Request: {context['method']} {context['path']} "
        f"from {context['client_id']}"
    )


# Optional authentication dependency (for future use)
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Get current authenticated user (placeholder for future authentication).
    Получает текущего аутентифицированного пользователя (заглушка для будущей аутентификации).
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Optional user information
    """
    # For now, return None (no authentication required)
    # In the future, this could validate JWT tokens or API keys
    
    if credentials:
        # Placeholder for token validation
        logger.debug(f"Received credentials: {credentials.scheme}")
    
    return None


# Combined dependency for common checks
async def common_dependencies(
    _: bool = Depends(check_service_health),
    __: bool = Depends(check_rate_limit),
    ___: bool = Depends(validate_content_type),
    ____: None = Depends(log_request)
) -> None:
    """
    Combined dependency that runs common checks.
    Комбинированная зависимость для общих проверок.
    """
    pass


# Development-only dependencies
async def development_only():
    """
    Dependency that only allows access in development mode.
    Зависимость, которая разрешает доступ только в режиме разработки.
    
    Raises:
        HTTPException: If not in development mode
    """
    try:
        if hasattr(config_holder, 'cfg') and hasattr(config_holder.cfg, 'app'):
            environment = config_holder.cfg.app.get('environment', 'development')
            if environment != 'development':
                raise HTTPException(
                    status_code=403,
                    detail="This endpoint is only available in development mode"
                )
    except Exception:
        # If config is not available, assume development
        pass


# Cache for service instances (singleton pattern)
_service_cache: Dict[str, Any] = {}


async def get_cached_service(service_type: str, service_class):
    """
    Get cached service instance (singleton pattern).
    Получает кэшированный экземпляр сервиса (паттерн синглтон).
    
    Args:
        service_type: Type of service
        service_class: Service class
        
    Returns:
        Service instance
    """
    if service_type not in _service_cache:
        _service_cache[service_type] = service_class()
    
    return _service_cache[service_type]


async def get_cached_writing_service() -> WritingImageService:
    """Get cached writing image service instance."""
    return await get_cached_service("writing_image", WritingImageService)


async def get_cached_validation_service() -> ValidationService:
    """Get cached validation service instance."""
    return await get_cached_service("validation", ValidationService)
