"""
Prompt Builder - система построения промптов для AI генерации изображений.
Интегрирует семантический анализ иероглифов и стили генерации.
"""

import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass
import logging
import re

from app.utils.logger import get_module_logger
from app.ai.prompt.style_definitions import StyleDefinitions

logger = get_module_logger(__name__)


@dataclass
class PromptConfig:
    """Конфигурация построения промптов"""
    # Длина промпта
    max_prompt_length: int = 400
    
@dataclass
class PromptResult:
    """Результат построения промпта"""
    success: bool
    main_prompt: str = ""
    
    # Метаданные
    generation_time_ms: int = 0

    style_data: Optional[Dict[str, Any]] = None
    
    # Ошибки
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        """Инициализация после создания"""
        if self.style_data is None:
            self.style_data = {}
        if self.warnings is None:
            self.warnings = []


class PromptBuilder:
    """
    Основной класс для построения промптов AI генерации.
    Использует семантический анализ иероглифов и стилевые определения.
    """
    
    def __init__(self, config: Optional[PromptConfig] = None):
        """
        Инициализация PromptBuilder.
        
        Args:
            config: Конфигурация построения промптов
        """
        self.config = config or PromptConfig()
        
        # Компоненты системы
        self.style_definitions = StyleDefinitions()
        
        logger.info("PromptBuilder initialized")
    
    async def build_prompt(
        self,
        character: str,
        translation: str = "",
        style: str = "comic",
    ) -> PromptResult:
        """
        Строит промпт для AI генерации изображения.
        
        Args:
            character: Китайский иероглиф
            translation: Перевод иероглифа
            style: Стиль генерации
            
        Returns:
            PromptResult: Результат построения промпта
        """
        start_time = time.time()
        
        try:
            # 2. Получение стилевых определений
            style_data = self.style_definitions.get_style_definition(style)
            
            # 3. Построение основного промпта
            main_prompt = await self._build_main_prompt(
                character=character,
                translation=translation,
                style=style,
                style_data=style_data,
            )
            
            # 5. Оптимизация длины промптов
            main_prompt = self._optimize_prompt_length(main_prompt, self.config.max_prompt_length)
            
            # Подсчет времени
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            # Создание результата
            result = PromptResult(
                success=True,
                main_prompt=main_prompt,
                generation_time_ms=generation_time_ms,
                style_data=style_data,
            )
            
            logger.info(f"Built prompt for character '{character}' (style: {style}, "
                       f"time: {generation_time_ms}ms)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error building prompt for character {character}: {e}", exc_info=True)
            
            return PromptResult(
                success=False,
                main_prompt=None,
                error_message=str(e),
                generation_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def _build_main_prompt(
        self,
        character: str,
        translation: str,
        style: str,
        style_data: Dict[str, Any],
    ) -> str:
        """
        Строит основной промпт для генерации.
        
        Args:
            character: Иероглиф
            translation: Перевод
            style: Стиль генерации
            style_data: Данные стиля
            include_visual: Включать визуальные элементы
            include_cultural: Включать культурный контекст
            custom_elements: Дополнительные элементы
            
        Returns:
            str: Основной промпт
        """
        prompt_parts = []
        
        # 1. Базовая часть промпта на основе стиля
        base_template = style_data.get("base_template", "")
        # Заменяем плейсхолдеры
        base_prompt = base_template.format(
            character=character,
            meaning=translation.replace("\n", ",")
        )
        prompt_parts.append(base_prompt)
        
        main_prompt = ", ".join(filter(None, prompt_parts))
        
        return main_prompt
    
    def _optimize_prompt_length(self, prompt: str, max_length: int) -> str:
        """
        Оптимизирует длину промпта.
        
        Args:
            prompt: Исходный промпт
            max_length: Максимальная длина
            
        Returns:
            str: Оптимизированный промпт
        """
        if len(prompt) <= max_length:
            return prompt
        
        # Разбиваем на части по запятым
        parts = [part.strip() for part in prompt.split(",")]
        
        # Приоритетность частей (сначала важные)
        prioritized_parts = []
        quality_parts = []
        detail_parts = []
        
        for part in parts:
            if any(keyword in part.lower() for keyword in ["masterpiece", "best quality", "highly detailed"]):
                quality_parts.append(part)
            elif any(keyword in part.lower() for keyword in ["illustration", "artwork", "painting", "style"]):
                prioritized_parts.insert(0, part)  # В начало
            else:
                detail_parts.append(part)
        
        # Собираем в порядке приоритета
        optimized_parts = prioritized_parts + quality_parts + detail_parts
        
        # Добавляем части пока не превысим лимит
        result_parts = []
        current_length = 0
        
        for part in optimized_parts:
            if current_length + len(part) + 2 <= max_length:  # +2 для ", "
                result_parts.append(part)
                current_length += len(part) + 2
            else:
                break
        
        return ", ".join(result_parts)
 