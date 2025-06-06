"""
API client for writing image generation service.
Клиент для взаимодействия с сервисом генерации картинок написания.
UPDATED: Removed stub mode, configured for real service calls.
"""

import io
import asyncio
import logging
from typing import Dict, Optional, Any

import aiohttp

from app.utils import config_holder

# Настройка логгера
logger = logging.getLogger(__name__)


class WritingImageClient:
    """
    Client for interacting with the writing image generation service.
    Клиент для взаимодействия с сервисом генерации картинок написания.
    """
    
    def __init__(
        self, 
        service_url: str = "http://localhost:8600",
        api_endpoint: str = "/api/generate-writing-image",
        timeout: int = 10,
        retry_count: int = 2,
        retry_delay: int = 1
    ):
        """
        Initialize writing image client.
        
        Args:
            service_url: Base URL of the writing image service
            api_endpoint: API endpoint for generation
            timeout: Request timeout in seconds
            retry_count: Number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.service_url = service_url
        self.api_endpoint = api_endpoint
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        
        logger.info(f"Initialized WritingImageClient with service URL: {self.service_url}")

    async def generate_writing_image(
        self, 
        word: str, 
        language: str = "chinese",
        style: str = "traditional",
        width: int = 600,
        height: int = 600,
        show_guidelines: bool = True
    ) -> Dict[str, Any]:
        """
        Generate writing image for a word.
        Генерирует картинку написания для слова.
        
        Args:
            word: Word to generate image for
            language: Language code (chinese, japanese, korean, etc.)
            style: Writing style (traditional, simplified, calligraphy)
            width: Image width in pixels
            height: Image height in pixels
            show_guidelines: Whether to show guide lines
            
        Returns:
            Dict with status and result fields:
            {
                "success": bool,
                "status": int,
                "result": {
                    "image_data": bytes,  # Image binary data
                    "format": str,        # Image format (png, jpg)
                    "metadata": dict      # Additional metadata
                },
                "error": str
            }
        """
        url = f"{self.service_url}{self.api_endpoint}"
        
        response_dict = {
            "success": False,
            "status": 0,
            "result": None,
            "error": None
        }
        
        # Prepare request data
        request_data = {
            "word": word,
            "language": language,
            "style": style,
            "width": width,
            "height": height,
            "show_guidelines": show_guidelines
        }
        
        logger.info(f"Generating writing image for word: '{word}', language: '{language}'")
        
        # Retry logic
        for attempt in range(self.retry_count):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json=request_data,
                        timeout=self.timeout
                    ) as response:
                        response_dict["status"] = response.status
                        
                        if response.status >= 400:
                            try:
                                error_data = await response.json()
                                error_message = error_data.get("error", f"HTTP {response.status}")
                            except:
                                error_message = f"HTTP {response.status}"
                            
                            logger.error(f"Writing image service error: {response.status} - {error_message}")
                            response_dict["error"] = error_message
                            
                            # Retry on server errors
                            if response.status >= 500 and attempt < self.retry_count - 1:
                                logger.warning(f"Retrying writing image request (attempt {attempt+1}/{self.retry_count})...")
                                await asyncio.sleep(self.retry_delay)
                                continue
                            
                            return response_dict
                        
                        # Check content type
                        if response.content_type.startswith('image/'):
                            # Binary image response
                            image_data = await response.read()
                            response_dict["result"] = {
                                "image_data": image_data,
                                "format": response.content_type.split('/')[-1],
                                "metadata": {
                                    "word": word,
                                    "language": language,
                                    "style": style,
                                    "size": len(image_data)
                                }
                            }
                        elif response.content_type == 'application/json':
                            # JSON response with image data
                            json_data = await response.json()
                            if json_data.get("success") and "result" in json_data:
                                result = json_data["result"]
                                if "image_data" in result:
                                    import base64
                                    image_data = base64.b64decode(result["image_data"])
                                    response_dict["result"] = {
                                        "image_data": image_data,
                                        "format": result.get("format", "png"),
                                        "metadata": result.get("metadata", {})
                                    }
                                else:
                                    response_dict["result"] = result
                            else:
                                error_message = json_data.get("error", "Unknown error from service")
                                response_dict["error"] = error_message
                                return response_dict
                        else:
                            # Unknown content type
                            response_dict["error"] = f"Unexpected content type: {response.content_type}"
                            return response_dict
                        
                        response_dict["success"] = True
                        logger.info(f"Successfully generated writing image for: {word}")
                        return response_dict
                
            except aiohttp.ClientError as e:
                error_message = f"Writing image service request failed: {e}"
                logger.error(error_message)
                response_dict["error"] = error_message
                
                if attempt < self.retry_count - 1:
                    logger.warning(f"Retrying writing image request (attempt {attempt+1}/{self.retry_count})...")
                    await asyncio.sleep(self.retry_delay)
                    continue
        
        # All attempts failed
        logger.error(f"All {self.retry_count} attempts to generate writing image failed")
        return response_dict

    async def check_service_health(self) -> Dict[str, Any]:
        """
        Check if the writing image service is available.
        Проверяет доступность сервиса генерации картинок.
        
        Returns:
            Dict with health check results
        """
        health_url = f"{self.service_url}/health"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(health_url, timeout=5) as response:
                    if response.status == 200:
                        return {
                            "success": True,
                            "status": response.status,
                            "message": "Service is healthy"
                        }
                    else:
                        return {
                            "success": False,
                            "status": response.status,
                            "message": f"Service returned status {response.status}"
                        }
        except Exception as e:
            return {
                "success": False,
                "status": 0,
                "message": f"Service is not available: {e}"
            }


# Global client instance
_client_instance = None


def get_writing_image_client() -> WritingImageClient:
    """
    Get global writing image client instance.
    Получает глобальный экземпляр клиента сервиса картинок.
    
    Returns:
        WritingImageClient: Client instance
    """
    global _client_instance
    if _client_instance is None:
        # Get settings from config
        service_url = "http://localhost:8600"
        api_endpoint = "/api/generate-writing-image"
        timeout = 10
        retry_count = 2
        retry_delay = 1
        
        try:
            if hasattr(config_holder.cfg, 'writing_images'):
                config = config_holder.cfg.writing_images
                service_url = config.get('service_url', service_url)
                api_endpoint = config.get('api_endpoint', api_endpoint)
                timeout = config.get('timeout', timeout)
                retry_count = config.get('retry_count', retry_count)
                retry_delay = config.get('retry_delay', retry_delay)
        except Exception as e:
            logger.warning(f"Could not load writing image client config, using defaults: {e}")
        
        _client_instance = WritingImageClient(
            service_url=service_url,
            api_endpoint=api_endpoint,
            timeout=timeout,
            retry_count=retry_count,
            retry_delay=retry_delay
        )
    return _client_instance


async def generate_writing_image_via_service(
    word: str,
    language: str = "chinese",
    **kwargs
) -> io.BytesIO:
    """
    Convenient function to generate writing image via service.
    Удобная функция для генерации картинки через сервис.
    
    Args:
        word: Word to generate image for
        language: Language code
        **kwargs: Additional generation parameters
        
    Returns:
        io.BytesIO: Image data in memory
        
    Raises:
        Exception: If generation fails
    """
    client = get_writing_image_client()
    result = await client.generate_writing_image(word, language, **kwargs)
    
    if not result["success"]:
        raise Exception(f"Writing image generation failed: {result.get('error', 'Unknown error')}")
    
    image_data = result["result"]["image_data"]
    image_buffer = io.BytesIO(image_data)
    image_buffer.seek(0)
    
    return image_buffer
