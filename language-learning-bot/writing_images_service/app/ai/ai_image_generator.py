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
import logging
import io
import base64

from app.utils.logger import get_module_logger
from app.utils.image_utils import get_image_processor
from app.ai.conditioning.canny_conditioning import CannyConditioning
from app.ai.conditioning.depth_conditioning import DepthConditioning
from app.ai.conditioning.segmentation_conditioning import SegmentationConditioning
from app.ai.conditioning.scribble_conditioning import ScribbleConditioning

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
    
    # Кэширование
    enable_model_cache: bool = True
    enable_conditioning_cache: bool = True
    
    def __post_init__(self):
        """Инициализация значений по умолчанию"""
        if self.controlnet_models is None:
            self.controlnet_models = {
                "canny": "diffusers/controlnet-canny-sdxl-1.0",
                "depth": "diffusers/controlnet-depth-sdxl-1.0", 
                "segmentation": "diffusers/controlnet-seg-sdxl-1.0",
                "scribble": "diffusers/controlnet-scribble-sdxl-1.0"
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
    generated_image: Optional[Image.Image] = None
    generated_image_base64: Optional[str] = None
    
    # Промежуточные результаты
    conditioning_images: Optional[Dict[str, Image.Image]] = None
    conditioning_images_base64: Optional[Dict[str, str]] = None
    
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
        
        # Multi-ControlNet pipeline (будет инициализирован позже)
        self.pipeline = None
        self._models_loaded = False
        self._model_loading_lock = asyncio.Lock()
        
        # Статистика
        self.generation_count = 0
        self.total_generation_time = 0
        self.start_time = time.time()
        
        logger.info("AIImageGenerator initialized")
    
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
            style: Стиль генерации (comic, watercolor, realistic, anime)
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
            if not self._models_loaded:
                await self._ensure_models_loaded()
            
            # Настраиваем параметры
            weights = conditioning_weights or self.config.conditioning_weights
            methods = conditioning_methods or {
                "canny": "opencv_canny",
                "depth": "stroke_thickness_depth", 
                "segmentation": "radical_segmentation",
                "scribble": "skeletonization_scribble"
            }
            
            # 1. Предобработка - рендеринг иероглифа
            base_image = await self._preprocess_character(
                character, 
                self.config.width, 
                self.config.height
            )
            
            # 2. Генерация всех conditioning изображений
            conditioning_images = await self._generate_all_conditioning(
                base_image, character, methods
            )
            
            # 3. Построение промпта
            prompt, negative_prompt = await self._build_prompt(
                character, translation
            )
            
            # 4. AI генерация с Multi-ControlNet
            generated_image = await self._run_ai_generation(
                prompt=prompt,
                negative_prompt=negative_prompt,
                conditioning_images=conditioning_images,
                conditioning_weights=weights,
                seed=seed,
                **generation_params
            )
            
            # Подсчет времени генерации
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            # Создание результата
            result = AIGenerationResult(
                success=True,
                generated_image=final_image,
                generated_image_base64=self._to_base64(final_image) if final_image else None,
                conditioning_images=conditioning_images if include_conditioning_images else None,
                conditioning_images_base64=self._conditioning_to_base64(conditioning_images) if include_conditioning_images else None,
                prompt_used=prompt if include_prompt else None,
                generation_metadata={
                    'character': character,
                    'translation': translation,
                    'style': style,
                    'conditioning_weights_used': weights,
                    'conditioning_methods_used': methods,
                    'generation_time_ms': generation_time_ms,
                    'seed_used': seed,
                    'model_used': self.config.base_model,
                    'image_size': (self.config.width, self.config.height)
                }
            )
            
            # Обновляем статистику
            self.generation_count += 1
            self.total_generation_time += generation_time_ms
            
            logger.info(f"Successfully generated AI image for character: {character} "
                       f"(style: {style}, time: {generation_time_ms}ms)")
            
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
        """Обеспечивает загрузку AI моделей"""
        async with self._model_loading_lock:
            if self._models_loaded:
                return
            
            try:
                logger.info("Loading AI models...")
                
                # TODO: Загрузка Multi-ControlNet pipeline
                # from app.ai.multi_controlnet_pipeline import MultiControlNetPipeline
                # self.pipeline = MultiControlNetPipeline(
                #     model_name=self.config.base_model,
                #     controlnet_models=list(self.config.controlnet_models.values()),
                #     device=self.config.device,
                #     memory_efficient=self.config.memory_efficient
                # )
                # await self.pipeline.setup_pipeline()
                
                # Пока используем заглушку
                logger.info("AI models loading not implemented yet - using development mode")
                self.pipeline = None
                
                self._models_loaded = True
                logger.info("AI models loaded successfully")
                
            except Exception as e:
                logger.error(f"Failed to load AI models: {e}")
                raise
    
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
                initial_font_size=min(width, height) // 2,
                text_color=(0, 0, 0),
                center_horizontal=True,
                center_vertical=True
            )
            
            logger.debug(f"Rendered character '{character}' with font size {font_size}")
            return image
            
        except Exception as e:
            logger.error(f"Error preprocessing character {character}: {e}")
            raise
    
    async def _generate_all_conditioning(
        self,
        base_image: Image.Image,
        character: str,
        methods: Dict[str, str]
    ) -> Dict[str, Image.Image]:
        """
        Генерирует все типы conditioning изображений.
        
        Args:
            base_image: Базовое изображение иероглифа
            character: Исходный иероглиф
            methods: Методы для каждого типа conditioning
            
        Returns:
            Dict[str, Image.Image]: Conditioning изображения
        """
        conditioning_images = {}
        
        try:
            # Генерируем все типы conditioning параллельно
            tasks = []
            
            for conditioning_type, generator in self.conditioning_generators.items():
                method = methods.get(conditioning_type, "default")
                
                # Создаем задачу для генерации
                task = asyncio.create_task(
                    generator.generate_from_image(base_image, method=method),
                    name=f"conditioning_{conditioning_type}"
                )
                tasks.append((conditioning_type, task))
            
            # Ожидаем завершения всех задач
            for conditioning_type, task in tasks:
                try:
                    result = await task
                    if result.success and result.image:
                        conditioning_images[conditioning_type] = result.image
                        logger.debug(f"Generated {conditioning_type} conditioning "
                                   f"(method: {result.method_used}, "
                                   f"quality: {result.quality_score:.2f})")
                    else:
                        logger.warning(f"Failed to generate {conditioning_type} conditioning: "
                                     f"{result.error_message}")
                        
                        # Создаем fallback изображение
                        conditioning_images[conditioning_type] = await self._create_fallback_conditioning(
                            base_image, conditioning_type
                        )
                        
                except Exception as e:
                    logger.error(f"Error generating {conditioning_type} conditioning: {e}")
                    conditioning_images[conditioning_type] = await self._create_fallback_conditioning(
                        base_image, conditioning_type
                    )
            
            logger.info(f"Generated {len(conditioning_images)} conditioning images for character: {character}")
            return conditioning_images
            
        except Exception as e:
            logger.error(f"Error in conditioning generation: {e}")
            # Возвращаем fallback conditioning для всех типов
            return await self._create_all_fallback_conditioning(base_image)
    
    async def _build_prompt(
        self,
        character: str,
        translation: str,
        style: str
    ) -> Tuple[str, str]:
        """
        Строит промпт для AI генерации.
        
        Args:
            character: Иероглиф
            translation: Перевод
            style: Стиль генерации
            
        Returns:
            Tuple[str, str]: (prompt, negative_prompt)
        """
        try:
            # TODO: Интеграция с системой промптов
            # from app.ai.prompt.prompt_builder import PromptBuilder
            # prompt_builder = PromptBuilder()
            # prompt, negative_prompt = await prompt_builder.build_prompt(
            #     character=character,
            #     translation=translation,
            #     style=style
            # )
            
            # Пока используем простые шаблоны
            style_templates = {
                "comic": f"A vibrant comic book style illustration of {translation or 'Chinese character'}, "
                        f"inspired by the character {character}, bold outlines, bright colors, pop art style",
                        
                "watercolor": f"A soft watercolor painting depicting {translation or 'Chinese character'}, "
                             f"with flowing brushstrokes inspired by {character}, delicate washes, artistic style",
                             
                "realistic": f"A detailed realistic illustration representing {translation or 'Chinese character'}, "
                            f"maintaining the essence of Chinese character {character}, photorealistic, natural lighting",
                            
                "anime": f"An anime-style artwork showing {translation or 'Chinese character'}, "
                        f"stylized after the Chinese character {character}, cell shading, bright colors, manga influence"
            }
            
            prompt = style_templates.get(style, style_templates["comic"])
            
            logger.debug(f"Built prompt for {character} ({style}): {prompt[:100]}...")
            return prompt
            
        except Exception as e:
            logger.error(f"Error building prompt: {e}")
            # Fallback промпт
            fallback_prompt = f"A beautiful illustration of {translation or character}, masterpiece, best quality"
            fallback_negative = "blurry, low quality, distorted"
            return fallback_prompt, fallback_negative
    
    async def _run_ai_generation(
        self,
        prompt: str,
        conditioning_images: Dict[str, Image.Image],
        conditioning_weights: Dict[str, float],
        seed: Optional[int] = None,
        **generation_params
    ) -> Image.Image:
        """
        Запускает AI генерацию с Multi-ControlNet.
        
        Args:
            prompt: Промпт для генерации
            negative_prompt: Негативный промпт
            conditioning_images: Conditioning изображения
            conditioning_weights: Веса conditioning
            seed: Seed для воспроизводимости
            **generation_params: Дополнительные параметры
            
        Returns:
            Image.Image: Сгенерированное изображение
        """
        try:
            if self.pipeline is None:
                # В development режиме создаем заглушку
                logger.info("AI pipeline not available, creating development placeholder")
                return await self._create_development_placeholder(
                    prompt, conditioning_images
                )
            
            # TODO: Реальная AI генерация
            # result = await self.pipeline.generate(
            #     prompt=prompt,
            #     negative_prompt=negative_prompt,
            #     control_images=conditioning_images,
            #     conditioning_scales=conditioning_weights,
            #     num_inference_steps=self.config.num_inference_steps,
            #     guidance_scale=self.config.guidance_scale,
            #     width=self.config.width,
            #     height=self.config.height,
            #     seed=seed,
            #     **generation_params
            # )
            # return result
            
            # Пока возвращаем заглушку
            return await self._create_development_placeholder(prompt, conditioning_images)
            
        except Exception as e:
            logger.error(f"Error in AI generation: {e}")
            raise
    
    # TODO - избавится от понятия fallback, все эти методы перенести каждый в свой блок обуславливания как метод по умолчанию
    async def _create_fallback_conditioning(
        self, 
        base_image: Image.Image, 
        conditioning_type: str
    ) -> Image.Image:
        """
        Создает fallback conditioning изображение.
        
        Args:
            base_image: Базовое изображение
            conditioning_type: Тип conditioning
            
        Returns:
            Image.Image: Fallback изображение
        """
        # Простые fallback методы
        img_array = np.array(base_image.convert('L'))
        
        if conditioning_type == "canny":
            # Простая детекция границ
            import cv2
            edges = cv2.Canny(img_array, 50, 150)
            return Image.fromarray(edges, mode='L').convert('RGB')
            
        elif conditioning_type == "depth":
            # Простая инверсия для имитации глубины
            depth = 255 - img_array
            return Image.fromarray(depth, mode='L').convert('RGB')
            
        elif conditioning_type == "segmentation":
            # Простая бинаризация
            _, binary = cv2.threshold(img_array, 127, 255, cv2.THRESH_BINARY)
            return Image.fromarray(binary, mode='L').convert('RGB')
            
        elif conditioning_type == "scribble":
            # Простая скелетизация
            from skimage import morphology
            binary = img_array < 127
            skeleton = morphology.skeletonize(binary)
            skeleton_img = (skeleton * 255).astype(np.uint8)
            return Image.fromarray(255 - skeleton_img, mode='L').convert('RGB')
        
        # Fallback - возвращаем исходное изображение
        return base_image
    
    # TODO - избавится от понятия fallback, все эти методы перенести каждый в свой блок обуславливания как метод по умолчанию
    async def _create_all_fallback_conditioning(
        self, 
        base_image: Image.Image
    ) -> Dict[str, Image.Image]:
        """Создает fallback conditioning для всех типов."""
        conditioning_images = {}
        
        for conditioning_type in self.conditioning_generators.keys():
            conditioning_images[conditioning_type] = await self._create_fallback_conditioning(
                base_image, conditioning_type
            )
        
        return conditioning_images
    
    async def _create_development_placeholder(
        self,
        prompt: str,
        conditioning_images: Dict[str, Image.Image]
    ) -> Image.Image:
        """
        Создает placeholder для development режима.
        
        Args:
            prompt: Промпт генерации
            conditioning_images: Conditioning изображения
            
        Returns:
            Image.Image: Placeholder изображение
        """
        # Создаем коллаж из conditioning изображений
        width, height = self.config.width, self.config.height
        
        # Создаем базовое изображение
        placeholder = await self.image_processor.create_image(width, height, (240, 240, 240))
        
        # Добавляем заголовок
        title_text = "AI Generated Image"
        placeholder, _ = await self.image_processor.add_auto_fit_text(
            placeholder, title_text, width - 40, 60, 
            initial_font_size=32, text_color=(60, 60, 60),
            center_horizontal=True, offset_y=-height//3
        )
        
        # Добавляем информацию о промпте
        prompt_text = f"Prompt: {prompt[:50]}..."
        placeholder, _ = await self.image_processor.add_auto_fit_text(
            placeholder, prompt_text, width - 40, 40,
            initial_font_size=16, text_color=(100, 100, 100),
            center_horizontal=True, offset_y=-height//6
        )
        
        # Добавляем conditioning preview
        if conditioning_images:
            cond_text = f"Conditioning: {', '.join(conditioning_images.keys())}"
            placeholder, _ = await self.image_processor.add_auto_fit_text(
                placeholder, cond_text, width - 40, 30,
                initial_font_size=14, text_color=(120, 120, 120),
                center_horizontal=True, offset_y=height//6
            )
        
        # Добавляем маркер development
        dev_text = "(Development Mode)"
        placeholder, _ = await self.image_processor.add_auto_fit_text(
            placeholder, dev_text, width - 40, 30,
            initial_font_size=18, text_color=(150, 150, 150),
            center_horizontal=True, offset_y=height//3
        )
        
        return placeholder
    
    def _to_base64(self, image: Image.Image) -> str:
        """Конвертирует изображение в base64"""
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _conditioning_to_base64(self, conditioning_images: Dict[str, Image.Image]) -> Dict[str, str]:
        """Конвертирует conditioning изображения в base64"""
        result = {}
        for cond_type, image in conditioning_images.items():
            result[cond_type] = self._to_base64(image)
        return result
