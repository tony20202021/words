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


class WritingImageCache:
    """
    Simple in-memory cache for writing images.
    Простой кэш в памяти для картинок написания.
    """
    
    def __init__(self, max_size_mb: int = 100, ttl_seconds: int = 86400):
        """
        Initialize cache.
        
        Args:
            max_size_mb: Maximum cache size in MB
            ttl_seconds: Time to live for cached items in seconds
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.ttl_seconds = ttl_seconds
        self.current_size_bytes = 0
        
        logger.info(f"Initialized WritingImageCache: max_size={max_size_mb}MB, ttl={ttl_seconds}s")
    
    def _generate_cache_key(self, word: str, language: str, style: str = "traditional") -> str:
        """Generate cache key for word, language, and style."""
        key_string = f"{word}:{language}:{style}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_expired(self, item: Dict[str, Any]) -> bool:
        """Check if cache item is expired."""
        expires_at = datetime.fromisoformat(item["expires_at"])
        return datetime.now() > expires_at
    
    def _cleanup_expired(self):
        """Remove expired items from cache."""
        expired_keys = []
        for key, item in self.cache.items():
            if self._is_expired(item):
                expired_keys.append(key)
                self.current_size_bytes -= item["size_bytes"]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache items")
    
    def _ensure_space(self, required_bytes: int):
        """Ensure there's enough space in cache for new item."""
        self._cleanup_expired()
        
        # If still not enough space, remove oldest items
        while (self.current_size_bytes + required_bytes > self.max_size_bytes 
               and self.cache):
            # Find oldest item
            oldest_key = min(
                self.cache.keys(), 
                key=lambda k: self.cache[k]["created_at"]
            )
            
            self.current_size_bytes -= self.cache[oldest_key]["size_bytes"]
            del self.cache[oldest_key]
            logger.debug(f"Removed oldest cache item: {oldest_key}")
    
    def get(self, word: str, language: str, style: str = "traditional") -> Optional[io.BytesIO]:
        """
        Get cached writing image.
        
        Args:
            word: Word
            language: Language code
            style: Writing style
            
        Returns:
            BytesIO with image data or None if not found/expired
        """
        cache_key = self._generate_cache_key(word, language, style)
        
        if cache_key not in self.cache:
            return None
        
        item = self.cache[cache_key]
        
        if self._is_expired(item):
            self.current_size_bytes -= item["size_bytes"]
            del self.cache[cache_key]
            logger.debug(f"Cache item expired and removed: {cache_key}")
            return None
        
        # Update access info
        item["access_count"] += 1
        item["last_accessed"] = datetime.now().isoformat()
        
        # Return copy of image data
        image_buffer = io.BytesIO(item["image_data"])
        image_buffer.seek(0)
        
        logger.debug(f"Cache hit for: {word} ({language}, {style})")
        return image_buffer
    
    def put(
        self, 
        word: str, 
        language: str, 
        image_data: bytes, 
        style: str = "traditional"
    ):
        """
        Store writing image in cache.
        
        Args:
            word: Word
            language: Language code
            image_data: Image binary data
            style: Writing style
        """
        cache_key = self._generate_cache_key(word, language, style)
        size_bytes = len(image_data)
        
        # Ensure there's space
        self._ensure_space(size_bytes)
        
        # Create cache item
        now = datetime.now()
        expires_at = now + timedelta(seconds=self.ttl_seconds)
        
        cache_item = {
            "word": word,
            "language": language,
            "style": style,
            "image_data": image_data,
            "size_bytes": size_bytes,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "access_count": 0,
            "last_accessed": None
        }
        
        self.cache[cache_key] = cache_item
        self.current_size_bytes += size_bytes
        
        logger.debug(f"Cached writing image: {word} ({language}, {style}) - {size_bytes} bytes")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        self._cleanup_expired()
        
        total_items = len(self.cache)
        total_size_mb = self.current_size_bytes / (1024 * 1024)
        
        if total_items > 0:
            avg_size_bytes = self.current_size_bytes / total_items
            total_accesses = sum(item["access_count"] for item in self.cache.values())
            avg_accesses = total_accesses / total_items
        else:
            avg_size_bytes = 0
            total_accesses = 0
            avg_accesses = 0
        
        return {
            "total_items": total_items,
            "total_size_mb": round(total_size_mb, 2),
            "max_size_mb": self.max_size_bytes / (1024 * 1024),
            "usage_percent": round((self.current_size_bytes / self.max_size_bytes) * 100, 1),
            "avg_size_bytes": round(avg_size_bytes),
            "total_accesses": total_accesses,
            "avg_accesses": round(avg_accesses, 1),
            "ttl_seconds": self.ttl_seconds
        }
    
    def clear(self):
        """Clear all cached items."""
        items_count = len(self.cache)
        self.cache.clear()
        self.current_size_bytes = 0
        logger.info(f"Cleared cache: removed {items_count} items")


# Global cache instance
_cache_instance: Optional[WritingImageCache] = None


def get_writing_image_cache() -> WritingImageCache:
    """
    Get global writing image cache instance.
    Получает глобальный экземпляр кэша картинок написания.
    
    Returns:
        WritingImageCache: Cache instance
    """
    global _cache_instance
    if _cache_instance is None:
        # Get settings from config
        max_size_mb = 100
        ttl_seconds = 86400  # 24 hours
        
        try:
            if hasattr(config_holder.cfg, 'writing_image_service'):
                cache_config = config_holder.cfg.writing_image_service.writing_images.cache
                max_size_mb = cache_config.get('max_size_mb', max_size_mb)
                ttl_seconds = cache_config.get('ttl', ttl_seconds)
        except Exception as e:
            logger.warning(f"Could not load cache config, using defaults: {e}")
        
        _cache_instance = WritingImageCache(max_size_mb, ttl_seconds)
    
    return _cache_instance


async def get_cached_writing_image(
    word: str, 
    language: str, 
    style: str = "traditional"
) -> Optional[io.BytesIO]:
    """
    Get writing image from cache.
    Получает картинку написания из кэша.
    
    Args:
        word: Word
        language: Language code
        style: Writing style
        
    Returns:
        BytesIO with image data or None if not cached
    """
    cache = get_writing_image_cache()
    return cache.get(word, language, style)


async def cache_writing_image(
    word: str, 
    language: str, 
    image_data: bytes, 
    style: str = "traditional"
):
    """
    Store writing image in cache.
    Сохраняет картинку написания в кэш.
    
    Args:
        word: Word
        language: Language code
        image_data: Image binary data
        style: Writing style
    """
    cache = get_writing_image_cache()
    cache.put(word, language, image_data, style)


def is_cache_enabled() -> bool:
    """
    Check if caching is enabled in configuration.
    Проверяет, включено ли кэширование в конфигурации.
    
    Returns:
        bool: True if caching is enabled
    """
    try:
        if hasattr(config_holder.cfg, 'writing_image_service'):
            return config_holder.cfg.writing_image_service.writing_images.cache.get('enabled', True)
    except Exception:
        pass
    
    return True  # Default to enabled


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    Получает статистику кэша.
    
    Returns:
        Dict with cache statistics
    """
    if not is_cache_enabled():
        return {"enabled": False}
    
    cache = get_writing_image_cache()
    stats = cache.get_stats()
    stats["enabled"] = True
    return stats


def clear_cache():
    """
    Clear writing image cache.
    Очищает кэш картинок написания.
    """
    cache = get_writing_image_cache()
    cache.clear()


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
