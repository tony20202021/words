"""
Multi-ControlNet Pipeline для AI генерации изображений.
Интегрирует Stable Diffusion XL с множественными ControlNet моделями.
"""

import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass
from PIL import Image
import numpy as np
import logging
import torch
import gc

from app.utils.logger import get_module_logger

logger = get_module_logger(__name__)


@dataclass
class PipelineConfig:
    """Конфигурация Multi-ControlNet pipeline"""
    # Основная модель
    base_model: str = "stabilityai/stable-diffusion-xl-base-1.0"
    
    # ControlNet модели
    controlnet_models: Dict[str, str] = None
    
    # Устройство и оптимизации
    device: str = "cuda"
    torch_dtype: str = "float16"  # float16, float32, bfloat16
    memory_efficient: bool = True
    enable_attention_slicing: bool = True
    enable_cpu_offload: bool = False
    enable_model_cpu_offload: bool = False
    enable_sequential_cpu_offload: bool = False
    enable_vae_slicing: bool = False
    enable_vae_tiling: bool = False
    use_torch_compile: bool = True
    use_channels_last_memory_format: bool = True
    
    # Генерация
    max_batch_size: int = 4
    enable_safety_checker: bool = False
    
    def __post_init__(self):
        """Инициализация значений по умолчанию"""
        if self.controlnet_models is None:
            self.controlnet_models = {
                "canny": "diffusers/controlnet-canny-sdxl-1.0",
                "depth": "diffusers/controlnet-depth-sdxl-1.0",
                "segmentation": "diffusers/controlnet-seg-sdxl-1.0", 
                "scribble": "diffusers/controlnet-scribble-sdxl-1.0"
            }


@dataclass
class GenerationParams:
    """Параметры генерации"""
    prompt: str
    num_inference_steps: int = 30
    guidance_scale: float = 7.5
    width: int = 1024
    height: int = 1024
    seed: Optional[int] = None
    num_images_per_prompt: int = 1
    eta: float = 0.0
    generator: Optional[torch.Generator] = None
    latents: Optional[torch.FloatTensor] = None
    callback_on_step_end: Optional[callable] = None


