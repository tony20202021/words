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
        user_hint: Optional[str] = None,  # НОВОЕ: пользовательская подсказка (уже переведенная)
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
            hint_info = f", hint: '{user_hint}'" if user_hint else ""
            logger.debug(f"Building prompt for character: '{character}', "
                        f"translation: '{translation}', style: '{style}'{hint_info}")
            
            # ОБНОВЛЕНО: Передаем пользовательскую подсказку в PromptBuilder
            prompt_result = await self.prompt_builder.build_prompt(
                character=character,
                translation=translation,
                # user_hint=user_hint,  # НОВОЕ: передаем подсказку
                style=style,  # НОВОЕ: передаем стиль
                **kwargs
            )
            
            if not prompt_result.success:
                logger.error(f"Prompt building failed: {prompt_result.error_message}")
                return prompt_result
            
            # Обработка и оптимизация промпта с подсказкой
            final_prompt = await self._process_prompt_with_hint(
                base_prompt=prompt_result.main_prompt,
                user_hint=user_hint,
                style=style,
                character=character
            )
            
            # Обновляем результат с финальным промптом
            prompt_result.main_prompt = final_prompt
            
            # Добавляем метаданные о подсказке
            if user_hint:
                prompt_result.hint_metadata = {
                    "user_hint": user_hint,
                    "integration_method": self.hint_config["default_integration_method"],
                    "hint_weight": self.hint_config["hint_weight_in_prompt"],
                    "hint_length": len(user_hint),
                    "integrated": True
                }
                self.hint_prompt_count += 1
            
            # Обновляем статистику
            prompt_time_ms = int((time.time() - prompt_start) * 1000)
            prompt_result.generation_time_ms = prompt_time_ms
            self.prompt_count += 1
            self.total_prompt_time += prompt_time_ms
            
            # Логируем результат
            hint_result_info = f" (with hint: '{user_hint}')" if user_hint else ""
            logger.info(f"✓ Built prompt for character: '{character}' "
                       f"(style: {style}, time: {prompt_time_ms}ms{hint_result_info})")
            logger.debug(f"Final prompt: '{final_prompt[:100]}...'")
            
            return prompt_result
            
        except Exception as e:
            prompt_time_ms = int((time.time() - prompt_start) * 1000)
            logger.error(f"Error building prompt: {e}", exc_info=True)
            
            return PromptResult(
                success=False,
                error_message=str(e),
                generation_time_ms=prompt_time_ms
            )
    
    async def _process_prompt_with_hint(
        self,
        base_prompt: str,
        user_hint: Optional[str],
        style: str,
        character: str
    ) -> str:
        """
        НОВОЕ: Обрабатывает и интегрирует пользовательскую подсказку в промпт.
        
        Args:
            base_prompt: Базовый промпт
            user_hint: Пользовательская подсказка (переведенная)
            style: Стиль генерации
            character: Иероглиф
            
        Returns:
            str: Финальный промпт с интегрированной подсказкой
        """
        if not user_hint or not user_hint.strip():
            return base_prompt
        
        try:
            integration_method = self.hint_config["default_integration_method"]
            
            if integration_method == "append":
                # Простое добавление в конец
                final_prompt = f"{base_prompt}, {user_hint}"
                
            elif integration_method == "prefix":
                # Добавление в начало
                final_prompt = f"{user_hint}, {base_prompt}"
                
            elif integration_method == "integrate":
                # Интеллектуальная интеграция в подходящее место
                final_prompt = self._smart_integrate_hint(base_prompt, user_hint, style)
                
            else:
                # Fallback to append
                final_prompt = f"{base_prompt}, {user_hint}"
            
            # Оптимизируем длину финального промпта
            if self.hint_config["enable_hint_optimization"]:
                final_prompt = self._optimize_prompt_with_hint(final_prompt)
            
            return final_prompt
            
        except Exception as e:
            logger.warning(f"Error processing hint, using base prompt: {e}")
            return base_prompt
    
    def _smart_integrate_hint(self, base_prompt: str, hint: str, style: str) -> str:
        """
        НОВОЕ: Интеллектуально интегрирует подсказку в промпт.
        
        Args:
            base_prompt: Базовый промпт
            hint: Пользовательская подсказка
            style: Стиль генерации
            
        Returns:
            str: Промпт с интегрированной подсказкой
        """
        try:
            # Определяем тип подсказки
            hint_lower = hint.lower()
            
            # Стилевые подсказки интегрируем рядом с описанием стиля
            style_keywords = ["style", "painting", "art", "drawing", "illustration"]
            if any(keyword in hint_lower for keyword in style_keywords):
                # Ищем место для вставки стилевой подсказки
                style_insert_patterns = [
                    f"{style} style",
                    "style illustration",
                    "artwork",
                    "painting"
                ]
                
                for pattern in style_insert_patterns:
                    if pattern in base_prompt.lower():
                        insertion_point = base_prompt.lower().find(pattern) + len(pattern)
                        return (base_prompt[:insertion_point] + 
                               f", {hint}" + 
                               base_prompt[insertion_point:])
            
            # Цветовые и атмосферные подсказки добавляем в конец
            atmospheric_keywords = ["color", "mood", "atmosphere", "bright", "dark", "warm", "cool"]
            if any(keyword in hint_lower for keyword in atmospheric_keywords):
                return f"{base_prompt}, {hint}"
            
            # Элементы окружения вставляем перед финальными модификаторами
            element_keywords = ["background", "environment", "nature", "water", "fire", "mountain"]
            if any(keyword in hint_lower for keyword in element_keywords):
                # Ищем место перед quality модификаторами
                quality_patterns = ["highly detailed", "masterpiece", "best quality"]
                for pattern in quality_patterns:
                    if pattern in base_prompt.lower():
                        insertion_point = base_prompt.lower().find(pattern)
                        return (base_prompt[:insertion_point] + 
                               f"{hint}, " + 
                               base_prompt[insertion_point:])
            
            # По умолчанию добавляем в конец
            return f"{base_prompt}, {hint}"
            
        except Exception as e:
            logger.warning(f"Error in smart integration, using append: {e}")
            return f"{base_prompt}, {hint}"
    
    def _optimize_prompt_with_hint(self, prompt: str) -> str:
        """
        НОВОЕ: Оптимизирует промпт с подсказкой по длине и качеству.
        
        Args:
            prompt: Промпт для оптимизации
            
        Returns:
            str: Оптимизированный промпт
        """
        try:
            max_length = 500  # Увеличенный лимит для подсказок
            
            if len(prompt) <= max_length:
                return prompt
            
            # Разбиваем на части
            parts = [part.strip() for part in prompt.split(",")]
            
            # Приоритизируем части
            essential_parts = []
            style_parts = []
            hint_parts = []
            quality_parts = []
            detail_parts = []
            
            for part in parts:
                part_lower = part.lower()
                
                # Базовые элементы (всегда оставляем)
                if any(keyword in part_lower for keyword in ["character", "inspired by", "illustration of"]):
                    essential_parts.append(part)
                # Стилевые элементы (высокий приоритет)
                elif any(keyword in part_lower for keyword in ["style", "painting", "artwork"]):
                    style_parts.append(part)
                # Пользовательские подсказки (высокий приоритет)
                elif any(keyword in part_lower for keyword in ["user", "hint", "beautiful", "bright", "dark"]):
                    hint_parts.append(part)
                # Качественные модификаторы
                elif any(keyword in part_lower for keyword in ["detailed", "quality", "masterpiece"]):
                    quality_parts.append(part)
                else:
                    detail_parts.append(part)
            
            # Собираем в порядке приоритета
            optimized_parts = essential_parts + style_parts + hint_parts + quality_parts + detail_parts
            
            # Добавляем части пока не превысим лимит
            result_parts = []
            current_length = 0
            
            for part in optimized_parts:
                if current_length + len(part) + 2 <= max_length:
                    result_parts.append(part)
                    current_length += len(part) + 2
                else:
                    break
            
            optimized_prompt = ", ".join(result_parts)
            
            if len(optimized_prompt) < len(prompt):
                logger.debug(f"Optimized prompt length: {len(prompt)} -> {len(optimized_prompt)}")
            
            return optimized_prompt
            
        except Exception as e:
            logger.warning(f"Error optimizing prompt: {e}")
            return prompt[:500]  # Простое обрезание как fallback
    
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
            