"""
AI Image Generator - основной класс для генерации изображений по иероглифам.
Рефакторинг: разделен на отдельные компоненты для лучшей структуры кода.
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
        self.total_generation_time = 0
        self.start_time = time.time()
        
        logger.info("AIImageGenerator initialized with modular architecture")
    
    async def generate_character_image(
        self,
        character: str,
        translation: str = "",
        conditioning_weights: Optional[Dict[str, float]] = None,
        conditioning_methods: Optional[Dict[str, str]] = None,
        include_conditioning_images: bool = False,
        include_prompt: bool = False,
        include_semantic_analysis: bool = False,
        seed: Optional[int] = None,
        **generation_params
    ) -> AIGenerationResult:
        """
        Генерирует AI изображение для иероглифа.
        
        Args:
            character: Китайский иероглиф
            translation: Перевод иероглифа на русском
            conditioning_weights: Веса для разных типов conditioning
            conditioning_methods: Методы для разных типов conditioning
            include_conditioning_images: Включать ли conditioning изображения в результат
            include_prompt: Включать ли промпт в результат
            include_semantic_analysis: Включать ли semantic analysis в результат
            seed: Seed для воспроизводимости
            **generation_params: Дополнительные параметры генерации
            
        Returns:
            AIGenerationResult: Результат генерации
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting AI generation for character: '{character}', translation: '{translation}'")
            
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
            
            # 4. Перевод текста в английский
            english_translation, translation_metadata = await self.translation_manager.translate_to_english(
                character, translation
            )
            logger.info(f"✓ Translation: '{translation}' -> '{english_translation}' "
                       f"(source: {translation_metadata.get('source', 'unknown')})")
            
            # 5. Построение промпта
            prompt_result = await self.prompt_manager.build_prompt(
                character, english_translation
            )
            logger.info(f"✓ Generated prompt: '{prompt_result.main_prompt[:100]}...'")
            
            # 6. AI генерация
            final_image = await self.model_manager.run_generation(
                prompt=prompt_result.main_prompt,
                conditioning_images=conditioning_images,
                conditioning_weights=conditioning_weights or self.config.conditioning_weights,
                seed=seed,
                **generation_params
            )
            logger.info(f"✓ AI generation completed: {final_image.size}")
            
            # 7. Подготовка результата
            generation_time_ms = int((time.time() - start_time) * 1000)
            
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
                model_config=self.config
            )
            
            # Обновляем статистику
            self.generation_count += 1
            self.total_generation_time += generation_time_ms
            
            logger.info(f"✓ Successfully generated AI image for character: {character} "
                       f"(total_time: {generation_time_ms}ms)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in AI image generation for character {character}: {e}", exc_info=True)
            
            return AIGenerationResult.create_error_result(
                character=character,
                original_translation=translation,
                error_message=str(e),
                generation_time_ms=int((time.time() - start_time) * 1000)
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
        
        Returns:
            Dict[str, Any]: Статус генератора
        """
        try:
            uptime_seconds = int(time.time() - self.start_time)
            avg_generation_time = (
                self.total_generation_time / self.generation_count 
                if self.generation_count > 0 else 0
            )
            
            status = {
                "uptime_seconds": uptime_seconds,
                "generation_count": self.generation_count,
                "total_generation_time_ms": self.total_generation_time,
                "average_generation_time_ms": avg_generation_time,
                
                # Статус отдельных менеджеров
                "model_manager": await self.model_manager.get_status(),
                "conditioning_manager": await self.conditioning_manager.get_status(),
                "translation_manager": await self.translation_manager.get_status(),
                "prompt_manager": await self.prompt_manager.get_status(),
                "image_processor": await self.image_processor.get_status(),
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting generation status: {e}")
            return {"error": str(e)}
    
    async def get_translation_service_status(self) -> Dict[str, Any]:
        """Возвращает детальный статус Translation Service"""
        return await self.translation_manager.get_detailed_status()
    
    async def switch_translation_model(self, model_name: str) -> bool:
        """Переключает модель перевода"""
        return await self.translation_manager.switch_model(model_name)
    
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
            