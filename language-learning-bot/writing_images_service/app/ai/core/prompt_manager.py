"""
Prompt Manager
Менеджер для построения промптов для AI генерации.
"""

import time
import random
from typing import Dict, Any, Optional

from app.utils.logger import get_module_logger
from app.ai.core.generation_config import AIGenerationConfig
from app.ai.prompt.prompt_builder import PromptBuilder, PromptResult

logger = get_module_logger(__name__)


class PromptManager:
    """
    Менеджер для построения промптов для AI генерации.
    """
    
    def __init__(self, config: AIGenerationConfig):
        """
        Инициализация Prompt Manager.
        
        Args:
            config: Конфигурация AI генерации
        """
        self.config = config
        self.prompt_builder: Optional[PromptBuilder] = None
        
        # Статистика
        self.prompt_count = 0
        self.total_prompt_time = 0
        self.start_time = time.time()
        
        logger.info("PromptManager initialized")
    
    async def ensure_prompt_ready(self):
        """Обеспечивает готовность prompt builder"""
        if self.prompt_builder is None:
            self.prompt_builder = PromptBuilder()
        
        logger.debug("✓ Prompt builder ready")
    
    async def build_prompt(
        self,
        character: str,
        english_translation: str,
        style: Optional[str] = None
    ) -> PromptResult:
        """
        Строит промпт для AI генерации.
        
        Args:
            character: Иероглиф
            english_translation: Английский перевод
            style: Стиль генерации (опционально)
            
        Returns:
            PromptResult: Результат построения промпта
        """
        start_time = time.time()
        
        try:
            await self.ensure_prompt_ready()
            
            # Выбираем стиль
            if style is None:
                available_styles = self.prompt_builder.style_definitions.get_style_names()
                style = random.choice(available_styles)
            
            # Строим промпт
            prompt_result = await self.prompt_builder.build_prompt(
                character=character,
                translation=english_translation,
                style=style
            )
            
            if not prompt_result.success:
                raise RuntimeError(f"Prompt building failed: {prompt_result.error_message}")
            
            # Обновляем статистику
            prompt_time = time.time() - start_time
            self.prompt_count += 1
            self.total_prompt_time += prompt_time
            
            logger.debug(f"Built prompt for {character} with English translation '{english_translation}' "
                        f"(style: {style}): '{prompt_result.main_prompt[:100]}...' "
                        f"in {prompt_time:.3f}s")
            
            return prompt_result
            
        except Exception as e:
            logger.error(f"Error building prompt: {e}")
            raise RuntimeError(f"Prompt generation failed: {e}")
    
    async def build_prompt_with_custom_style(
        self,
        character: str,
        english_translation: str,
        custom_style_template: str,
        style_modifiers: Optional[str] = None
    ) -> PromptResult:
        """
        Строит промпт с кастомным стилем.
        
        Args:
            character: Иероглиф
            english_translation: Английский перевод
            custom_style_template: Кастомный шаблон стиля
            style_modifiers: Дополнительные модификаторы стиля
            
        Returns:
            PromptResult: Результат построения промпта
        """
        try:
            await self.ensure_prompt_ready()
            
            # Используем кастомный шаблон
            prompt_result = await self.prompt_builder.build_custom_prompt(
                character=character,
                translation=english_translation,
                template=custom_style_template,
                modifiers=style_modifiers
            )
            
            if not prompt_result.success:
                raise RuntimeError(f"Custom prompt building failed: {prompt_result.error_message}")
            
            logger.debug(f"Built custom prompt for {character}: '{prompt_result.main_prompt[:100]}...'")
            return prompt_result
            
        except Exception as e:
            logger.error(f"Error building custom prompt: {e}")
            raise RuntimeError(f"Custom prompt generation failed: {e}")
    
    def get_available_styles(self) -> list:
        """Возвращает доступные стили промптов"""
        if self.prompt_builder is None:
            # Возвращаем базовые стили
            return ["comic", "watercolor", "realistic", "anime", "ink"]
        
        return self.prompt_builder.style_definitions.get_style_names()
    
    async def get_status(self) -> Dict[str, Any]:
        """Возвращает статус Prompt Manager"""
        uptime_seconds = int(time.time() - self.start_time)
        avg_prompt_time = (
            self.total_prompt_time / self.prompt_count 
            if self.prompt_count > 0 else 0
        )
        
        return {
            "prompt_count": self.prompt_count,
            "total_prompt_time_seconds": self.total_prompt_time,
            "average_prompt_time_seconds": avg_prompt_time,
            "uptime_seconds": uptime_seconds,
            "available_styles": self.get_available_styles(),
            "prompt_builder_ready": self.prompt_builder is not None
        }
    
    async def cleanup(self):
        """Очищает ресурсы Prompt Manager"""
        try:
            logger.info("Cleaning up Prompt Manager...")
            
            # Prompt Builder не требует специальной очистки
            self.prompt_builder = None
            
            logger.info("✓ Prompt Manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during prompt manager cleanup: {e}")
            