"""
AI Image Generator - основной класс для генерации изображений по иероглифам.
Использует Multi-ControlNet pipeline для создания изображений разных стилей.
"""

import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass
from PIL import Image
import numpy as np
import io
import base64
import random

from app.utils.logger import get_module_logger
from app.utils.image_utils import get_image_processor
from app.ai.conditioning.canny_conditioning import CannyConditioning
from app.ai.conditioning.depth_conditioning import DepthConditioning
from app.ai.conditioning.segmentation_conditioning import SegmentationConditioning
from app.ai.conditioning.scribble_conditioning import ScribbleConditioning
from app.ai.prompt.prompt_builder import PromptBuilder, PromptResult
from app.ai.multi_controlnet_pipeline import MultiControlNetPipeline, PipelineConfig
from app.ai.models.model_loader import ModelLoader

logger = get_module_logger(__name__)


@dataclass
class AIGenerationConfig:
    """Конфигурация AI генерации"""
    # Модели
    base_model: str = "stabilityai/stable-diffusion-xl-base-1.0"
    controlnet_models: Dict[str, str] = None
    
    # Параметры генерации
    num_inference_steps: int = 30
    guidance_scale: float = 7.5
    width: int = 1024
    height: int = 1024
    batch_size: int = 1
    
    # Conditioning веса по умолчанию
    conditioning_weights: Dict[str, float] = None
    
    # GPU настройки
    device: str = "cuda"
    memory_efficient: bool = True
    enable_attention_slicing: bool = True
    enable_cpu_offload: bool = False
    
    def __post_init__(self):
        """Инициализация значений по умолчанию"""
        if self.controlnet_models is None:
            # UPDATED: Single Union ControlNet instead of 4 separate models
            self.controlnet_models = {
                "union": "xinsir/controlnet-union-sdxl-1.0"
            }
        
        if self.conditioning_weights is None:
            self.conditioning_weights = {
                "canny": 0.8,
                "depth": 0.6,
                "segmentation": 0.5,
                "scribble": 0.4
            }


@dataclass 
class AIGenerationResult:
    """Результат AI генерации изображения"""
    success: bool
    generated_image_base64: Optional[str] = None
    
    # Промежуточные результаты
    base_image_base64: Optional[str] = None
    conditioning_images_base64: Optional[Dict[str, Dict[str, str]]] = None
    
    # Промпты
    prompt_used: Optional[str] = None
    
    # Метаданные
    generation_metadata: Optional[Dict[str, Any]] = None
    
    # Ошибки и предупреждения
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        """Инициализация после создания"""
        if self.warnings is None:
            self.warnings = []
    
    def to_base64(self, image: Image.Image) -> str:
        """Конвертирует изображение в base64"""
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')


