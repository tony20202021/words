"""
Translation Service - основной сервис для перевода русских значений в английские промпты.
Включает автоматический выбор модели, кэширование, fallback стратегии.
ОБНОВЛЕНО: Поддержка новой структуры конфигурации memory_profiles
"""

import time
import asyncio
import json
import hashlib
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import torch
import traceback

from app.ai.models.translation_model import TranslationModel, TranslationResult, ModelInfo
from app.utils.logger import get_module_logger
from app.utils import config_holder

logger = get_module_logger(__name__)


@dataclass
class TranslationServiceConfig:
    """Конфигурация Translation Service"""
    enabled: bool = True
    active_model: str = "qwen2_7b"
    auto_model_selection: bool = True
    
    # Кэширование
    cache_enabled: bool = True
    max_cache_size: int = 10000
    cache_ttl_hours: int = 168  # 7 дней
    persistent_cache: bool = True
    cache_file: str = "./cache/translation_cache.json"
    
    # Fallback
    fallback_enabled: bool = True
    fallback_strategies: List[str] = None
    simple_dictionary: Dict[str, str] = None
    
    # Мониторинг
    monitoring_enabled: bool = True
    log_translations: bool = True
    
    def __post_init__(self):
        if self.fallback_strategies is None:
            self.fallback_strategies = ["use_cache", "use_simple_dict", "return_original", "use_character_only"]
        
        if self.simple_dictionary is None:
            self.simple_dictionary = {
                "учить": "learn",
                "изучать": "study",
                "писать": "write",
                "читать": "read",
                "говорить": "speak",
                "слушать": "listen",
                "смотреть": "look, see",
                "дом": "house",
                "школа": "school",
                "работа": "work"
            }


@dataclass
class CacheEntry:
    """Запись в кэше переводов"""
    character: str
    russian_text: str
    english_text: str
    model_used: str
    timestamp: float
    confidence_score: float
    access_count: int = 0
    last_access: float = 0.0


