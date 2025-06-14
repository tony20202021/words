"""
Prompt Manager
Менеджер для работы с системой построения промптов.
ОБНОВЛЕНО: Добавлена поддержка пользовательской подсказки hint_writing
"""

import time
import asyncio
from typing import Dict, Any, Optional, List

from app.utils.logger import get_module_logger
from app.ai.core.generation_config import AIGenerationConfig
from app.ai.prompt.prompt_builder import PromptBuilder, PromptConfig, PromptResult

logger = get_module_logger(__name__)


class PromptManager:
    """
    Менеджер для работы с системой построения промптов.
    Отвечает за создание промптов с учетом стилей и пользовательских подсказок.
    ОБНОВЛЕНО: Поддержка пользовательских подсказок hint_writing
    """
    
    def __init__(self, config: AIGenerationConfig):
        """
        Инициализация Prompt Manager.
        
        Args:
            config: Конфигурация AI генерации
        """
        self.config = config
        self.prompt_builder: Optional[PromptBuilder] = None
        self._prompt_initialized = False
        self._prompt_lock = asyncio.Lock()
        
        # Статистика
        self.prompt_count = 0
        self.hint_prompt_count = 0  # НОВОЕ: счетчик промптов с подсказками
        self.total_prompt_time = 0
        self.start_time = time.time()
        
        # НОВОЕ: Конфигурация для обработки подсказок
        self.hint_config = {
            "max_hint_length": 200,
            "hint_integration_methods": ["append", "integrate", "prefix"],
            "default_integration_method": "integrate",
            "hint_weight_in_prompt": 0.3,
            "enable_hint_optimization": True
        }
        
        logger.info("PromptManager initialized with hint support")
        
        # Асинхронная инициализация PromptBuilder
        asyncio.create_task(self._initialize_prompt_builder())
    
    async def _initialize_prompt_builder(self):
        """Инициализирует PromptBuilder"""
        async with self._prompt_lock:
            if self._prompt_initialized:
                return
            
            try:
                logger.info("Initializing PromptBuilder with hint support...")
                start_time = time.time()
                
                # Создаем конфигурацию для PromptBuilder
                prompt_config = PromptConfig(
                    max_prompt_length=400,  # Увеличиваем для поддержки подсказок
                )
                
                # Загружаем конфигурацию подсказок из основного конфига
                self._load_hint_config()
                
                self.prompt_builder = PromptBuilder(prompt_config)
                
                init_time = time.time() - start_time
                self._prompt_initialized = True
                
                logger.info(f"✓ PromptBuilder with hint support initialized successfully in {init_time:.1f}s")
                
            except Exception as e:
                logger.error(f"Failed to initialize PromptBuilder: {e}")
                self._prompt_initialized = False
                self.prompt_builder = None
                raise RuntimeError(f"PromptBuilder initialization failed: {e}")
    
    def _load_hint_config(self):
        """Загружает конфигурацию обработки подсказок"""
        try:
            # Здесь можно загрузить конфигурацию из файлов или переменных окружения
            # Пока используем значения по умолчанию
            logger.debug(f"Loaded hint config: {self.hint_config}")
            
        except Exception as e:
            logger.warning(f"Could not load hint config, using defaults: {e}")
    
    async def ensure_prompt_ready(self):
        """Обеспечивает готовность PromptBuilder"""
        if not self._prompt_initialized:
            await self._initialize_prompt_builder()
        
        if not self.prompt_builder:
            raise RuntimeError("PromptBuilder not available")
    
    async def build_prompt(
        self,
        character: str,
        translation: str,
        hint_writing: Optional[str] = None,  # НОВОЕ: пользовательская подсказка (уже переведенная)
        style: str = "comic",  # НОВОЕ: стиль генерации
        **kwargs
    ) -> PromptResult:
        """
        Строит промпт для AI генерации с учетом пользовательской подсказки.
        ОБНОВЛЕНО: Поддержка пользовательских подсказок
        
        Args:
            character: Китайский иероглиф
            translation: Перевод иероглифа на английском
            user_hint: Пользовательская подсказка (уже переведенная на английский)
            style: Стиль генерации
            **kwargs: Дополнительные параметры
            
        Returns:
            PromptResult: Результат построения промпта с метаданными подсказки
        """
        prompt_start = time.time()
        
        try:
            # Ждем инициализации PromptBuilder
            await self.ensure_prompt_ready()
            
            # Логируем информацию о построении промпта
            hint_info = f", hint: '{hint_writing}'" if hint_writing else ""
            logger.debug(f"Building prompt for character: '{character}', "
                        f"translation: '{translation}', style: '{style}'{hint_info}")
            
            # ОБНОВЛЕНО: Передаем пользовательскую подсказку в PromptBuilder
            prompt_result = await self.prompt_builder.build_prompt(
                character=character,
                translation=translation,
                hint_writing=hint_writing,  # НОВОЕ: передаем подсказку
                style=style,  # НОВОЕ: передаем стиль
                **kwargs
            )
            
            if not prompt_result.success:
                logger.error(f"Prompt building failed: {prompt_result.error_message}")
                return prompt_result
            
            # Добавляем метаданные о подсказке
            if hint_writing:
                prompt_result.hint_metadata = {
                    "hint_writing": hint_writing,
                    "hint_length": len(hint_writing),
                    "integrated": True
                }
                self.hint_prompt_count += 1
            
            # Обновляем статистику
            prompt_time_ms = int((time.time() - prompt_start) * 1000)
            prompt_result.generation_time_ms = prompt_time_ms
            self.prompt_count += 1
            self.total_prompt_time += prompt_time_ms
            
            # Логируем результат
            hint_result_info = f" (with hint_writing: '{hint_writing}')" if hint_writing else ""
            logger.info(f"✓ Built prompt for character: '{character}' "
                       f"(style: {style}, time: {prompt_time_ms}ms{hint_result_info})")
            logger.debug(f"Final prompt: '{prompt_result.main_prompt}'")
            
            return prompt_result
            
        except Exception as e:
            prompt_time_ms = int((time.time() - prompt_start) * 1000)
            logger.error(f"Error building prompt: {e}", exc_info=True)
            
            return PromptResult(
                success=False,
                error_message=str(e),
                generation_time_ms=prompt_time_ms
            )
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Возвращает статус Prompt Manager.
        ОБНОВЛЕНО: Включает статистику использования подсказок
        """
        uptime_seconds = int(time.time() - self.start_time)
        avg_prompt_time = (
            self.total_prompt_time / self.prompt_count 
            if self.prompt_count > 0 else 0
        )
        
        # НОВОЕ: Статистика подсказок
        hint_usage_percentage = (
            (self.hint_prompt_count / self.prompt_count * 100)
            if self.prompt_count > 0 else 0
        )
        
        return {
            "initialized": self._prompt_initialized,
            "prompt_builder_ready": self.prompt_builder is not None,
            "uptime_seconds": uptime_seconds,
            "prompt_count": self.prompt_count,
            "hint_prompt_count": self.hint_prompt_count,  # НОВОЕ
            "hint_usage_percentage": hint_usage_percentage,  # НОВОЕ
            "total_prompt_time_ms": self.total_prompt_time,
            "average_prompt_time_ms": avg_prompt_time,
            
            # НОВОЕ: Возможности
            "capabilities": {
                "user_hints": True,
                "hint_integration": True,
                "style_support": True,
                "prompt_optimization": True,
                "smart_integration": True
            },
            
            # НОВОЕ: Конфигурация подсказок
            "hint_config": self.hint_config
        }
    
    async def get_hint_integration_methods(self) -> List[str]:
        """
        НОВОЕ: Возвращает доступные методы интеграции подсказок.
        
        Returns:
            List[str]: Список методов интеграции
        """
        return self.hint_config["hint_integration_methods"]
    
    async def set_hint_integration_method(self, method: str) -> bool:
        """
        НОВОЕ: Устанавливает метод интеграции подсказок.
        
        Args:
            method: Метод интеграции
            
        Returns:
            bool: True если метод установлен успешно
        """
        if method in self.hint_config["hint_integration_methods"]:
            self.hint_config["default_integration_method"] = method
            logger.info(f"Set hint integration method to: {method}")
            return True
        else:
            logger.warning(f"Invalid hint integration method: {method}")
            return False
    
    async def cleanup(self):
        """Очищает ресурсы Prompt Manager"""
        try:
            logger.info("Cleaning up Prompt Manager...")
            
            self.prompt_builder = None
            self._prompt_initialized = False
            
            logger.info("✓ Prompt Manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during prompt manager cleanup: {e}")
            