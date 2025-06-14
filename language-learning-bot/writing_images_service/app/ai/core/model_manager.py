"""
Model Manager
Менеджер для загрузки и управления AI моделями.
"""

import time
import asyncio
from typing import Dict, Any, Optional
from PIL import Image

from app.utils.logger import get_module_logger
from app.ai.core.generation_config import AIGenerationConfig
from app.ai.multi_controlnet_pipeline import MultiControlNetPipeline, PipelineConfig
from app.ai.models.model_loader import ModelLoader

logger = get_module_logger(__name__)


class ModelManager:
    """
    Менеджер для загрузки и управления AI моделями (SDXL + Union ControlNet).
    """
    
    def __init__(self, config: AIGenerationConfig):
        """
        Инициализация Model Manager.
        
        Args:
            config: Конфигурация AI генерации
        """
        self.config = config
        self.model_loader: Optional[ModelLoader] = None
        self.pipeline: Optional[MultiControlNetPipeline] = None
        self._models_loaded = False
        self._model_loading_lock = asyncio.Lock()
        
        # Статистика
        self.generation_count = 0
        self.total_inference_time = 0
        self.start_time = time.time()
        
        logger.info("ModelManager initialized")
    
    async def ensure_models_loaded(self):
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
                
                # Загружаем Union ControlNet модель
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
    
    async def run_generation(
        self,
        prompt: str,
        conditioning_images: Dict[str, Dict[str, Image.Image]],
        seed: Optional[int] = None,
        **generation_params
    ) -> Image.Image:
        """
        Запускает AI генерацию с Multi-ControlNet.
        
        Args:
            prompt: Промпт для генерации
            conditioning_images: Conditioning изображения
            seed: Seed для воспроизводимости
            **generation_params: Дополнительные параметры
            
        Returns:
            Image.Image: Сгенерированное изображение
        """
        start_time = time.time()
        
        try:
            if not self.pipeline or not self.pipeline.is_ready():
                raise RuntimeError("Pipeline not ready for generation")
            
            # Подготавливаем conditioning изображения для pipeline
            control_images = {}
            
            # Берем первое доступное изображение для каждого типа conditioning
            for control_type, type_images in conditioning_images.items():
                for method, image in type_images.items():
                    if image is not None:
                        control_images[control_type] = image
                        break
            
            if not control_images:
                raise RuntimeError("No valid conditioning images available for generation")
            
            logger.debug(f"Using conditioning: {list(control_images.keys())}")
            
            # Настраиваем параметры генерации
            num_inference_steps = generation_params.get(
                'num_inference_steps', 
                self.config.num_inference_steps if hasattr(self.config, 'num_inference_steps') else 30
            )
            guidance_scale = generation_params.get(
                'guidance_scale', 
                self.config.guidance_scale if hasattr(self.config, 'guidance_scale') else 20.0
            )
            controlnet_conditioning_scale = generation_params.get(
                'controlnet_conditioning_scale', 
                self.config.controlnet_conditioning_scale if hasattr(self.config, 'controlnet_conditioning_scale') else 0.7
            )

            gen_params = {
                'num_inference_steps': num_inference_steps,
                'guidance_scale': guidance_scale,
                'controlnet_conditioning_scale': controlnet_conditioning_scale,
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
            
            # Обновляем статистику
            inference_time = time.time() - start_time
            self.generation_count += 1
            self.total_inference_time += inference_time
            
            logger.debug(f"✓ AI generation completed successfully in {inference_time:.2f}s")
            return result_image
            
        except Exception as e:
            logger.error(f"Error in AI generation: {e}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"AI generation failed: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Возвращает статус Model Manager"""
        uptime_seconds = int(time.time() - self.start_time)
        avg_inference_time = (
            self.total_inference_time / self.generation_count 
            if self.generation_count > 0 else 0
        )
        
        status = {
            "models_loaded": self._models_loaded,
            "pipeline_ready": self.pipeline.is_ready() if self.pipeline else False,
            "generation_count": self.generation_count,
            "total_inference_time_seconds": self.total_inference_time,
            "average_inference_time_seconds": avg_inference_time,
            "uptime_seconds": uptime_seconds,
            "controlnet_model": "union"
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
    
    async def cleanup(self):
        """Очищает ресурсы Model Manager"""
        try:
            logger.info("Cleaning up Model Manager...")
            
            if self.pipeline:
                await self.pipeline.unload_pipeline()
                self.pipeline = None
            
            if self.model_loader:
                await self.model_loader.unload_all_models()
                self.model_loader = None
            
            self._models_loaded = False
            
            logger.info("✓ Model Manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during model manager cleanup: {e}")
            