class MultiControlNetPipeline:
    """
    Multi-ControlNet pipeline для генерации изображений с множественным conditioning.
    Поддерживает до 4 типов ControlNet одновременно.
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Инициализация Multi-ControlNet pipeline.
        
        Args:
            config: Конфигурация pipeline
        """
        self.config = config or PipelineConfig()
        
        # Pipeline компоненты
        self.pipeline = None
        self.controlnets = {}
        self.vae = None
        self.scheduler = None
        
        # Состояние
        self._is_loaded = False
        self._device = torch.device(self.config.device)
        self._torch_dtype = getattr(torch, self.config.torch_dtype)
        
        # Статистика
        self.generation_count = 0
        self.total_inference_time = 0
        self.memory_stats = []
        
        # Проверяем доступность CUDA
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA not available. GPU is required for Multi-ControlNet pipeline.")
        
        logger.info(f"MultiControlNetPipeline initialized for device: {self.config.device}")
    
    async def setup_pipeline(self):
        """
        Настраивает и загружает все компоненты pipeline.
        
        Raises:
            RuntimeError: Если настройка pipeline не удалась
        """
        try:
            logger.info("Setting up Multi-ControlNet pipeline...")
            start_time = time.time()
            
            # Проверяем доступность GPU
            await self._check_device_availability()
            
            # Загружаем ControlNet модели
            await self._load_controlnets()
            
            # Загружаем основной pipeline
            await self._load_base_pipeline()
            
            # Применяем оптимизации
            await self._apply_optimizations()
            
            self._is_loaded = True
            setup_time = time.time() - start_time
            
            logger.info(f"Multi-ControlNet pipeline setup completed in {setup_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to setup Multi-ControlNet pipeline: {e}")
            raise RuntimeError(f"Pipeline setup failed: {e}")
    
    async def generate(
        self,
        prompt: str,
        control_images: Dict[str, Image.Image] = None,
        conditioning_scales: Dict[str, float] = None,
        **generation_params
    ) -> Image.Image:
        """
        Генерирует изображение с Multi-ControlNet conditioning.
        
        Args:
            prompt: Текстовый промпт
            control_images: Словарь conditioning изображений по типам
            conditioning_scales: Веса conditioning для каждого типа
            **generation_params: Дополнительные параметры генерации
            
        Returns:
            Image.Image: Сгенерированное изображение
            
        Raises:
            RuntimeError: Если генерация не удалась
        """
        if not self._is_loaded:
            raise RuntimeError("Pipeline not loaded. Call setup_pipeline() first.")
        
        start_time = time.time()
        
        try:
            # Подготавливаем параметры
            params = GenerationParams(
                prompt=prompt,
                **generation_params
            )
            
            # Подготавливаем conditioning
            prepared_controls = await self._prepare_control_inputs(
                control_images or {}, 
                conditioning_scales or {}
            )
            
            # Настраиваем генератор для seed
            generator = self._setup_generator(params.seed)
            
            # Мониторинг памяти
            memory_before = self._get_memory_usage()
            
            # Основная генерация
            result_image = await self._run_inference(params, prepared_controls, generator)
            
            # Статистика
            inference_time = time.time() - start_time
            memory_after = self._get_memory_usage()
            
            self._update_stats(inference_time, memory_before, memory_after)
            
            logger.info(f"Generated image in {inference_time:.2f}s "
                       f"(GPU memory: {memory_before:.1f}MB -> {memory_after:.1f}MB)")
            
            return result_image
            
        except Exception as e:
            logger.error(f"Error in Multi-ControlNet generation: {e}")
            raise RuntimeError(f"Generation failed: {e}")
        finally:
            # Очистка памяти
            await self._cleanup_memory()
    
    async def _check_device_availability(self):
        """Проверяет доступность GPU и настраивает устройство."""
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA not available")
        
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
        logger.info(f"Using GPU with {gpu_memory:.1f}GB memory")
        
        # Настраиваем оптимизации для GPU памяти
        if gpu_memory < 12:  # Меньше 12GB
            self.config.memory_efficient = True
            self.config.enable_attention_slicing = True
            self.config.enable_cpu_offload = True
            logger.info("Enabled memory optimizations for GPU < 12GB")
        elif gpu_memory >= 80:  # 80GB+ - минимальные оптимизации
            self.config.memory_efficient = False
            self.config.enable_attention_slicing = False
            self.config.max_batch_size = 4
            logger.info("Configured for high-memory GPU (80GB+)")
        
        logger.info(f"Using device: {self._device}")
    
    async def _load_controlnets(self):
        """
        Загружает все ControlNet модели.
        
        Raises:
            RuntimeError: Если загрузка критичных моделей не удалась
        """
        try:
            logger.info("Loading ControlNet models...")
            
            from diffusers import ControlNetModel
            
            for control_type, model_name in self.config.controlnet_models.items():
                logger.info(f"Loading {control_type} ControlNet: {model_name}")
                
                try:
                    controlnet = ControlNetModel.from_pretrained(
                        model_name,
                        torch_dtype=self._torch_dtype,
                        use_safetensors=True
                    )
                    
                    controlnet = controlnet.to(self._device)
                    self.controlnets[control_type] = controlnet
                    
                    logger.info(f"✓ Loaded {control_type} ControlNet")
                    
                except Exception as e:
                    logger.error(f"✗ Failed to load {control_type} ControlNet: {e}")
                    raise RuntimeError(f"Failed to load {control_type} ControlNet: {e}")
            
            if not self.controlnets:
                raise RuntimeError("No ControlNet models loaded")
            
            logger.info(f"Loaded {len(self.controlnets)} ControlNet models")
            
        except Exception as e:
            logger.error(f"Failed to load ControlNet models: {e}")
            raise
    
    async def _load_base_pipeline(self):
        """
        Загружает основной Stable Diffusion pipeline.
        
        Raises:
            RuntimeError: Если загрузка pipeline не удалась
        """
        try:
            logger.info(f"Loading base pipeline: {self.config.base_model}")
            
            from diffusers import StableDiffusionXLControlNetPipeline, MultiControlNetModel
            
            # Объединяем все ControlNet в MultiControlNet
            if len(self.controlnets) > 1:
                multi_controlnet = MultiControlNetModel(list(self.controlnets.values()))
                logger.info(f"Created MultiControlNet with {len(self.controlnets)} models")
            else:
                multi_controlnet = list(self.controlnets.values())[0]
                logger.info("Using single ControlNet model")
            
            # Загружаем pipeline
            self.pipeline = StableDiffusionXLControlNetPipeline.from_pretrained(
                self.config.base_model,
                controlnet=multi_controlnet,
                torch_dtype=self._torch_dtype,
                use_safetensors=True,
                variant="fp16" if self._torch_dtype == torch.float16 else None
            )
            
            # Настраиваем scheduler
            from diffusers import DPMSolverMultistepScheduler
            self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipeline.scheduler.config
            )
            
            # Перемещаем на устройство
            if not self.config.enable_cpu_offload:
                self.pipeline = self.pipeline.to(self._device)
            
            logger.info("✓ Base pipeline loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load base pipeline: {e}")
            raise RuntimeError(f"Failed to load base pipeline: {e}")
    
    async def _apply_optimizations(self):
        """
        Применяет оптимизации для экономии памяти и ускорения.
        
        Raises:
            RuntimeError: Если критичные оптимизации не удались
        """
        try:
            logger.info("Applying pipeline optimizations...")
            
            # Attention slicing для экономии памяти
            if self.config.enable_attention_slicing:
                self.pipeline.enable_attention_slicing()
                logger.debug("✓ Enabled attention slicing")
            
            # CPU offload для экономии GPU памяти
            if self.config.enable_cpu_offload:
                self.pipeline.enable_model_cpu_offload()
                logger.debug("✓ Enabled model CPU offload")
            elif self.config.enable_sequential_cpu_offload:
                self.pipeline.enable_sequential_cpu_offload()
                logger.debug("✓ Enabled sequential CPU offload")
            
            # VAE optimizations
            if self.config.enable_vae_slicing:
                self.pipeline.enable_vae_slicing()
                logger.debug("✓ Enabled VAE slicing")
            
            if self.config.enable_vae_tiling:
                self.pipeline.enable_vae_tiling()
                logger.debug("✓ Enabled VAE tiling")
            
            # Torch optimizations
            if self.config.use_torch_compile and hasattr(torch, 'compile'):
                try:
                    self.pipeline.unet = torch.compile(self.pipeline.unet, mode="reduce-overhead")
                    logger.debug("✓ Enabled torch.compile for UNet")
                except Exception as e:
                    logger.warning(f"torch.compile failed: {e}")
            
            # Memory format optimization
            if self.config.use_channels_last_memory_format:
                try:
                    if hasattr(self.pipeline, 'unet'):
                        self.pipeline.unet.to(memory_format=torch.channels_last)
                    logger.debug("✓ Enabled channels_last memory format")
                except Exception as e:
                    logger.warning(f"channels_last failed: {e}")
            
            # Отключаем safety checker если не нужен
            if not self.config.enable_safety_checker:
                self.pipeline.safety_checker = None
                self.pipeline.requires_safety_checker = False
                logger.debug("✓ Disabled safety checker")
            
            logger.info("Pipeline optimizations applied successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply optimizations: {e}")
            # Оптимизации не критичны, продолжаем без них
            logger.warning("Continuing without some optimizations")
    
    async def _prepare_control_inputs(
        self,
        control_images: Dict[str, Image.Image],
        conditioning_scales: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Подготавливает control inputs для генерации.
        
        Args:
            control_images: Conditioning изображения
            conditioning_scales: Веса conditioning
            
        Returns:
            Dict[str, Any]: Подготовленные control inputs
        """
        prepared_controls = {
            'images': [],
            'scales': [],
            'types': []
        }
        
        # Проверяем доступные ControlNet
        available_types = list(self.controlnets.keys())
        
        for control_type in available_types:
            if control_type in control_images:
                image = control_images[control_type]
                scale = conditioning_scales.get(control_type, 1.0)
                
                # Приводим изображение к нужному размеру
                if image.size != (1024, 1024):
                    image = image.resize((1024, 1024), Image.Resampling.LANCZOS)
                
                prepared_controls['images'].append(image)
                prepared_controls['scales'].append(scale)
                prepared_controls['types'].append(control_type)
        
        logger.debug(f"Prepared {len(prepared_controls['images'])} control inputs: "
                    f"{prepared_controls['types']}")
        
        return prepared_controls
    
    def _setup_generator(self, seed: Optional[int]) -> Optional[torch.Generator]:
        """Настраивает генератор для воспроизводимости."""
        if seed is not None:
            generator = torch.Generator(device=self._device)
            generator.manual_seed(seed)
            logger.debug(f"Set random seed: {seed}")
            return generator
        return None
    
    async def _run_inference(
        self,
        params: GenerationParams,
        prepared_controls: Dict[str, Any],
        generator: Optional[torch.Generator]
    ) -> Image.Image:
        """
        Выполняет основную AI генерацию.
        
        Args:
            params: Параметры генерации
            prepared_controls: Подготовленные control inputs
            generator: Генератор для seed
            
        Returns:
            Image.Image: Сгенерированное изображение
            
        Raises:
            RuntimeError: Если генерация не удалась
        """
        try:
            logger.debug(f"Running inference with prompt: '{params.prompt[:50]}...'")
            
            # Подготавливаем аргументы для pipeline
            pipeline_args = {
                "prompt": params.prompt,
                "num_inference_steps": params.num_inference_steps,
                "guidance_scale": params.guidance_scale,
                "width": params.width,
                "height": params.height,
                "generator": generator,
                "num_images_per_prompt": params.num_images_per_prompt,
                "eta": params.eta,
            }
            
            # Добавляем control inputs если есть
            if prepared_controls['images']:
                pipeline_args["image"] = prepared_controls['images']
                pipeline_args["controlnet_conditioning_scale"] = prepared_controls['scales']
            
            # Добавляем callback если есть
            if params.callback_on_step_end:
                pipeline_args["callback_on_step_end"] = params.callback_on_step_end
            
            # Запускаем генерацию
            with torch.no_grad():
                result = self.pipeline(**pipeline_args)
            
            # Возвращаем первое изображение
            generated_image = result.images[0]
            
            logger.debug("✓ Inference completed successfully")
            return generated_image
            
        except Exception as e:
            logger.error(f"Error in inference: {e}")
            raise RuntimeError(f"Inference failed: {e}")
    
    def _get_memory_usage(self) -> float:
        """Возвращает использование GPU памяти в MB."""
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated() / 1024**2
        return 0.0
    
    def _update_stats(self, inference_time: float, memory_before: float, memory_after: float):
        """Обновляет статистику производительности."""
        self.generation_count += 1
        self.total_inference_time += inference_time
        
        stats = {
            "generation_id": self.generation_count,
            "inference_time": inference_time,
            "memory_before": memory_before,
            "memory_after": memory_after,
            "memory_diff": memory_after - memory_before
        }
        
        self.memory_stats.append(stats)
        
        # Сохраняем только последние 100 записей
        if len(self.memory_stats) > 100:
            self.memory_stats = self.memory_stats[-100:]
    
    async def _cleanup_memory(self):
        """Очищает GPU память после генерации."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
    
    async def unload_pipeline(self):
        """Выгружает pipeline для освобождения памяти."""
        try:
            logger.info("Unloading Multi-ControlNet pipeline...")
            
            # Очищаем компоненты
            if self.pipeline is not None:
                del self.pipeline
                self.pipeline = None
            
            for control_type in list(self.controlnets.keys()):
                if self.controlnets[control_type] is not None:
                    del self.controlnets[control_type]
                    self.controlnets[control_type] = None
            
            # Очищаем память
            await self._cleanup_memory()
            
            self._is_loaded = False
            logger.info("Pipeline unloaded successfully")
            
        except Exception as e:
            logger.error(f"Error unloading pipeline: {e}")
    
    async def reload_pipeline(self):
        """Перезагружает pipeline."""
        await self.unload_pipeline()
        await self.setup_pipeline()
    
    def is_ready(self) -> bool:
        """Проверяет готовность pipeline к генерации."""
        return self._is_loaded and self.pipeline is not None
    
    def get_supported_controlnet_types(self) -> List[str]:
        """Возвращает поддерживаемые типы ControlNet."""
        return list(self.config.controlnet_models.keys())
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """Возвращает статистику генерации."""
        if not self.memory_stats:
            return {}
        
        avg_time = self.total_inference_time / self.generation_count if self.generation_count > 0 else 0
        recent_stats = self.memory_stats[-10:] if len(self.memory_stats) >= 10 else self.memory_stats
        
        return {
            "total_generations": self.generation_count,
            "total_inference_time": self.total_inference_time,
            "average_inference_time": avg_time,
            "recent_memory_usage": [s["memory_after"] for s in recent_stats],
            "pipeline_loaded": self._is_loaded,
            "available_controlnets": list(self.controlnets.keys())
        }
    