class TranslationCache:
    """Кэш переводов с TTL и персистентностью"""
    
    def __init__(self, config: TranslationServiceConfig):
        self.config = config
        self.cache: Dict[str, CacheEntry] = {}
        self.cache_file = Path(config.cache_file)
        self._cache_lock = asyncio.Lock()
        
        # Создаем директорию если нужно
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Загружаем существующий кэш
        if config.persistent_cache:
            asyncio.create_task(self._load_cache())
    
    def _generate_cache_key(self, character: str, russian_text: str) -> str:
        """Генерирует ключ для кэша"""
        content = f"{character}:{russian_text}".lower().strip()
        return hashlib.md5(content.encode()).hexdigest()
    
    async def get(self, character: str, russian_text: str) -> Optional[TranslationResult]:
        """Получает перевод из кэша"""
        if not self.config.cache_enabled:
            return None
        
        async with self._cache_lock:
            cache_key = self._generate_cache_key(character, russian_text)
            
            if cache_key not in self.cache:
                return None
            
            entry = self.cache[cache_key]
            
            # Проверяем TTL
            current_time = time.time()
            age_hours = (current_time - entry.timestamp) / 3600
            
            if age_hours > self.config.cache_ttl_hours:
                # Запись устарела
                del self.cache[cache_key]
                logger.debug(f"Cache entry expired for: {character}")
                return None
            
            # Обновляем статистику доступа
            entry.access_count += 1
            entry.last_access = current_time
            
            logger.debug(f"Cache hit for: {character} -> {entry.english_text}")
            
            return TranslationResult(
                success=True,
                translated_text=entry.english_text,
                original_text=russian_text,
                character=character,
                translation_time_ms=0,  # Кэш мгновенный
                model_used=entry.model_used,
                cache_hit=True,
                confidence_score=entry.confidence_score
            )
    
    async def put(self, character: str, russian_text: str, translation_result: TranslationResult):
        """Сохраняет перевод в кэш"""
        if not self.config.cache_enabled or not translation_result.success:
            return
        
        async with self._cache_lock:
            cache_key = self._generate_cache_key(character, russian_text)
            
            # Проверяем размер кэша
            if len(self.cache) >= self.config.max_cache_size:
                # Удаляем самые старые записи
                await self._cleanup_old_entries()
            
            # Создаем запись
            entry = CacheEntry(
                character=character,
                russian_text=russian_text,
                english_text=translation_result.translated_text,
                model_used=translation_result.model_used,
                timestamp=time.time(),
                confidence_score=translation_result.confidence_score,
                access_count=1,
                last_access=time.time()
            )
            
            self.cache[cache_key] = entry
            
            logger.debug(f"Cached translation: {character} -> {entry.english_text}")
            
            # Сохраняем в файл если нужно
            if self.config.persistent_cache:
                asyncio.create_task(self._save_cache())
    
    async def _cleanup_old_entries(self):
        """Удаляет старые записи из кэша"""
        if len(self.cache) < self.config.max_cache_size:
            return
        
        # Сортируем по времени последнего доступа
        sorted_entries = sorted(
            self.cache.items(),
            key=lambda x: x[1].last_access
        )
        
        # Удаляем 20% самых старых записей
        entries_to_remove = int(len(sorted_entries) * 0.2)
        
        for cache_key, _ in sorted_entries[:entries_to_remove]:
            del self.cache[cache_key]
        
        logger.debug(f"Cleaned up {entries_to_remove} old cache entries")
    
    async def _load_cache(self):
        """Загружает кэш из файла"""
        try:
            if not self.cache_file.exists():
                logger.debug("No existing cache file found")
                return
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Восстанавливаем записи
            for cache_key, entry_data in cache_data.items():
                entry = CacheEntry(**entry_data)
                
                # Проверяем TTL при загрузке
                age_hours = (time.time() - entry.timestamp) / 3600
                if age_hours <= self.config.cache_ttl_hours:
                    self.cache[cache_key] = entry
            
            logger.info(f"Loaded {len(self.cache)} translations from cache file")
            
        except Exception as e:
            logger.warning(f"Could not load cache file: {e}")
    
    async def _save_cache(self):
        """Сохраняет кэш в файл"""
        try:
            cache_data = {}
            for cache_key, entry in self.cache.items():
                cache_data[cache_key] = asdict(entry)
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Saved {len(self.cache)} translations to cache file")
            
        except Exception as e:
            logger.warning(f"Could not save cache file: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша"""
        if not self.cache:
            return {
                "enabled": self.config.cache_enabled,
                "entries": 0,
                "hit_rate": 0.0,
                "total_accesses": 0
            }
        
        total_accesses = sum(entry.access_count for entry in self.cache.values())
        cache_hits = len([entry for entry in self.cache.values() if entry.access_count > 1])
        hit_rate = cache_hits / len(self.cache) if self.cache else 0.0
        
        return {
            "enabled": self.config.cache_enabled,
            "entries": len(self.cache),
            "max_size": self.config.max_cache_size,
            "hit_rate": hit_rate,
            "total_accesses": total_accesses,
            "cache_file": str(self.cache_file)
        }


class TranslationService:
    """
    Основной сервис перевода с автоматическим выбором модели, кэшированием и fallback стратегиями.
    ОБНОВЛЕНО: Поддержка новой структуры конфигурации memory_profiles
    """
    
    def __init__(self):
        """Инициализация Translation Service"""
        # Модели
        self.available_models: Dict[str, Dict[str, Any]] = {}
        self.loaded_models: Dict[str, TranslationModel] = {}
        self.active_model: Optional[TranslationModel] = None
        self._model_loading_lock = asyncio.Lock()
        
        # Статистика
        self.translation_count = 0
        self.cache_hits = 0
        self.fallback_usage = 0
        self.start_time = time.time()
        
        self.config = self._load_config()
        self.cache = TranslationCache(self.config)
        
        logger.info("TranslationService initialized")
        
        # Асинхронная инициализация
        asyncio.create_task(self._initialize_service())
    
    def _load_config(self) -> TranslationServiceConfig:
        """Загружает конфигурацию из Hydra config"""
        config = TranslationServiceConfig()
        
        try:
            if hasattr(config_holder, 'cfg') and hasattr(config_holder.cfg, 'translation'):
                translation_cfg = config_holder.cfg.translation
                
                config.enabled = translation_cfg.get('enabled', True)
                config.active_model = translation_cfg.get('active_model', 'qwen2_7b')
                
                # Автоматический выбор модели
                auto_cfg = translation_cfg.get('auto_model_selection', {})
                config.auto_model_selection = auto_cfg.get('enabled', True)
                
                # Кэширование
                cache_cfg = translation_cfg.get('caching', {})
                config.cache_enabled = cache_cfg.get('enabled', True)
                config.max_cache_size = cache_cfg.get('max_cache_size', 10000)
                config.cache_ttl_hours = cache_cfg.get('cache_ttl_hours', 168)
                config.persistent_cache = cache_cfg.get('persistent_cache', True)
                config.cache_file = cache_cfg.get('cache_file', './cache/translation_cache.json')
                
                # Fallback
                fallback_cfg = translation_cfg.get('fallback', {})
                config.fallback_enabled = fallback_cfg.get('enabled', True)
                if 'strategies' in fallback_cfg:
                    config.fallback_strategies = fallback_cfg['strategies']
                if 'simple_dictionary' in fallback_cfg:
                    config.simple_dictionary = fallback_cfg['simple_dictionary']
                
                # Мониторинг
                monitoring_cfg = translation_cfg.get('monitoring', {})
                config.monitoring_enabled = monitoring_cfg.get('enabled', True)
                config.log_translations = monitoring_cfg.get('log_translations', True)
                
                # Загружаем доступные модели
                if 'candidate_models' in translation_cfg:
                    self.available_models = dict(translation_cfg['candidate_models'])
                
                logger.info(f"Loaded translation config: active_model={config.active_model}, "
                           f"cache_enabled={config.cache_enabled}, ")
                if hasattr(self, 'available_models'):
                    logger.info(f"available_models={len(self.available_models)}")
                
        except Exception as e:
            logger.warning(f"Could not load full translation config, using defaults: {e}")
            logger.warning(traceback.format_exc())
        
        return config
    
    async def _initialize_service(self):
        """Асинхронная инициализация сервиса"""
        try:
            # Автоматический выбор модели если включен
            if self.config.auto_model_selection:
                optimal_model = await self._select_optimal_model()
                if optimal_model:
                    self.config.active_model = optimal_model
                    logger.info(f"Auto-selected model: {optimal_model}")
            
            # Предзагружаем активную модель
            if self.config.enabled:
                await self._ensure_active_model_loaded()
                
        except Exception as e:
            logger.error(f"Error initializing translation service: {e}")
    
    async def _select_optimal_model(self) -> Optional[str]:
        """
        Автоматически выбирает оптимальную модель на основе доступной GPU памяти.
        ОБНОВЛЕНО: Поддержка новой структуры memory_profiles
        """
        try:
            if not torch.cuda.is_available():
                logger.warning("CUDA not available, using lightweight model")
                return "opus_zh_en"
            
            # Получаем информацию о GPU памяти
            total_memory_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
            allocated_memory_gb = torch.cuda.memory_allocated() / 1024**3
            free_memory_gb = total_memory_gb - allocated_memory_gb
            
            logger.info(f"GPU Memory: {free_memory_gb:.1f}GB free / {total_memory_gb:.1f}GB total")
            
            # ОБНОВЛЕНО: Загружаем memory_profiles из конфигурации
            memory_profiles = {}
            if hasattr(config_holder, 'cfg') and hasattr(config_holder.cfg, 'translation'):
                auto_cfg = config_holder.cfg.translation.get('auto_model_selection', {})
                memory_profiles = auto_cfg.get('memory_profiles', {})
            
            logger.info(f"Memory profiles: {memory_profiles}")
            
            # Определяем профиль памяти и выбираем модель
            selected_profile = None
            selected_models = []
            
            # Проверяем профили в порядке убывания требований к памяти
            for profile_name in ['high_memory', 'medium_memory', 'low_memory']:
                if profile_name in memory_profiles:
                    profile = memory_profiles[profile_name]
                    threshold_gb = profile.get('threshold_gb', 0)
                    
                    if free_memory_gb >= threshold_gb:
                        selected_profile = profile_name
                        selected_models = profile.get('preferred_models', [])
                        logger.info(f"{profile_name.title()} memory mode: preferring {selected_models}")
                        break
            
            logger.info(f"selected_models: {selected_models}")
            logger.info(f"self.available_models: {self.available_models.keys()}")

            # Ищем первую доступную модель из предпочтительных
            if selected_models:
                for model_name in selected_models:
                    if model_name in self.available_models:
                        logger.info(f"✓ Selected model: {model_name} (profile: {selected_profile})")
                        return model_name
                        
                # Если никто из предпочтительных не найден, логируем предупреждение
                logger.warning(f"None of preferred models {selected_models} found in available models")
            
            # Fallback: первая доступная модель
            if self.available_models:
                fallback_model = next(iter(self.available_models.keys()))
                logger.warning(f"Using fallback model: {fallback_model}")
                return fallback_model
            
            logger.error("No available models found for auto-selection")
            return None
            
        except Exception as e:
            logger.error(f"Error selecting optimal model: {e}")
            return None
    
    async def _ensure_active_model_loaded(self):
        """Обеспечивает загрузку активной модели"""
        async with self._model_loading_lock:
            if self.active_model and self.active_model.is_loaded():
                return
            
            try:
                model_name = self.config.active_model
                
                if model_name not in self.available_models:
                    raise ValueError(f"Model {model_name} not found in available models: {list(self.available_models.keys())}")
                
                logger.info(f"Loading active translation model: {model_name}")
                
                # Создаем модель если еще не создана
                if model_name not in self.loaded_models:
                    model_config = self.available_models[model_name]
                    self.loaded_models[model_name] = TranslationModel(model_config)
                
                # Загружаем модель
                model = self.loaded_models[model_name]
                success = await model.load_model()
                
                if not success:
                    raise RuntimeError(f"Failed to load model {model_name}")
                
                self.active_model = model
                logger.info(f"✓ Active translation model loaded: {model_name}")
                
            except Exception as e:
                logger.error(f"Failed to load active translation model: {e}")
                logger.error(traceback.format_exc())
                self.active_model = None
                raise
    
    async def translate(
        self,
        character: str,
        russian_text: str,
        **kwargs
    ) -> TranslationResult:
        """
        Основной метод перевода с кэшированием и fallback стратегиями.
        
        Args:
            character: Китайский иероглиф
            russian_text: Русское значение
            **kwargs: Дополнительные параметры
            
        Returns:
            TranslationResult: Результат перевода
        """
        if not self.config.enabled:
            return TranslationResult(
                success=False,
                error_message="Translation service is disabled"
            )
        
        start_time = time.time()
        
        try:
            # 1. Проверяем кэш
            cached_result = await self.cache.get(character, russian_text)
            if cached_result:
                self.cache_hits += 1
                if self.config.log_translations:
                    logger.debug(f"Cache hit: {character} ({russian_text}) -> {cached_result.translated_text}")
                return cached_result
            
            # 2. Пытаемся перевести с помощью AI модели
            try:
                await self._ensure_active_model_loaded()
                
                if self.active_model:
                    result = await self.active_model.translate(character, russian_text, **kwargs)
                    
                    if result.success:
                        # Сохраняем в кэш
                        await self.cache.put(character, russian_text, result)
                        
                        self.translation_count += 1
                        
                        if self.config.log_translations:
                            logger.info(f"AI translation: {character} ({russian_text}) -> {result.translated_text} "
                                       f"({result.translation_time_ms}ms)")
                        
                        return result
                    else:
                        logger.warning(f"AI translation failed: {result.error_message}")
                        
            except Exception as e:
                logger.error(f"AI translation error: {e}")
            
            # 3. Fallback стратегии
            if self.config.fallback_enabled:
                fallback_result = await self._apply_fallback_strategies(character, russian_text)
                
                if fallback_result.success:
                    self.fallback_usage += 1
                    
                    if self.config.log_translations:
                        logger.info(f"Fallback translation: {character} ({russian_text}) -> {fallback_result.translated_text}")
                    
                    return fallback_result
            
            # 4. Полная неудача
            translation_time_ms = int((time.time() - start_time) * 1000)
            
            return TranslationResult(
                success=False,
                original_text=russian_text,
                character=character,
                translation_time_ms=translation_time_ms,
                error_message="All translation strategies failed"
            )
            
        except Exception as e:
            translation_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Translation service error: {e}")
            
            return TranslationResult(
                success=False,
                original_text=russian_text,
                character=character,
                translation_time_ms=translation_time_ms,
                error_message=str(e)
            )
    
    async def _apply_fallback_strategies(self, character: str, russian_text: str) -> TranslationResult:
        """Применяет fallback стратегии"""
        
        for strategy in self.config.fallback_strategies:
            try:
                if strategy == "use_cache":
                    # Уже проверили кэш выше, пропускаем
                    continue
                    
                elif strategy == "use_simple_dict":
                    # Простой словарь
                    russian_lower = russian_text.lower().strip()
                    if russian_lower in self.config.simple_dictionary:
                        english_text = self.config.simple_dictionary[russian_lower]
                        
                        return TranslationResult(
                            success=True,
                            translated_text=english_text,
                            original_text=russian_text,
                            character=character,
                            translation_time_ms=1,
                            model_used="simple_dictionary",
                            confidence_score=0.6
                        )
                
                elif strategy == "return_original":
                    # Возвращаем оригинальный русский текст
                    return TranslationResult(
                        success=True,
                        translated_text=russian_text,
                        original_text=russian_text,
                        character=character,
                        translation_time_ms=1,
                        model_used="fallback_original",
                        confidence_score=0.3
                    )
                
                elif strategy == "use_character_only":
                    # Используем только иероглиф
                    return TranslationResult(
                        success=True,
                        translated_text=character,
                        original_text=russian_text,
                        character=character,
                        translation_time_ms=1,
                        model_used="fallback_character",
                        confidence_score=0.2
                    )
                    
            except Exception as e:
                logger.warning(f"Fallback strategy '{strategy}' failed: {e}")
                continue
        
        # Все fallback стратегии не сработали
        return TranslationResult(
            success=False,
            original_text=russian_text,
            character=character,
            error_message="All fallback strategies failed"
        )
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Возвращает статус Translation Service"""
        uptime_seconds = int(time.time() - self.start_time)
        
        status = {
            "enabled": self.config.enabled,
            "active_model": self.config.active_model,
            "model_loaded": self.active_model.is_loaded() if self.active_model else False,
            "uptime_seconds": uptime_seconds,
            "statistics": {
                "total_translations": self.translation_count,
                "cache_hits": self.cache_hits,
                "fallback_usage": self.fallback_usage,
                "cache_hit_rate": self.cache_hits / max(1, self.translation_count + self.cache_hits)
            },
            "cache_stats": self.cache.get_cache_stats(),
            "available_models": list(self.available_models.keys()),
            "loaded_models": list(self.loaded_models.keys())
        }
        
        # Добавляем статистику активной модели
        if self.active_model:
            status["active_model_stats"] = self.active_model.get_translation_stats()
            status["active_model_info"] = asdict(self.active_model.get_model_info())
        
        return status
    
    async def switch_model(self, model_name: str) -> bool:
        """Переключается на другую модель"""
        async with self._model_loading_lock:
            try:
                if model_name not in self.available_models:
                    logger.error(f"Model {model_name} not available")
                    return False
                
                logger.info(f"Switching to translation model: {model_name}")
                
                # Выгружаем текущую модель если нужно
                if self.active_model and self.active_model.model_id != model_name:
                    await self.active_model.unload_model()
                
                # Создаем новую модель если нужно
                if model_name not in self.loaded_models:
                    model_config = self.available_models[model_name]
                    model_config['model_name'] = model_name
                    
                    self.loaded_models[model_name] = TranslationModel(model_config)
                
                # Загружаем и активируем
                model = self.loaded_models[model_name]
                success = await model.load_model()
                
                if success:
                    self.active_model = model
                    self.config.active_model = model_name
                    logger.info(f"✓ Switched to translation model: {model_name}")
                    return True
                else:
                    logger.error(f"Failed to load model: {model_name}")
                    return False
                    
            except Exception as e:
                logger.error(f"Error switching translation model: {e}")
                return False
    
    async def cleanup(self):
        """Очищает ресурсы сервиса"""
        try:
            logger.info("Cleaning up Translation Service...")
            
            # Сохраняем кэш
            if self.config.persistent_cache:
                await self.cache._save_cache()
            
            # Выгружаем все модели
            for model in self.loaded_models.values():
                await model.unload_model()
            
            self.loaded_models.clear()
            self.active_model = None
            
            logger.info("✓ Translation Service cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during translation service cleanup: {e}")
    
    def is_ready(self) -> bool:
        """Проверяет готовность сервиса"""
        return (
            self.config.enabled and 
            self.active_model is not None and 
            self.active_model.is_loaded()
        )
    