"""
AI Image Generator - основной класс для генерации изображений по иероглифам.
Рефакторинг: разделен на отдельные компоненты для лучшей структуры кода.
ОБНОВЛЕНО: Добавлена поддержка пользовательской подсказки hint_writing
"""

import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass

from app.utils.logger import get_module_logger
from app.ai.core.generation_config import AIGenerationConfig
from app.ai.core.generation_result import AIGenerationResult
from app.ai.core.model_manager import ModelManager
from app.ai.core.conditioning_manager import ConditioningManager
from app.ai.core.translation_manager import TranslationManager
from app.ai.core.prompt_manager import PromptManager
from app.ai.core.image_processor import ImageProcessor

logger = get_module_logger(__name__)


class AIImageGenerator:
    """
    Основной класс для AI генерации изображений по иероглифам.
    Рефакторинг: использует отдельные менеджеры для каждого аспекта генерации.
    ОБНОВЛЕНО: Поддержка пользовательских подсказок hint_writing
    """
    
    def __init__(self, config: Optional[AIGenerationConfig] = None):
        """
        Инициализация AI генератора.
        
        Args:
            config: Конфигурация AI генерации
        """
        self.config = config or AIGenerationConfig()
        
        # Инициализация менеджеров
        self.model_manager = ModelManager(self.config)
        self.conditioning_manager = ConditioningManager(self.config)
        self.translation_manager = TranslationManager(self.config)
        self.prompt_manager = PromptManager(self.config)
        self.image_processor = ImageProcessor(self.config)
        
        # Статистика
        self.generation_count = 0
        self.hint_generation_count = 0  # НОВОЕ: счетчик генераций с подсказками
        self.total_generation_time = 0
        self.start_time = time.time()
        
        logger.info("AIImageGenerator initialized with modular architecture and hint support")
    
    async def generate_character_image(
        self,
        character: str,
        translation: str = "",
        user_hint: Optional[str] = None,  # НОВОЕ: пользовательская подсказка
        style: str = "comic",  # НОВОЕ: стиль генерации
        conditioning_weights: Optional[Dict[str, float]] = None,
        conditioning_methods: Optional[Dict[str, str]] = None,
        include_conditioning_images: bool = False,
        include_prompt: bool = False,
        seed: Optional[int] = None,
        **generation_params
    ) -> AIGenerationResult:
        """
        Генерирует AI изображение для иероглифа.
        ОБНОВЛЕНО: Поддержка пользовательской подсказки hint_writing
        
        Args:
            character: Китайский иероглиф
            translation: Перевод иероглифа на русском
            user_hint: Пользовательская подсказка для AI генерации
            style: Стиль генерации (comic, watercolor, realistic, etc.)
            conditioning_weights: Веса для разных типов conditioning
            conditioning_methods: Методы для разных типов conditioning
            include_conditioning_images: Включать ли conditioning изображения в результат
            include_prompt: Включать ли промпт в результат
            seed: Seed для воспроизводимости
            **generation_params: Дополнительные параметры генерации
            
        Returns:
            AIGenerationResult: Результат генерации с метаданными подсказки
        """
        start_time = time.time()
        
        try:
            # Логируем информацию о генерации с подсказкой
            hint_info = f", user_hint: '{user_hint}'" if user_hint else ""
            logger.info(f"Starting AI generation for character: '{character}', "
                       f"translation: '{translation}', style: '{style}'{hint_info}")
            
            # 1. Инициализация всех менеджеров
            await self._ensure_managers_ready()
            
            # 2. Предобработка иероглифа
            base_image = await self.image_processor.preprocess_character(
                character, self.config.width, self.config.height
            )
            logger.info(f"✓ Character preprocessed: {base_image.size}")
            
            # 3. Генерация conditioning изображений
            conditioning_images = await self.conditioning_manager.generate_all_conditioning(
                base_image, character, conditioning_methods
            )
            logger.info(f"✓ Generated conditioning for: {list(conditioning_images.keys())}")
            
            # 4. Обработка перевода (основного)
            english_translation, translation_metadata = await self.translation_manager.translate_to_english(
                character, translation
            )
            logger.info(f"✓ Translation: '{translation}' -> '{english_translation}' "
                       f"(source: {translation_metadata.get('source', 'unknown')})")
            
            # 5. НОВОЕ: Обработка пользовательской подсказки
            user_hint_data = {}
            english_hint = ""
            
            if user_hint and user_hint.strip():
                logger.info(f"Processing user hint: '{user_hint}'")
                
                # Переводим подсказку на английский
                english_hint, hint_translation_metadata = await self.translation_manager.translate_to_english(
                    character, user_hint
                )
                
                user_hint_data = {
                    "original_hint": user_hint,
                    "translated_hint": english_hint,
                    "translation_source": hint_translation_metadata.get('source', 'unknown'),
                    "translation_time_ms": hint_translation_metadata.get('time_ms', 0),
                    "used_in_prompt": True
                }
                
                logger.info(f"✓ User hint translated: '{user_hint}' -> '{english_hint}' "
                           f"(source: {hint_translation_metadata.get('source', 'unknown')})")
                
                # Увеличиваем счетчик генераций с подсказками
                self.hint_generation_count += 1
            
            # 6. Построение промпта с учетом подсказки
            prompt_result = await self.prompt_manager.build_prompt(
                character=character,
                translation=english_translation,
                user_hint=english_hint,  # НОВОЕ: передаем переведенную подсказку
                style=style  # НОВОЕ: передаем стиль
            )
            logger.info(f"✓ Generated prompt: '{prompt_result.main_prompt[:100]}...'")
            
            logger.info(f"generation_params={generation_params.keys()}")
            logger.info(f"generation_params[guidance_scale]={generation_params['guidance_scale']}")
            
            # 7. AI генерация
            final_image = await self.model_manager.run_generation(
                prompt=prompt_result.main_prompt,
                conditioning_images=conditioning_images,
                conditioning_weights=conditioning_weights or self.config.conditioning_weights,
                seed=seed,
                **generation_params
            )
            logger.info(f"✓ AI generation completed: {final_image.size}")
            
            # 8. Подготовка результата с метаданными подсказки
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            # ОБНОВЛЕНО: Создаем результат с метаданными подсказки
            result = AIGenerationResult.create_success_result(
                generated_image=final_image,
                base_image=base_image if include_conditioning_images else None,
                conditioning_images=conditioning_images if include_conditioning_images else None,
                prompt_used=prompt_result.main_prompt if include_prompt else None,
                character=character,
                original_translation=translation,
                english_translation=english_translation,
                translation_metadata=translation_metadata,
                conditioning_weights=conditioning_weights or self.config.conditioning_weights,
                generation_time_ms=generation_time_ms,
                seed_used=seed,
                model_config=self.config,
                # user_hint_metadata=user_hint_data,  # НОВОЕ: метаданные подсказки
                # style_used=style  # НОВОЕ: использованный стиль
            )
            
            # Обновляем статистику
            self.generation_count += 1
            self.total_generation_time += generation_time_ms
            
            # Логируем с информацией о подсказке
            hint_result_info = ""
            if user_hint:
                hint_result_info = f" (hint: '{user_hint}' -> '{english_hint}', used: {user_hint_data.get('used_in_prompt', False)})"
            
            logger.info(f"✓ Successfully generated AI image for character: {character} "
                       f"(style: {style}, total_time: {generation_time_ms}ms{hint_result_info})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in AI image generation for character {character}: {e}", exc_info=True)
            
            return AIGenerationResult.create_error_result(
                character=character,
                original_translation=translation,
                error_message=str(e),
                generation_time_ms=int((time.time() - start_time) * 1000),
                # user_hint=user_hint  # НОВОЕ: сохраняем подсказку в случае ошибки
            )
    
    async def _ensure_managers_ready(self):
        """Обеспечивает готовность всех менеджеров"""
        try:
            # Инициализируем менеджеры в правильном порядке
            await self.model_manager.ensure_models_loaded()
            await self.translation_manager.ensure_translation_ready()
            await self.conditioning_manager.ensure_conditioning_ready()
            await self.prompt_manager.ensure_prompt_ready()
            
            logger.debug("✓ All managers ready")
            
        except Exception as e:
            logger.error(f"Failed to initialize managers: {e}")
            raise RuntimeError(f"Manager initialization failed: {e}")
    
    async def get_generation_status(self) -> Dict[str, Any]:
        """
        Возвращает статус AI генератора.
        ОБНОВЛЕНО: Включает статистику использования подсказок
        
        Returns:
            Dict[str, Any]: Статус генератора с метриками подсказок
        """
        try:
            uptime_seconds = int(time.time() - self.start_time)
            avg_generation_time = (
                self.total_generation_time / self.generation_count 
                if self.generation_count > 0 else 0
            )
            
            # НОВОЕ: Статистика использования подсказок
            hint_usage_percentage = (
                (self.hint_generation_count / self.generation_count * 100)
                if self.generation_count > 0 else 0
            )
            
            status = {
                "uptime_seconds": uptime_seconds,
                "generation_count": self.generation_count,
                "hint_generation_count": self.hint_generation_count,  # НОВОЕ
                "hint_usage_percentage": hint_usage_percentage,  # НОВОЕ
                "total_generation_time_ms": self.total_generation_time,
                "average_generation_time_ms": avg_generation_time,
                
                # Статус отдельных менеджеров
                "model_manager": await self.model_manager.get_status(),
                "conditioning_manager": await self.conditioning_manager.get_status(),
                "translation_manager": await self.translation_manager.get_status(),
                "prompt_manager": await self.prompt_manager.get_status(),
                "image_processor": await self.image_processor.get_status(),
                
                # НОВОЕ: Возможности системы
                "capabilities": {
                    "user_hints": True,
                    "hint_translation": True,
                    "style_support": True,
                    "multi_language": True,
                    "controlnet_union": True,
                    "conditioning_types": ["canny", "depth", "segmentation", "scribble"]
                }
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting generation status: {e}")
            return {"error": str(e)}
    
    async def get_translation_service_status(self) -> Dict[str, Any]:
        """
        Возвращает детальный статус Translation Service.
        ОБНОВЛЕНО: Включает метрики перевода подсказок
        """
        try:
            base_status = await self.translation_manager.get_detailed_status()
            
            # НОВОЕ: Добавляем информацию о поддержке подсказок
            base_status["hint_support"] = {
                "enabled": True,
                "translation_enabled": True,
                "supported_languages": ["русский", "english"],
                "max_hint_length": 200
            }
            
            return base_status
            
        except Exception as e:
            logger.error(f"Error getting translation service status: {e}")
            return {"error": str(e)}
    
    async def switch_translation_model(self, model_name: str) -> bool:
        """Переключает модель перевода"""
        return await self.translation_manager.switch_model(model_name)
    
    async def validate_user_hint(self, hint: str) -> Dict[str, Any]:
        """
        НОВОЕ: Валидирует пользовательскую подсказку
        
        Args:
            hint: Пользовательская подсказка
            
        Returns:
            Dict[str, Any]: Результат валидации
        """
        try:
            if not hint or not hint.strip():
                return {
                    "valid": True,
                    "message": "Empty hint is valid",
                    "suggestions": []
                }
            
            # Проверяем длину
            if len(hint) > 200:
                return {
                    "valid": False,
                    "message": "Hint is too long (max 200 characters)",
                    "errors": ["hint_too_long"],
                    "max_length": 200,
                    "current_length": len(hint)
                }
            
            # Проверяем на недопустимые символы или слова
            forbidden_patterns = [
                "nsfw", "nude", "explicit", "sexual", "violence", "blood",
                "порно", "голый", "секс", "насилие", "кровь"
            ]
            
            hint_lower = hint.lower()
            found_forbidden = [pattern for pattern in forbidden_patterns if pattern in hint_lower]
            
            if found_forbidden:
                return {
                    "valid": False,
                    "message": "Hint contains inappropriate content",
                    "errors": ["inappropriate_content"],
                    "forbidden_patterns": found_forbidden
                }
            
            # Подсказка валидна
            return {
                "valid": True,
                "message": "Hint is valid",
                "processed_hint": hint.strip(),
                "estimated_translation_quality": "good" if len(hint.strip()) > 10 else "basic"
            }
            
        except Exception as e:
            logger.error(f"Error validating user hint: {e}")
            return {
                "valid": False,
                "message": f"Validation error: {str(e)}",
                "errors": ["validation_error"]
            }
    
    async def get_hint_suggestions(self, character: str, translation: str) -> Dict[str, Any]:
        """
        НОВОЕ: Предлагает варианты подсказок для иероглифа
        
        Args:
            character: Китайский иероглиф
            translation: Перевод иероглифа
            
        Returns:
            Dict[str, Any]: Предложения подсказок
        """
        try:
            # Базовые предложения подсказок
            suggestions = {
                "style_suggestions": [
                    "в стиле японской каллиграфии",
                    "акварельный рисунок",
                    "минималистичный дизайн",
                    "традиционная китайская живопись"
                ],
                "mood_suggestions": [
                    "спокойная атмосфера",
                    "яркий и энергичный",
                    "мистическое настроение",
                    "философская глубина"
                ],
                "element_suggestions": [
                    "с элементами природы",
                    "на фоне заката",
                    "с золотыми акцентами",
                    "в окружении цветов"
                ]
            }
            
            # Специфичные предложения на основе перевода
            if translation:
                translation_lower = translation.lower()
                
                if any(word in translation_lower for word in ["вода", "река", "море"]):
                    suggestions["contextual_suggestions"] = [
                        "с волнами и брызгами",
                        "отражение в воде",
                        "морская тематика"
                    ]
                elif any(word in translation_lower for word in ["огонь", "солнце", "свет"]):
                    suggestions["contextual_suggestions"] = [
                        "с языками пламени",
                        "солнечные лучи",
                        "теплое свечение"
                    ]
                elif any(word in translation_lower for word in ["дерево", "лес", "природа"]):
                    suggestions["contextual_suggestions"] = [
                        "среди зеленой листвы",
                        "в лесной чаще",
                        "с древесной текстурой"
                    ]
            
            return {
                "character": character,
                "translation": translation,
                "suggestions": suggestions,
                "tips": [
                    "Используйте описательные прилагательные",
                    "Упоминайте конкретные стили или техники",
                    "Добавляйте детали окружения или настроения",
                    "Избегайте противоречивых описаний"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting hint suggestions: {e}")
            return {
                "error": str(e),
                "suggestions": {"basic": ["красивый рисунок", "в ярких цветах"]}
            }
    
    async def cleanup(self):
        """Очищает ресурсы генератора"""
        try:
            logger.info("Cleaning up AI Image Generator...")
            
            # Очищаем все менеджеры
            await self.translation_manager.cleanup()
            await self.model_manager.cleanup()
            await self.conditioning_manager.cleanup()
            await self.prompt_manager.cleanup()
            await self.image_processor.cleanup()
            
            logger.info("✓ AI Image Generator cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def __del__(self):
        """Деструктор для очистки ресурсов"""
        if hasattr(self, 'generation_count'):
            logger.warning("AIImageGenerator deleted without explicit cleanup")
            