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
from app.ai.prompt.semantic_analyzer import SemanticAnalyzer
from app.ai.prompt.style_definitions import StyleDefinitions

logger = get_module_logger(__name__)


@dataclass
class PromptConfig:
    """Конфигурация построения промптов"""
    # Семантический анализ
    enable_semantic_analysis: bool = True
    include_etymology: bool = True
    include_visual_associations: bool = True
    include_cultural_context: bool = True
    
    # Качественные модификаторы
    quality_boosters: List[str] = None
    composition_hints: List[str] = None
    
    # Длина промпта
    max_prompt_length: int = 400
    max_negative_prompt_length: int = 200
    
    # Кэширование
    enable_prompt_cache: bool = True
    cache_ttl_seconds: int = 3600
    
    def __post_init__(self):
        """Инициализация значений по умолчанию"""
        if self.quality_boosters is None:
            self.quality_boosters = [
                "masterpiece",
                "best quality", 
                "highly detailed",
                "8k resolution",
                "professional artwork"
            ]
        
        if self.composition_hints is None:
            self.composition_hints = [
                "rule of thirds",
                "dynamic composition",
                "balanced layout",
                "focal point emphasis"
            ]


@dataclass
class PromptResult:
    """Результат построения промпта"""
    success: bool
    main_prompt: str = ""
    negative_prompt: str = ""
    
    # Промпт анализ
    prompt_elements: Dict[str, List[str]] = None
    semantic_contribution: Dict[str, float] = None
    
    # Метаданные
    generation_time_ms: int = 0
    semantic_analysis_used: bool = False
    visual_elements_used: List[str] = None
    cultural_context_used: List[str] = None
    
    # Ошибки
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        """Инициализация после создания"""
        if self.prompt_elements is None:
            self.prompt_elements = {}
        if self.semantic_contribution is None:
            self.semantic_contribution = {}
        if self.visual_elements_used is None:
            self.visual_elements_used = []
        if self.cultural_context_used is None:
            self.cultural_context_used = []
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
        self.semantic_analyzer = SemanticAnalyzer()
        self.style_definitions = StyleDefinitions()
        
        # Кэш промптов
        self.prompt_cache: Dict[str, PromptResult] = {}
        
        # Статистика
        self.build_count = 0
        self.total_build_time = 0
        self.cache_hits = 0
        
        logger.info("PromptBuilder initialized")
    
    async def build_prompt(
        self,
        character: str,
        translation: str = "",
        style: str = "comic",
        include_semantic_analysis: bool = None,
        include_visual_elements: bool = None,
        include_cultural_context: bool = None,
        custom_elements: Optional[List[str]] = None
    ) -> PromptResult:
        """
        Строит промпт для AI генерации изображения.
        
        Args:
            character: Китайский иероглиф
            translation: Перевод иероглифа
            style: Стиль генерации
            include_semantic_analysis: Включать ли семантический анализ
            include_visual_elements: Включать ли визуальные элементы
            include_cultural_context: Включать ли культурный контекст
            custom_elements: Дополнительные элементы промпта
            
        Returns:
            PromptResult: Результат построения промпта
        """
        start_time = time.time()
        
        try:
            # Используем конфигурацию по умолчанию если не указано
            include_semantic = include_semantic_analysis if include_semantic_analysis is not None else self.config.enable_semantic_analysis
            include_visual = include_visual_elements if include_visual_elements is not None else self.config.include_visual_associations
            include_cultural = include_cultural_context if include_cultural_context is not None else self.config.include_cultural_context
            
            # Проверяем кэш
            cache_key = self._generate_cache_key(
                character, translation, style, 
                include_semantic, include_visual, include_cultural,
                custom_elements
            )
            
            if self.config.enable_prompt_cache:
                cached_result = self._get_from_cache(cache_key)
                if cached_result:
                    self.cache_hits += 1
                    return cached_result
            
            # 1. Семантический анализ иероглифа
            semantic_data = None
            if include_semantic:
                semantic_data = await self._analyze_character_semantics(character)
            
            # 2. Получение стилевых определений
            style_data = self.style_definitions.get_style_definition(style)
            
            # 3. Построение основного промпта
            main_prompt = await self._build_main_prompt(
                character=character,
                translation=translation,
                style=style,
                style_data=style_data,
                semantic_data=semantic_data,
                include_visual=include_visual,
                include_cultural=include_cultural,
                custom_elements=custom_elements or []
            )
            
            # 4. Построение негативного промпта
            negative_prompt = await self._build_negative_prompt(style, style_data)
            
            # 5. Оптимизация длины промптов
            main_prompt = self._optimize_prompt_length(main_prompt, self.config.max_prompt_length)
            negative_prompt = self._optimize_prompt_length(negative_prompt, self.config.max_negative_prompt_length)
            
            # Подсчет времени
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            # Создание результата
            result = PromptResult(
                success=True,
                main_prompt=main_prompt,
                negative_prompt=negative_prompt,
                generation_time_ms=generation_time_ms,
                semantic_analysis_used=include_semantic and semantic_data is not None,
                prompt_elements=self._analyze_prompt_elements(main_prompt),
                semantic_contribution=self._calculate_semantic_contribution(semantic_data, main_prompt),
                visual_elements_used=self._extract_visual_elements(semantic_data) if semantic_data else [],
                cultural_context_used=self._extract_cultural_context(semantic_data) if semantic_data else []
            )
            
            # Кэширование
            if self.config.enable_prompt_cache:
                self._save_to_cache(cache_key, result)
            
            # Обновление статистики
            self.build_count += 1
            self.total_build_time += generation_time_ms
            
            logger.info(f"Built prompt for character '{character}' (style: {style}, "
                       f"semantic: {include_semantic}, time: {generation_time_ms}ms)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error building prompt for character {character}: {e}", exc_info=True)
            
            # Возвращаем fallback промпт
            fallback_prompt = self._create_fallback_prompt(character, translation, style)
            
            return PromptResult(
                success=False,
                main_prompt=fallback_prompt,
                negative_prompt=self.style_definitions.get_style_definition(style).get("negative_prompt", ""),
                error_message=str(e),
                generation_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def _analyze_character_semantics(self, character: str) -> Optional[Dict[str, Any]]:
        """
        Выполняет семантический анализ иероглифа.
        
        Args:
            character: Иероглиф для анализа
            
        Returns:
            Optional[Dict[str, Any]]: Результаты семантического анализа
        """
        try:
            semantic_result = await self.semantic_analyzer.analyze_character(
                character=character,
                include_etymology=self.config.include_etymology,
                include_visual_associations=self.config.include_visual_associations,
                include_cultural_context=self.config.include_cultural_context
            )
            
            if semantic_result.success:
                return semantic_result.analysis_data
            else:
                logger.warning(f"Semantic analysis failed for {character}: {semantic_result.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error in semantic analysis for {character}: {e}")
            return None
    
    async def _build_main_prompt(
        self,
        character: str,
        translation: str,
        style: str,
        style_data: Dict[str, Any],
        semantic_data: Optional[Dict[str, Any]],
        include_visual: bool,
        include_cultural: bool,
        custom_elements: List[str]
    ) -> str:
        """
        Строит основной промпт для генерации.
        
        Args:
            character: Иероглиф
            translation: Перевод
            style: Стиль генерации
            style_data: Данные стиля
            semantic_data: Семантические данные
            include_visual: Включать визуальные элементы
            include_cultural: Включать культурный контекст
            custom_elements: Дополнительные элементы
            
        Returns:
            str: Основной промпт
        """
        prompt_parts = []
        
        # 1. Базовая часть промпта на основе стиля
        base_template = style_data.get("base_template", "")
        if base_template:
            # Заменяем плейсхолдеры
            base_prompt = base_template.format(
                character=character,
                translation=translation or "Chinese character",
                meaning=translation or character
            )
            prompt_parts.append(base_prompt)
        else:
            # Fallback базовый промпт
            prompt_parts.append(f"A {style} style illustration of {translation or character}")
        
        # 2. Семантические элементы
        if semantic_data and include_visual:
            visual_elements = self._build_visual_elements_prompt(semantic_data)
            if visual_elements:
                prompt_parts.append(visual_elements)
        
        # 3. Культурный контекст
        if semantic_data and include_cultural:
            cultural_elements = self._build_cultural_context_prompt(semantic_data)
            if cultural_elements:
                prompt_parts.append(cultural_elements)
        
        # 4. Стилевые модификаторы
        style_modifiers = style_data.get("style_modifiers", [])
        if style_modifiers:
            prompt_parts.append(", ".join(style_modifiers))
        
        # 5. Качественные модификаторы
        if self.config.quality_boosters:
            prompt_parts.append(", ".join(self.config.quality_boosters))
        
        # 6. Композиционные подсказки
        if self.config.composition_hints:
            # Добавляем только некоторые композиционные подсказки для разнообразия
            selected_hints = self.config.composition_hints[:2]
            prompt_parts.append(", ".join(selected_hints))
        
        # 7. Дополнительные элементы
        if custom_elements:
            prompt_parts.append(", ".join(custom_elements))
        
        # Объединяем все части
        main_prompt = ", ".join(filter(None, prompt_parts))
        
        return main_prompt
    
    def _build_visual_elements_prompt(self, semantic_data: Dict[str, Any]) -> str:
        """
        Строит часть промпта с визуальными элементами на основе семантики.
        
        Args:
            semantic_data: Семантические данные
            
        Returns:
            str: Часть промпта с визуальными элементами
        """
        visual_elements = []
        
        # Цветовые ассоциации
        color_associations = semantic_data.get("color_associations", [])
        if color_associations:
            # Выбираем первые 2 цвета для промпта
            colors = color_associations[:2]
            visual_elements.append(f"{' and '.join(colors)} colors")
        
        # Текстурные ассоциации
        texture_associations = semantic_data.get("texture_associations", [])
        if texture_associations:
            # Выбираем одну текстуру
            texture = texture_associations[0]
            visual_elements.append(f"{texture} texture")
        
        # Элементы природы (если есть в значении)
        meanings = semantic_data.get("meanings", [])
        nature_elements = []
        for meaning in meanings:
            if any(element in meaning.lower() for element in ["fire", "water", "wood", "earth", "metal"]):
                nature_elements.append(meaning.lower())
        
        if nature_elements:
            # Добавляем природные элементы
            element = nature_elements[0]
            visual_elements.append(f"{element} element")
        
        # Визуальные свойства иероглифа
        visual_properties = semantic_data.get("visual_properties", {})
        if visual_properties:
            complexity = visual_properties.get("complexity", "medium")
            if complexity in ["high", "complex"]:
                visual_elements.append("intricate details")
            elif complexity in ["low", "simple"]:
                visual_elements.append("clean simple lines")
        
        return ", ".join(visual_elements) if visual_elements else ""
    
    def _build_cultural_context_prompt(self, semantic_data: Dict[str, Any]) -> str:
        """
        Строит часть промпта с культурным контекстом.
        
        Args:
            semantic_data: Семантические данные
            
        Returns:
            str: Часть промпта с культурным контекстом
        """
        cultural_elements = []
        
        # Этимология и исторический контекст
        etymology = semantic_data.get("etymology", {})
        if etymology:
            historical_period = etymology.get("historical_period")
            if historical_period:
                cultural_elements.append(f"{historical_period} era aesthetic")
        
        # Философские ассоциации
        semantic_domains = semantic_data.get("semantic_domains", [])
        philosophy_domains = [domain for domain in semantic_domains 
                            if any(term in domain.lower() for term in ["philosophy", "wisdom", "virtue", "harmony"])]
        if philosophy_domains:
            cultural_elements.append("traditional Chinese wisdom")
        
        # Символическое значение
        symbolic_meaning = semantic_data.get("symbolic_meaning")
        if symbolic_meaning:
            cultural_elements.append("symbolic representation")
        
        # Каллиграфические элементы
        if semantic_data.get("calligraphy_style"):
            cultural_elements.append("calligraphic elegance")
        
        return ", ".join(cultural_elements) if cultural_elements else ""
    
    async def _build_negative_prompt(
        self, 
        style: str, 
        style_data: Dict[str, Any]
    ) -> str:
        """
        Строит негативный промпт.
        
        Args:
            style: Стиль генерации
            style_data: Данные стиля
            
        Returns:
            str: Негативный промпт
        """
        negative_parts = []
        
        # Базовые негативные элементы
        base_negative = [
            "blurry", "low quality", "distorted", "ugly", 
            "bad anatomy", "text", "watermark", "signature"
        ]
        negative_parts.extend(base_negative)
        
        # Стиль-специфичные негативные элементы
        style_negative = style_data.get("negative_prompt_additions", [])
        if style_negative:
            negative_parts.extend(style_negative)
        
        # Удаляем дубликаты
        negative_parts = list(dict.fromkeys(negative_parts))
        
        return ", ".join(negative_parts)
    
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
    
    def _analyze_prompt_elements(self, prompt: str) -> Dict[str, List[str]]:
        """
        Анализирует элементы промпта по категориям.
        
        Args:
            prompt: Промпт для анализа
            
        Returns:
            Dict[str, List[str]]: Элементы по категориям
        """
        elements = {
            "visual": [],
            "style": [],
            "quality": [],
            "composition": [],
            "cultural": [],
            "semantic": []
        }
        
        # Разбиваем промпт на части
        parts = [part.strip() for part in prompt.split(",")]
        
        for part in parts:
            part_lower = part.lower()
            
            # Классификация по ключевым словам
            if any(keyword in part_lower for keyword in ["color", "texture", "light", "shadow"]):
                elements["visual"].append(part)
            elif any(keyword in part_lower for keyword in ["style", "illustration", "artwork", "painting"]):
                elements["style"].append(part)
            elif any(keyword in part_lower for keyword in ["masterpiece", "quality", "detailed", "resolution"]):
                elements["quality"].append(part)
            elif any(keyword in part_lower for keyword in ["composition", "layout", "focal", "balance"]):
                elements["composition"].append(part)
            elif any(keyword in part_lower for keyword in ["chinese", "traditional", "cultural", "wisdom"]):
                elements["cultural"].append(part)
            else:
                elements["semantic"].append(part)
        
        return elements
    
    def _calculate_semantic_contribution(
        self, 
        semantic_data: Optional[Dict[str, Any]], 
        prompt: str
    ) -> Dict[str, float]:
        """
        Вычисляет вклад семантического анализа в промпт.
        
        Args:
            semantic_data: Семантические данные
            prompt: Готовый промпт
            
        Returns:
            Dict[str, float]: Вклад по категориям (0.0 - 1.0)
        """
        if not semantic_data:
            return {}
        
        contribution = {
            "visual_associations": 0.0,
            "cultural_context": 0.0,
            "etymology": 0.0,
            "symbolic_meaning": 0.0
        }
        
        prompt_lower = prompt.lower()
        
        # Визуальные ассоциации
        visual_terms = semantic_data.get("color_associations", []) + semantic_data.get("texture_associations", [])
        visual_matches = sum(1 for term in visual_terms if term.lower() in prompt_lower)
        if visual_terms:
            contribution["visual_associations"] = min(1.0, visual_matches / len(visual_terms))
        
        # Культурный контекст
        cultural_indicators = ["traditional", "chinese", "wisdom", "philosophy", "calligraphic"]
        cultural_matches = sum(1 for indicator in cultural_indicators if indicator in prompt_lower)
        contribution["cultural_context"] = min(1.0, cultural_matches / len(cultural_indicators))
        
        # Этимология
        etymology = semantic_data.get("etymology", {})
        if etymology:
            etymology_terms = [etymology.get("historical_period", ""), etymology.get("origin", "")]
            etymology_matches = sum(1 for term in etymology_terms if term and term.lower() in prompt_lower)
            contribution["etymology"] = min(1.0, etymology_matches / max(len(etymology_terms), 1))
        
        # Символическое значение
        if semantic_data.get("symbolic_meaning"):
            contribution["symbolic_meaning"] = 0.3 if "symbolic" in prompt_lower else 0.0
        
        return contribution
    
    def _extract_visual_elements(self, semantic_data: Dict[str, Any]) -> List[str]:
        """Извлекает использованные визуальные элементы."""
        visual_elements = []
        
        color_associations = semantic_data.get("color_associations", [])
        visual_elements.extend(color_associations[:2])  # Первые 2 цвета
        
        texture_associations = semantic_data.get("texture_associations", [])
        if texture_associations:
            visual_elements.append(texture_associations[0])  # Первая текстура
        
        return visual_elements
    
    def _extract_cultural_context(self, semantic_data: Dict[str, Any]) -> List[str]:
        """Извлекает использованный культурный контекст."""
        cultural_elements = []
        
        etymology = semantic_data.get("etymology", {})
        if etymology.get("historical_period"):
            cultural_elements.append(etymology["historical_period"])
        
        if semantic_data.get("calligraphy_style"):
            cultural_elements.append("calligraphy")
        
        semantic_domains = semantic_data.get("semantic_domains", [])
        philosophy_domains = [domain for domain in semantic_domains 
                            if "philosophy" in domain.lower() or "wisdom" in domain.lower()]
        cultural_elements.extend(philosophy_domains[:1])  # Первый философский домен
        
        return cultural_elements
    
    def _create_fallback_prompt(self, character: str, translation: str, style: str) -> str:
        """
        Создает fallback промпт при ошибках.
        
        Args:
            character: Иероглиф
            translation: Перевод
            style: Стиль
            
        Returns:
            str: Fallback промпт
        """
        style_adjectives = {
            "comic": "vibrant comic book style",
            "watercolor": "soft watercolor",
            "realistic": "detailed realistic",
            "anime": "anime-style"
        }
        
        style_adj = style_adjectives.get(style, style)
        subject = translation or f"Chinese character {character}"
        
        return f"A {style_adj} illustration of {subject}, masterpiece, best quality, highly detailed"
    
    # Методы кэширования
    
    def _generate_cache_key(
        self, 
        character: str, 
        translation: str, 
        style: str,
        semantic: bool,
        visual: bool, 
        cultural: bool,
        custom_elements: Optional[List[str]]
    ) -> str:
        """Генерирует ключ для кэширования промпта."""
        import hashlib
        
        key_parts = [
            character, translation, style,
            str(semantic), str(visual), str(cultural)
        ]
        
        if custom_elements:
            key_parts.append(",".join(sorted(custom_elements)))
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[PromptResult]:
        """Получает промпт из кэша."""
        if cache_key in self.prompt_cache:
            cached_result = self.prompt_cache[cache_key]
            
            # Проверяем срок жизни
            current_time = time.time()
            if hasattr(cached_result, 'cached_at'):
                if current_time - cached_result.cached_at < self.config.cache_ttl_seconds:
                    return cached_result
                else:
                    del self.prompt_cache[cache_key]
        
        return None
    
    def _save_to_cache(self, cache_key: str, result: PromptResult):
        """Сохраняет промпт в кэш."""
        result.cached_at = time.time()
        self.prompt_cache[cache_key] = result
        
        # Ограничиваем размер кэша
        max_cache_size = 1000
        if len(self.prompt_cache) > max_cache_size:
            # Удаляем старые записи
            sorted_items = sorted(
                self.prompt_cache.items(),
                key=lambda x: getattr(x[1], 'cached_at', 0)
            )
            
            for key, _ in sorted_items[:len(self.prompt_cache) - max_cache_size]:
                del self.prompt_cache[key]
    
    # Публичные методы статистики
    
    def get_builder_stats(self) -> Dict[str, Any]:
        """Возвращает статистику PromptBuilder."""
        return {
            "build_count": self.build_count,
            "total_build_time_ms": self.total_build_time,
            "avg_build_time_ms": self.total_build_time / max(self.build_count, 1),
            "cache_hits": self.cache_hits,
            "cache_hit_rate": self.cache_hits / max(self.build_count, 1),
            "cache_size": len(self.prompt_cache),
            "semantic_analysis_enabled": self.config.enable_semantic_analysis
        }
    
    def clear_cache(self):
        """Очищает кэш промптов."""
        self.prompt_cache.clear()
        logger.info("Prompt cache cleared")
    
    def clear_stats(self):
        """Очищает статистику."""
        self.build_count = 0
        self.total_build_time = 0
        self.cache_hits = 0
        logger.info("PromptBuilder statistics cleared")
        