"""
API client for writing image generation service.
Клиент для взаимодействия с сервисом генерации картинок написания.
UPDATED: Removed stub mode, configured for real service calls.
"""

import io
import asyncio
from typing import Dict, Optional, Any

import aiohttp

from app.utils import config_holder
from app.utils.logger import get_module_logger

# Настройка логгера
logger = get_module_logger(__name__)


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
        retry_count: int = 1,
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
        translation: str = "",
        hint_writing: str = "",
        show_debug: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate writing image for a word.
        Генерирует картинку написания для слова.
        
        Args:
            word: Word to generate image for
            translation: Translation of the word
            hint_writing: Hint for writing the word
            show_debug: Whether to show debug information
            
        Returns:
            Dict with status and result fields:
            {
                "success": bool,
                "status": int,
                "result": {
                    "generated_image": bytes,  # Image binary data
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
        
        # TODO - брать из конфига
        width = 512
        height = 512
        batch_size = 1

        include_conditioning_images = show_debug
        include_prompt = show_debug
        include_semantic_analysis = show_debug

        # Prepare request data
        request_data = {
            "word": word,
            "translation": translation,
            "hint_writing": hint_writing,
            "width": width,
            "height": height,
            "include_conditioning_images": include_conditioning_images,
            "include_prompt": include_prompt,
            "include_semantic_analysis": include_semantic_analysis,
            "batch_size": batch_size,
        }

        logger.info(f"Generating writing image for word: '{word}', translation: '{translation}'")
        
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
                            logger.error(f"service: {url}, request_data={request_data}")
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
                            generated_image = await response.read()
                            response_dict["result"] = {
                                "generated_image": generated_image,
                                "format": response.content_type.split('/')[-1],
                                "metadata": {
                                    "word": word,
                                    "translation": translation,
                                    "size": len(generated_image)
                                }
                            }
                        elif response.content_type == 'application/json':
                            # JSON response with image data
                            json_data = await response.json()
                            logger.info(f"json_data keys: {list(json_data.keys())}")
                            
                            # Writing Service возвращает данные напрямую, не в поле "result"
                            if json_data.get("success"):
                                if "generated_image_base64" in json_data:
                                    import base64
                                    try:
                                        generated_image = base64.b64decode(json_data["generated_image_base64"]) if json_data["generated_image_base64"] is not None else None
                                        base_image = base64.b64decode(json_data["base_image_base64"]) if json_data["base_image_base64"] is not None else None
                                        conditioning_images  = {}
                                        for key_type in json_data["conditioning_images_base64"].keys():
                                            conditioning_images[key_type] = {}
                                            for key_method in json_data["conditioning_images_base64"][key_type].keys():
                                                conditioning_images[key_type][key_method] = base64.b64decode(json_data["conditioning_images_base64"][key_type][key_method]) if json_data["conditioning_images_base64"][key_type][key_method] is not None else None
                                        response_dict["result"] = {
                                            "generated_image": generated_image,
                                            "format": json_data.get("format", None),
                                            "success": json_data.get("success", False),
                                            "status": json_data.get("status", None),
                                            "base_image": base_image,
                                            "conditioning_images": conditioning_images,
                                            "prompt_used": json_data.get("prompt_used", None),
                                            "generation_metadata": json_data.get("generation_metadata", None),
                                            "error": json_data.get("error", None),
                                            "warnings": json_data.get("warnings", None),
                                        }
                                        logger.info(f"Successfully decoded image data, size: {len(generated_image)} bytes")
                                    except Exception as decode_error:
                                        logger.error(f"Failed to decode base64 image data: {decode_error}")
                                        response_dict["error"] = f"Failed to decode image data: {decode_error}"
                                        return response_dict
                                else:
                                    logger.error("Missing generated_image in successful response")
                                    response_dict["error"] = "Missing generated_image in response"
                                    return response_dict
                            else:
                                error_message = json_data.get("error", "Service returned success=false")
                                logger.error(f"Service error: {error_message}")
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