class AIImageGenerator:
    """
    Основной класс для AI генерации изображений по иероглифам.
    Координирует работу conditioning генераторов и Multi-ControlNet pipeline.
    """
    
    def __init__(self, config: Optional[AIGenerationConfig] = None):
        """
        Инициализация AI генератора.
        
        Args:
            config: Конфигурация AI генерации
        """
        self.config = config or AIGenerationConfig()
        self.image_processor = get_image_processor()
        
        # Инициализация conditioning генераторов
        self.conditioning_generators = {
            "canny": CannyConditioning(),
            "depth": DepthConditioning(),
            "segmentation": SegmentationConditioning(),
            "scribble": ScribbleConditioning()
        }
        
        # Model Loader и Pipeline
        self.model_loader = None
        self.pipeline = None
        self._models_loaded = False
        self._model_loading_lock = asyncio.Lock()
        
        # Статистика
        self.generation_count = 0
        self.total_generation_time = 0
        self.start_time = time.time()
        
        logger.info("AIImageGenerator initialized with ControlNet Union support")
    
    async def generate_character_image(
        self,
        character: str,
        translation: str = "",
        conditioning_weights: Optional[Dict[str, float]] = None,
        conditioning_methods: Optional[Dict[str, str]] = None,
        include_conditioning_images: bool = False,
        include_prompt: bool = False,
        seed: Optional[int] = None,
        **generation_params
    ) -> AIGenerationResult:
        """
        Генерирует AI изображение для иероглифа.
        
        Args:
            character: Китайский иероглиф
            translation: Перевод иероглифа
            conditioning_weights: Веса для разных типов conditioning
            conditioning_methods: Методы для разных типов conditioning
            include_conditioning_images: Включать ли conditioning изображения в результат
            include_prompt: Включать ли промпт в результат
            seed: Seed для воспроизводимости
            **generation_params: Дополнительные параметры генерации
            
        Returns:
            AIGenerationResult: Результат генерации
        """
        start_time = time.time()
        
        try:
            # Загружаем модели если нужно
            await self._ensure_models_loaded()
            
            # Настраиваем параметры
            weights = conditioning_weights or self.config.conditioning_weights
            
            logger.info(f"Starting AI generation for character: '{character}', translation: '{translation}'")
            
            # 1. Предобработка - рендеринг иероглифа
            base_image = await self._preprocess_character(
                character, 
                self.config.width, 
                self.config.height
            )
            
            logger.info(f"✓ Character preprocessed: {base_image.size}")
            base_image.save("./temp/base_image.png")

            # 2. Генерация всех conditioning изображений
            conditioning_images = await self._generate_all_conditioning(
                base_image, character
            )
            logger.info(f"✓ Generated conditioning for: {list(conditioning_images.keys())}")
            for cond_type, cond_data in conditioning_images.items():
                for method, image in cond_data.items():
                    image.save(f"./temp/{cond_type}_{method}.png")
            
            # 3. Построение промпта
            prompt_result = await self._generate_prompt(
                character, translation
            )
            logger.info(f"✓ Generated prompt: '{prompt_result.main_prompt}...'")
            
            # 4. AI генерация с Multi-ControlNet
            final_image = await self._run_ai_generation(
                prompt=prompt_result.main_prompt,
                conditioning_images=conditioning_images,
                conditioning_weights=weights,
                seed=seed,
                **generation_params
            )
            
            logger.info(f"✓ AI generation completed: {final_image.size}")
            
            # Подсчет времени генерации
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            # Создание результата
            result = AIGenerationResult(
                success=True,
                generated_image_base64=self._to_base64(final_image),
                base_image_base64=self._to_base64(base_image) if include_conditioning_images else None,
                conditioning_images_base64=self._conditioning_to_base64(conditioning_images) if include_conditioning_images else None,
                prompt_used=prompt_result.main_prompt if include_prompt else None,
                generation_metadata={
                    'character': character,
                    'translation': translation,
                    'conditioning_weights_used': weights,
                    'conditioning_methods_used': {
                        conditioning_type: list(conditioning_images[conditioning_type].keys())
                        for conditioning_type in conditioning_images.keys()
                    },
                    'generation_time_ms': generation_time_ms,
                    'seed_used': seed,
                    'model_used': self.config.base_model,
                    'controlnet_model': "union",  # UPDATED: Single union model
                    'image_size': (self.config.width, self.config.height),
                    'inference_steps': generation_params.get('num_inference_steps', self.config.num_inference_steps),
                    'guidance_scale': generation_params.get('guidance_scale', self.config.guidance_scale)
                }
            )
            
            # Обновляем статистику
            self.generation_count += 1
            self.total_generation_time += generation_time_ms
            
            logger.info(f"✓ Successfully generated AI image for character: {character} "
                       f"(time: {generation_time_ms}ms, size: {len(result.generated_image_base64)} chars)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in AI image generation for character {character}: {e}", exc_info=True)
            
            return AIGenerationResult(
                success=False,
                error_message=str(e),
                generation_metadata={
                    'character': character,
                    'generation_time_ms': int((time.time() - start_time) * 1000),
                    'error_occurred': True
                }
            )
    
    async def _ensure_models_loaded(self):
        """
        Обеспечивает загрузку AI моделей.
        
        Raises:
            RuntimeError: Если загрузка моделей не удалась
        """
        async with self._model_loading_lock:
            if self._models_loaded:
                return
            
            try:
                logger.info("Loading AI models...")
                load_start = time.time()
                
                # Инициализируем Model Loader
                self.model_loader = ModelLoader()
                
                # Загружаем Stable Diffusion XL
                await self.model_loader.load_stable_diffusion_xl(self.config.base_model)
                
                # UPDATED: Load single union ControlNet model
                controlnets = await self.model_loader.load_controlnet_models(self.config.controlnet_models)
                
                # Настраиваем Multi-ControlNet pipeline
                pipeline_config = PipelineConfig(
                    base_model=self.config.base_model,
                    controlnet_models=self.config.controlnet_models,
                    device=self.config.device,
                    memory_efficient=self.config.memory_efficient,
                    enable_attention_slicing=self.config.enable_attention_slicing,
                    enable_cpu_offload=self.config.enable_cpu_offload
                )
                
                self.pipeline = MultiControlNetPipeline(pipeline_config)
                await self.pipeline.setup_pipeline()
                
                # Проверяем что pipeline готов
                if not self.pipeline.is_ready():
                    raise RuntimeError("Pipeline setup failed")
                
                load_time = time.time() - load_start
                self._models_loaded = True
                
                logger.info(f"✓ All AI models loaded successfully in {load_time:.1f}s")
                
                # Логируем статистику моделей
                model_status = self.model_loader.get_model_status()
                loaded_count = sum(1 for status in model_status.values() if status.loaded)
                total_count = len(model_status)
                logger.info(f"Model status: {loaded_count}/{total_count} loaded")
                
            except Exception as e:
                logger.error(f"Failed to load AI models: {e}")
                self._models_loaded = False
                raise RuntimeError(f"Model loading failed: {e}")
    
    async def _preprocess_character(
        self, 
        character: str, 
        width: int, 
        height: int
    ) -> Image.Image:
        """
        Предобработка иероглифа - рендеринг в изображение.
        
        Args:
            character: Иероглиф для рендеринга
            width: Ширина изображения
            height: Высота изображения
            
        Returns:
            Image.Image: Отрендеренное изображение иероглифа
        """
        try:
            # Используем ImageProcessor для рендеринга с автоподбором шрифта
            image = await self.image_processor.create_image(width, height, (255, 255, 255))
            
            # Добавляем иероглиф с автоподбором размера
            margin = min(width, height) // 10
            max_text_width = width - 2 * margin
            max_text_height = height - 2 * margin
            
            image, font_size = await self.image_processor.add_auto_fit_text(
                image=image,
                text=character,
                max_width=max_text_width,
                max_height=max_text_height,
                initial_font_size=min(width, height),
                text_color=(0, 0, 0),
                center_horizontal=True,
                center_vertical=True
            )
            
            logger.info(f"Rendered character '{character}' with font size {font_size}")
            return image
            
        except Exception as e:
            logger.error(f"Error preprocessing character {character}: {e}")
            raise RuntimeError(f"Character preprocessing failed: {e}")
    
    async def _generate_all_conditioning(
        self,
        base_image: Image.Image,
        character: str,
    ) -> Dict[str, Dict[str, Image.Image]]:
        """
        Генерирует все типы conditioning изображений.
        
        Args:
            base_image: Базовое изображение иероглифа
            character: Исходный иероглиф
            
        Returns:
            Dict[str, Dict[str, Image.Image]]: Conditioning изображения
        """
        
        try:
            # Генерируем все типы conditioning параллельно
            tasks = []
            
            # Выбираем случайный метод для разнообразия
            conditioning_type = random.choice(list(self.conditioning_generators.keys()))
            generator = self.conditioning_generators[conditioning_type]
            method = random.choice(generator.get_available_methods())

            conditioning_images = {
                conditioning_type: {
                    method: None
                }
            }
            
            logger.debug(f"Generating {conditioning_type} conditioning with method: {method}")
            
            # Создаем задачу для генерации
            task = asyncio.create_task(
                generator.generate_from_image(base_image, method=method),
                name=f"conditioning_{conditioning_type}_{method}"
            )
            tasks.append((conditioning_type, method, task))
            
            # Ожидаем завершения всех задач
            for conditioning_type, method, task in tasks:
                try:
                    result = await task
                    if result.success and result.image:
                        conditioning_images[conditioning_type][method] = result.image
                        logger.debug(f"✓ Generated {conditioning_type} conditioning "
                                   f"(method: {result.method_used}, "
                                   f"time: {result.processing_time_ms}ms)")
                    else:
                        logger.warning(f"Failed to generate {conditioning_type} conditioning {method}: "
                                     f"{result.error_message}")
                        conditioning_images[conditioning_type][method] = None
                        
                except Exception as e:
                    logger.error(f"Error generating {conditioning_type} conditioning {method}: {e}")
                    conditioning_images[conditioning_type][method] = None
            
            # Проверяем что хотя бы один conditioning тип сгенерирован
            valid_conditioning = {
                k: v for k, v in conditioning_images.items() 
                if any(img is not None for img in v.values())
            }
            
            if not valid_conditioning:
                raise RuntimeError("No conditioning images could be generated")
            
            logger.info(f"✓ Generated conditioning images for: {list(valid_conditioning.keys())}")
            return conditioning_images
            
        except Exception as e:
            logger.error(f"Error in conditioning generation: {e}")
            raise RuntimeError(f"Conditioning generation failed: {e}")
    
    async def _generate_prompt(
        self,
        character: str,
        translation: str
    ) -> PromptResult:
        """
        Строит промпт для AI генерации.
        
        Args:
            character: Иероглиф
            translation: Перевод
            
        Returns:
            PromptResult: Результат построения промпта
        """
        try:
            prompt_builder = PromptBuilder()
            
            # Выбираем случайный стиль для разнообразия
            available_styles = prompt_builder.style_definitions.get_style_names()
            style = random.choice(available_styles)
            
            prompt_result = await prompt_builder.build_prompt(
                character=character,
                translation=translation,
                style=style
            )
            
            if not prompt_result.success:
                raise RuntimeError(f"Prompt building failed: {prompt_result.error_message}")
            
            logger.debug(f"Built prompt for {character} (style: {style}): '{prompt_result.main_prompt[:100]}...'")
            return prompt_result
            
        except Exception as e:
            logger.error(f"Error building prompt: {e}")
            raise RuntimeError(f"Prompt generation failed: {e}")
    
    async def _run_ai_generation(
        self,
        prompt: str,
        conditioning_images: Dict[str, Dict[str, Image.Image]],
        conditioning_weights: Dict[str, float],
        seed: Optional[int] = None,
        **generation_params
    ) -> Image.Image:
        """
        Запускает AI генерацию с Multi-ControlNet.
        
        Args:
            prompt: Промпт для генерации
            conditioning_images: Conditioning изображения
            conditioning_weights: Веса conditioning
            seed: Seed для воспроизводимости
            **generation_params: Дополнительные параметры
            
        Returns:
            Image.Image: Сгенерированное изображение
        """
        try:
            if not self.pipeline or not self.pipeline.is_ready():
                raise RuntimeError("Pipeline not ready for generation")
            
            # Подготавливаем conditioning изображения для pipeline
            control_images = {}
            used_weights = {}
            
            for control_type, weight in conditioning_weights.items():
                if control_type in conditioning_images:
                    type_images = conditioning_images[control_type]
                    # Берем первое доступное изображение для этого типа
                    for method, image in type_images.items():
                        if image is not None:
                            control_images[control_type] = image
                            used_weights[control_type] = weight
                            break
            
            if not control_images:
                raise RuntimeError("No valid conditioning images available for generation")
            
            logger.debug(f"Using conditioning: {list(control_images.keys())} with weights: {used_weights}")
            
            # Настраиваем параметры генерации
            gen_params = {
                'num_inference_steps': generation_params.get('num_inference_steps', self.config.num_inference_steps),
                'guidance_scale': generation_params.get('guidance_scale', self.config.guidance_scale),
                'width': generation_params.get('width', self.config.width),
                'height': generation_params.get('height', self.config.height),
            }
            
            logger.debug(f"Generation parameters: {gen_params}")
            
            # Запускаем AI генерацию
            result_image = await self.pipeline.generate(
                prompt=prompt,
                control_images=control_images,
                seed=seed,
                **gen_params
            )
            
            logger.debug(f"✓ AI generation completed successfully")
            return result_image
            
        except Exception as e:
            logger.error(f"Error in AI generation: {e}")
            raise RuntimeError(f"AI generation failed: {e}")
    
    def _to_base64(self, image: Image.Image) -> str:
        """Конвертирует изображение в base64"""
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _conditioning_to_base64(self, conditioning_images: Dict[str, Dict[str, Image.Image]]) -> Dict[str, Dict[str, str]]:
        """Конвертирует conditioning изображения в base64"""
        result = {}
        for cond_type, cond_data in conditioning_images.items():
            result[cond_type] = {}
            for method, image in cond_data.items():
                result[cond_type][method] = self._to_base64(image) if image is not None else None
        return result
    
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
                "models_loaded": self._models_loaded,
                "pipeline_ready": self.pipeline.is_ready() if self.pipeline else False,
                "generation_count": self.generation_count,
                "total_generation_time_ms": self.total_generation_time,
                "average_generation_time_ms": avg_generation_time,
                "uptime_seconds": uptime_seconds,
                "available_conditioning_types": list(self.conditioning_generators.keys()),
                "controlnet_model": "union",  # UPDATED: Single union model
            }
            
            # Добавляем статистику моделей если доступно
            if self.model_loader:
                model_status = self.model_loader.get_model_status()
                status["model_status"] = {
                    name: {
                        "loaded": status.loaded,
                        "memory_usage_mb": status.memory_usage_mb,
                        "load_time_seconds": status.load_time_seconds
                    }
                    for name, status in model_status.items()
                }
                
                status["total_memory_usage"] = self.model_loader.get_total_memory_usage()
            
            # Добавляем статистику pipeline если доступно
            if self.pipeline:
                status["pipeline_stats"] = self.pipeline.get_generation_stats()
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting generation status: {e}")
            return {"error": str(e)}
    
    async def cleanup(self):
        """Очищает ресурсы генератора."""
        try:
            logger.info("Cleaning up AI Image Generator...")
            
            if self.pipeline:
                await self.pipeline.unload_pipeline()
                self.pipeline = None
            
            if self.model_loader:
                await self.model_loader.unload_all_models()
                self.model_loader = None
            
            self._models_loaded = False
            
            logger.info("✓ AI Image Generator cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            