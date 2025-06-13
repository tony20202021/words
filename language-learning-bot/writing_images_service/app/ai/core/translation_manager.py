"""
Translation Manager
Менеджер для перевода русских текстов в английские промпты.
"""

import time
import asyncio
from typing import Dict, Any, Optional, Tuple

from app.utils.logger import get_module_logger
from app.ai.core.generation_config import AIGenerationConfig
from app.ai.services.translation_service import TranslationService

logger = get_module_logger(__name__)


class TranslationManager:
    """
    Менеджер для работы с Translation Service.
    Отвечает за перевод русских текстов в английские промпты.
    """
    
    def __init__(self, config: AIGenerationConfig):
        """
        Инициализация Translation Manager.
        
        Args:
            config: Конфигурация AI генерации
        """
        self.config = config
        self.translation_service: Optional[TranslationService] = None
        self._translation_initialized = False
        self._translation_lock = asyncio.Lock()
        
        # Статистика
        self.translation_count = 0
        self.total_translation_time = 0
        self.start_time = time.time()
        
        logger.info("TranslationManager initialized")
        
        # Асинхронная инициализация Translation Service
        if self.config.enable_translation:
            asyncio.create_task(self._initialize_translation_service())
    
    async def _initialize_translation_service(self):
        """Инициализирует Translation Service"""
        async with self._translation_lock:
            if self._translation_initialized:
                return
            
            try:
                logger.info("Initializing Translation Service...")
                start_time = time.time()
                
                self.translation_service = TranslationService()
                
                # Ждем инициализации (может занять время для загрузки модели)
                max_wait_time = 60  # секунд
                wait_start = time.time()
                
                while not self.translation_service.is_ready():
                    if time.time() - wait_start > max_wait_time:
                        raise TimeoutError("Translation service initialization timeout")
                    
                    await asyncio.sleep(1)
                
                init_time = time.time() - start_time
                self._translation_initialized = True
                
                logger.info(f"✓ Translation Service initialized successfully in {init_time:.1f}s")
                
                # Логируем статус
                status = await self.translation_service.get_service_status()
                logger.info(f"Translation Service status: model={status.get('active_model')}, "
                           f"cache_enabled={status.get('cache_stats', {}).get('enabled')}")
                
            except Exception as e:
                logger.error(f"Failed to initialize Translation Service: {e}")
                self._translation_initialized = False
                self.translation_service = None
                
                if not self.config.translation_fallback_to_original:
                    raise RuntimeError(f"Translation Service initialization failed: {e}")
                else:
                    logger.warning("Translation Service disabled, will use original Russian text")
    
    async def ensure_translation_ready(self):
        """Обеспечивает готовность Translation Service"""
        if not self.config.enable_translation:
            return
        
        if not self._translation_initialized:
            await self._initialize_translation_service()
        
        if not self.translation_service or not self.translation_service.is_ready():
            if not self.config.translation_fallback_to_original:
                raise RuntimeError("Translation Service not available")
    
    async def translate_to_english(
        self,
        character: str,
        russian_text: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Переводит русский текст в английский для AI промптов.
        
        Args:
            character: Китайский иероглиф
            russian_text: Русский перевод
            
        Returns:
            Tuple[str, Dict]: (английский_перевод, метаданные_перевода)
        """
        translation_start = time.time()
        
        # Если Translation Service отключен, возвращаем оригинальный текст
        if not self.config.enable_translation:
            return russian_text, {
                'source': 'disabled',
                'time_ms': 0,
                'model_used': 'none'
            }
        
        # Если русский текст пустой, используем только иероглиф
        if not russian_text.strip():
            return character, {
                'source': 'character_only',
                'time_ms': 0,
                'model_used': 'none'
            }
        
        try:
            # Ждем инициализации Translation Service
            if not self._translation_initialized:
                await self._initialize_translation_service()
            
            # Если сервис все еще недоступен, используем fallback
            if not self.translation_service or not self.translation_service.is_ready():
                if self.config.translation_fallback_to_original:
                    logger.warning("Translation Service not ready, using original Russian text")
                    return russian_text, {
                        'source': 'service_unavailable_fallback',
                        'time_ms': int((time.time() - translation_start) * 1000),
                        'model_used': 'none'
                    }
                else:
                    raise RuntimeError("Translation Service not available")
            
            # Выполняем перевод
            translation_result = await self.translation_service.translate(
                character=character,
                russian_text=russian_text
            )
            
            translation_time_ms = int((time.time() - translation_start) * 1000)
            
            if translation_result.success:
                # Обновляем статистику
                self.translation_count += 1
                self.total_translation_time += translation_time_ms
                
                # Подготавливаем метаданные
                metadata = {
                    'source': 'cache' if translation_result.cache_hit else 'ai_model',
                    'time_ms': translation_time_ms,
                    'model_used': translation_result.model_used,
                    'confidence_score': translation_result.confidence_score,
                    'cache_hit': translation_result.cache_hit
                }
                
                return translation_result.translated_text, metadata
                
            else:
                # Перевод не удался
                logger.warning(f"Translation failed: {translation_result.error_message}")
                
                if self.config.translation_fallback_to_original:
                    return russian_text, {
                        'source': 'translation_failed_fallback',
                        'time_ms': translation_time_ms,
                        'model_used': 'none',
                        'error': translation_result.error_message
                    }
                else:
                    raise RuntimeError(f"Translation failed: {translation_result.error_message}")
                    
        except Exception as e:
            translation_time_ms = int((time.time() - translation_start) * 1000)
            logger.error(f"Error in translation: {e}")
            
            if self.config.translation_fallback_to_original:
                return russian_text, {
                    'source': 'error_fallback',
                    'time_ms': translation_time_ms,
                    'model_used': 'none',
                    'error': str(e)
                }
            else:
                raise RuntimeError(f"Translation error: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Возвращает статус Translation Manager"""
        uptime_seconds = int(time.time() - self.start_time)
        avg_translation_time = (
            self.total_translation_time / self.translation_count 
            if self.translation_count > 0 else 0
        )
        
        return {
            "enabled": self.config.enable_translation,
            "initialized": self._translation_initialized,
            "service_ready": self.translation_service.is_ready() if self.translation_service else False,
            "uptime_seconds": uptime_seconds,
            "translation_count": self.translation_count,
            "total_translation_time_ms": self.total_translation_time,
            "average_translation_time_ms": avg_translation_time
        }
    
    async def get_detailed_status(self) -> Dict[str, Any]:
        """Возвращает детальный статус Translation Service"""
        if not self.translation_service:
            return {
                "enabled": self.config.enable_translation,
                "initialized": False,
                "error": "Translation service not initialized"
            }
        
        try:
            return await self.translation_service.get_service_status()
        except Exception as e:
            logger.error(f"Error getting translation service status: {e}")
            return {"error": str(e)}
    
    async def switch_model(self, model_name: str) -> bool:
        """Переключает модель перевода"""
        if not self.translation_service:
            logger.error("Translation service not available")
            return False
        
        try:
            success = await self.translation_service.switch_model(model_name)
            if success:
                logger.info(f"✓ Switched translation model to: {model_name}")
            else:
                logger.error(f"✗ Failed to switch translation model to: {model_name}")
            return success
        except Exception as e:
            logger.error(f"Error switching translation model: {e}")
            return False
    
    async def cleanup(self):
        """Очищает ресурсы Translation Manager"""
        try:
            logger.info("Cleaning up Translation Manager...")
            
            if self.translation_service:
                await self.translation_service.cleanup()
                self.translation_service = None
            
            self._translation_initialized = False
            
            logger.info("✓ Translation Manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during translation manager cleanup: {e}")
            