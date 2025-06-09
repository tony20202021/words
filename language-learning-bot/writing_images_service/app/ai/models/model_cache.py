"""
Model cache manager for AI models.
Менеджер кэша для AI моделей.
"""

import logging
import time
import weakref
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from collections import OrderedDict

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Запись в кэше модели"""
    model: Any
    model_name: str
    load_time: float
    last_access_time: float
    access_count: int
    memory_usage_mb: float


class ModelCache:
    """
    Кэш моделей с автоматическим управлением памятью.
    """
    
    def __init__(self, max_cache_size: int = 10, ttl_seconds: int = 3600):
        """
        Инициализация кэша моделей.
        
        Args:
            max_cache_size: Максимальное количество моделей в кэше
            ttl_seconds: Время жизни модели в кэше (секунды)
        """
        self.max_cache_size = max_cache_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._access_times: Dict[str, float] = {}
        logger.info(f"ModelCache initialized with max_size={max_cache_size}, ttl={ttl_seconds}s")
    
    def put(self, key: str, model: Any, model_name: str, memory_usage_mb: float = 0.0):
        """
        Добавляет модель в кэш.
        
        Args:
            key: Ключ для модели
            model: Модель для кэширования
            model_name: Имя модели
            memory_usage_mb: Использование памяти в MB
        """
        current_time = time.time()
        
        # Если модель уже в кэше, обновляем её
        if key in self.cache:
            entry = self.cache[key]
            entry.model = model
            entry.last_access_time = current_time
            entry.access_count += 1
            # Перемещаем в конец (LRU)
            self.cache.move_to_end(key)
            logger.debug(f"Updated model in cache: {key}")
            return
        
        # Создаем новую запись
        entry = CacheEntry(
            model=model,
            model_name=model_name,
            load_time=current_time,
            last_access_time=current_time,
            access_count=1,
            memory_usage_mb=memory_usage_mb
        )
        
        # Добавляем в кэш
        self.cache[key] = entry
        self._access_times[key] = current_time
        
        # Проверяем лимиты кэша
        self._enforce_cache_limits()
        
        logger.info(f"Added model to cache: {key} ({model_name})")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Получает модель из кэша.
        
        Args:
            key: Ключ модели
            
        Returns:
            Модель или None если не найдена
        """
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        current_time = time.time()
        
        # Проверяем TTL
        if current_time - entry.load_time > self.ttl_seconds:
            logger.debug(f"Model expired in cache: {key}")
            self.remove(key)
            return None
        
        # Обновляем статистику доступа
        entry.last_access_time = current_time
        entry.access_count += 1
        self._access_times[key] = current_time
        
        # Перемещаем в конец (LRU)
        self.cache.move_to_end(key)
        
        logger.debug(f"Cache hit for model: {key}")
        return entry.model
    
    def remove(self, key: str) -> bool:
        """
        Удаляет модель из кэша.
        
        Args:
            key: Ключ модели
            
        Returns:
            True если модель была удалена
        """
        if key in self.cache:
            del self.cache[key]
            if key in self._access_times:
                del self._access_times[key]
            logger.info(f"Removed model from cache: {key}")
            return True
        return False
    
    def clear(self):
        """Очищает весь кэш."""
        self.cache.clear()
        self._access_times.clear()
        logger.info("Cache cleared")
    
    def _enforce_cache_limits(self):
        """Применяет ограничения кэша (размер и TTL)."""
        current_time = time.time()
        
        # Удаляем устаревшие модели
        expired_keys = []
        for key, entry in self.cache.items():
            if current_time - entry.load_time > self.ttl_seconds:
                expired_keys.append(key)
        
        for key in expired_keys:
            self.remove(key)
        
        # Удаляем лишние модели (LRU)
        while len(self.cache) > self.max_cache_size:
            # Удаляем самую старую модель (первую в OrderedDict)
            oldest_key = next(iter(self.cache))
            logger.info(f"Evicting model from cache (size limit): {oldest_key}")
            self.remove(oldest_key)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику кэша.
        
        Returns:
            Статистика использования кэша
        """
        current_time = time.time()
        total_memory_mb = sum(entry.memory_usage_mb for entry in self.cache.values())
        total_access_count = sum(entry.access_count for entry in self.cache.values())
        
        # Вычисляем hit rate (приблизительно)
        cache_entries = list(self.cache.values())
        avg_access_count = total_access_count / len(cache_entries) if cache_entries else 0
        
        stats = {
            "cache_size": len(self.cache),
            "max_cache_size": self.max_cache_size,
            "total_memory_mb": round(total_memory_mb, 2),
            "avg_access_count": round(avg_access_count, 2),
            "models_in_cache": list(self.cache.keys()),
            "cache_utilization": round(len(self.cache) / self.max_cache_size * 100, 1),
            "ttl_seconds": self.ttl_seconds
        }
        
        # Детали по каждой модели
        model_details = {}
        for key, entry in self.cache.items():
            age_seconds = current_time - entry.load_time
            model_details[key] = {
                "model_name": entry.model_name,
                "age_seconds": round(age_seconds, 1),
                "access_count": entry.access_count,
                "memory_usage_mb": entry.memory_usage_mb,
                "last_access_ago_seconds": round(current_time - entry.last_access_time, 1)
            }
        
        stats["model_details"] = model_details
        return stats
    
    def cleanup_expired(self):
        """Принудительно очищает устаревшие модели."""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if current_time - entry.load_time > self.ttl_seconds:
                expired_keys.append(key)
        
        for key in expired_keys:
            self.remove(key)
        
        logger.info(f"Cleaned up {len(expired_keys)} expired models")
        return len(expired_keys)
    
    def get_model_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Возвращает информацию о модели в кэше.
        
        Args:
            key: Ключ модели
            
        Returns:
            Информация о модели или None
        """
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        current_time = time.time()
        
        return {
            "model_name": entry.model_name,
            "load_time": entry.load_time,
            "age_seconds": round(current_time - entry.load_time, 1),
            "last_access_time": entry.last_access_time,
            "access_count": entry.access_count,
            "memory_usage_mb": entry.memory_usage_mb,
            "expires_in_seconds": round(self.ttl_seconds - (current_time - entry.load_time), 1)
        }
    
    def is_cached(self, key: str) -> bool:
        """
        Проверяет находится ли модель в кэше и не устарела ли.
        
        Args:
            key: Ключ модели
            
        Returns:
            True если модель в кэше и актуальна
        """
        if key not in self.cache:
            return False
        
        entry = self.cache[key]
        current_time = time.time()
        
        # Проверяем TTL
        if current_time - entry.load_time > self.ttl_seconds:
            return False
        
        return True
    
    def update_memory_usage(self, key: str, memory_usage_mb: float):
        """
        Обновляет информацию об использовании памяти для модели.
        
        Args:
            key: Ключ модели
            memory_usage_mb: Использование памяти в MB
        """
        if key in self.cache:
            self.cache[key].memory_usage_mb = memory_usage_mb
            logger.debug(f"Updated memory usage for {key}: {memory_usage_mb}MB")
    
    def get_least_recently_used(self) -> Optional[str]:
        """Возвращает ключ наименее недавно использованной модели."""
        if not self.cache:
            return None
        
        # В OrderedDict первый элемент - самый старый
        return next(iter(self.cache))
    
    def get_most_recently_used(self) -> Optional[str]:
        """Возвращает ключ наиболее недавно использованной модели."""
        if not self.cache:
            return None
        
        # В OrderedDict последний элемент - самый новый
        return next(reversed(self.cache))
    