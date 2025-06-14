"""
Multi-ControlNet Pipeline для AI генерации изображений.
Интегрирует Stable Diffusion XL с Union ControlNet моделью.
"""

import time
import traceback
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass
from PIL import Image
import torch
import gc
from diffusers import AutoencoderKL, EulerAncestralDiscreteScheduler

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
            # UPDATED: Single Union ControlNet instead of 4 separate models
            self.controlnet_models = {
                "union": "xinsir/controlnet-union-sdxl-1.0"
            }


@dataclass
class GenerationParams:
    """Параметры генерации"""
    prompt: str
    width: int = 1024
    height: int = 1024
    seed: Optional[int] = None
    num_images_per_prompt: int = 1
    num_inference_steps: int = 30
    guidance_scale: float = 5.0
    eta: float = 0.0
    generator: Optional[torch.Generator] = None
    latents: Optional[torch.FloatTensor] = None
    callback_on_step_end: Optional[callable] = None


class MultiControlNetPipeline:
    """
    Multi-ControlNet pipeline для генерации изображений с Union ControlNet.
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
        
        logger.info(f"MultiControlNetPipeline initialized for Union ControlNet on device: {self.config.device}")
    
    async def setup_pipeline(self):
        """
        Настраивает и загружает все компоненты pipeline.
        
        Raises:
            RuntimeError: Если настройка pipeline не удалась
        """
        try:
            logger.info("Setting up Union ControlNet pipeline...")
            start_time = time.time()
            
            # Проверяем доступность GPU
            await self._check_device_availability()
            
            # Загружаем ControlNet модели
            await self._load_controlnets()
            
            # Загружаем основной pipeline
            await self._load_base_pipeline()
            
            # # Применяем оптимизации
            # await self._apply_optimizations()
            
            self._is_loaded = True
            setup_time = time.time() - start_time
            
            logger.info(f"Union ControlNet pipeline setup completed in {setup_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to setup Union ControlNet pipeline: {e}")
            raise RuntimeError(f"Pipeline setup failed: {e}")
    
    async def generate(
        self,
        prompt: str,
        control_images: Dict[str, Image.Image] = None,
        **generation_params
    ) -> Image.Image:
        """
        Генерирует изображение с Union ControlNet conditioning.
        
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
            
            # Подготавливаем conditioning для Union ControlNet
            prepared_controls = await self._prepare_union_control_inputs(
                control_images or {}, 
            )
            
            # Настраиваем генератор для seed
            generator = self._setup_generator(params.seed)
            
            # Мониторинг памяти
            memory_before = self._get_memory_usage()
            
            # Основная генерация с Union ControlNet
            result_image = await self._run_union_inference(params, prepared_controls, generator)
            
            # Статистика
            inference_time = time.time() - start_time
            memory_after = self._get_memory_usage()
            
            self._update_stats(inference_time, memory_before, memory_after)
            
            logger.info(f"Generated image with Union ControlNet in {inference_time:.2f}s "
                       f"(GPU memory: {memory_before:.1f}MB -> {memory_after:.1f}MB)")
            
            return result_image
            
        except Exception as e:
            logger.error(f"Error in Union ControlNet generation: {e}")
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
        Загружает Union ControlNet модель.
        
        Raises:
            RuntimeError: Если загрузка критичных моделей не удалась
        """
        try:
            logger.info("Loading Union ControlNet model...")
            
            # FIXED: Используем оригинальный класс Union ControlNet
            try:
                from app.ai.models.controlnet_union import ControlNetModel_Union
                logger.info("Using ControlNetModel_Union (original class)")
                controlnet_class = ControlNetModel_Union
            except ImportError as e:
                logger.error(f"ControlNetModel_Union not available: {e}")
                logger.error(traceback.format_exc())
                raise RuntimeError("ControlNetModel_Union import failed")
            
            model_name = self.config.controlnet_models["union"]
            logger.info(f"Loading Union ControlNet: {model_name}")
            
            try:
                controlnet = controlnet_class.from_pretrained(
                    model_name,
                    # torch_dtype=self._torch_dtype,
                    torch_dtype=torch.float16, 
                    use_safetensors=True
                )
                # controlnet_model = ControlNetModel_Union.from_pretrained(
                # "xinsir/controlnet-union-sdxl-1.0", 
                # torch_dtype=torch.float16, 
                # use_safetensors=True)

                
                controlnet = controlnet.to(self._device)
                self.controlnets["union"] = controlnet
                
                logger.info(f"✓ Loaded Union ControlNet successfully")
                
            except Exception as e:
                logger.error(f"✗ Failed to load Union ControlNet: {e}")
                raise RuntimeError(f"Failed to load Union ControlNet: {e}")
            
            if not self.controlnets:
                raise RuntimeError("No ControlNet models loaded")
            
            logger.info("Union ControlNet model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Union ControlNet model: {e}")
            raise
    
    async def _load_base_pipeline(self):
        """
        Загружает основной Stable Diffusion pipeline с Union ControlNet.
        
        Raises:
            RuntimeError: Если загрузка pipeline не удалась
        """
        try:
            logger.info(f"Loading Union ControlNet pipeline: {self.config.base_model}")
            
            # FIXED: Используем оригинальный Union ControlNet pipeline
            try:
                from app.ai.pipeline.pipeline_controlnet_union_sd_xl import StableDiffusionXLControlNetUnionPipeline
                pipeline_class = StableDiffusionXLControlNetUnionPipeline
                logger.info("Using StableDiffusionXLControlNetUnionPipeline (original class)")
            except ImportError as e:
                logger.error(f"StableDiffusionXLControlNetUnionPipeline not available: {e}")
                logger.error(traceback.format_exc())
                raise RuntimeError("StableDiffusionXLControlNetUnionPipeline import failed")
            
            # Получаем Union ControlNet
            union_controlnet = self.controlnets["union"]
            
            eulera_scheduler = EulerAncestralDiscreteScheduler.from_pretrained("stabilityai/stable-diffusion-xl-base-1.0", subfolder="scheduler")
            vae = AutoencoderKL.from_pretrained("madebyollin/sdxl-vae-fp16-fix", torch_dtype=torch.float16)

            logger.debug(f"self._torch_dtype={self._torch_dtype}")

            # Создаем Union ControlNet pipeline
            self.pipeline = pipeline_class.from_pretrained(
                self.config.base_model,
                controlnet=union_controlnet,
                # torch_dtype=self._torch_dtype,
                # use_safetensors=True,
                # variant="fp16" if self._torch_dtype == torch.float16 else None
                vae=vae,
                torch_dtype=torch.float16,
                scheduler=eulera_scheduler,
            )

            self.pipeline = self.pipeline.to(self._device)

#             pipe = StableDiffusionXLControlNetUnionPipeline.from_pretrained(
#     "stabilityai/stable-diffusion-xl-base-1.0", 
#     controlnet=controlnet_model, 
#     vae=vae,
#     torch_dtype=torch.float16,
#     scheduler=eulera_scheduler,
# )

            
            # Настраиваем scheduler
            from diffusers import DPMSolverMultistepScheduler
            self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipeline.scheduler.config
            )
            
            # Перемещаем на устройство
            if not self.config.enable_cpu_offload:
                self.pipeline = self.pipeline.to(self._device)
            
            logger.info("✓ Union ControlNet pipeline loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Union ControlNet pipeline: {e}")
            raise RuntimeError(f"Failed to load Union ControlNet pipeline: {e}")
    
    async def _apply_optimizations(self):
        """
        Применяет оптимизации для экономии памяти и ускорения.
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
            
            # Отключаем safety checker если не нужен
            if not self.config.enable_safety_checker:
                self.pipeline.safety_checker = None
                self.pipeline.requires_safety_checker = False
                logger.debug("✓ Disabled safety checker")
            
            logger.info("Pipeline optimizations applied successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply optimizations: {e}")
            logger.warning("Continuing without some optimizations")
    
    async def _prepare_union_control_inputs(
        self,
        control_images: Dict[str, Image.Image],
    ) -> Dict[str, Any]:
        """
        Подготавливает control inputs для Union ControlNet.
        Использует формат из документации: image_list и union_control_type.
        
        Args:
            control_images: Conditioning изображения
            conditioning_scales: Веса conditioning
            
        Returns:
            Dict[str, Any]: Подготовленные control inputs для Union ControlNet
        """
        # FIXED: Используем правильный формат для Union ControlNet
        # Порядок согласно документации: [openpose, depth, hed/scribble, canny, normal, segment]
        control_type_mapping = {
            "openpose": 0,
            "depth": 1,
            "scribble": 2,  # hed/pidi/scribble/ted
            "canny": 3,     # canny/lineart/anime_lineart/mlsd
            "normal": 4,
            "segment": 5    # segmentation
        }
        
        # Маппинг наших типов к Union ControlNet типам
        our_to_union_mapping = {
            "depth": "depth",
            "canny": "canny", 
            "segmentation": "segment",
            "scribble": "scribble"
        }
        
        # Инициализация массивов для Union ControlNet
        image_list = [torch.zeros(1)] * 6  # 6 слотов для всех типов
        union_control_type = torch.zeros(6)  # Тензор флагов
        
        used_types = []
        
        # Заполняем доступные изображения
        for our_type, image in control_images.items():
            if our_type in our_to_union_mapping:
                union_type = our_to_union_mapping[our_type]
                if union_type in control_type_mapping:
                    idx = control_type_mapping[union_type]
                    
                    # Приводим изображение к нужному размеру
                    if image.size != (1024, 1024):
                        image = image.resize((1024, 1024), Image.Resampling.LANCZOS)
                    
                    image_list[idx] = image
                    union_control_type[idx] = 1.0  # Активируем этот тип
                    used_types.append(union_type)
        
        prepared_controls = {
            'image_list': image_list,
            'union_control_type': union_control_type,
            'used_types': used_types
        }
        
        logger.debug(f"Prepared Union ControlNet with types: {used_types}")
        logger.debug(f"Union control type tensor: {union_control_type}")
        
        return prepared_controls
    
    def _setup_generator(self, seed: Optional[int]) -> Optional[torch.Generator]:
        """Настраивает генератор для воспроизводимости."""
        if seed is not None:
            generator = torch.Generator(device=self._device)
            generator.manual_seed(seed)
            logger.debug(f"Set random seed: {seed}")
            return generator
        return None
    
    async def _run_union_inference(
        self,
        params: GenerationParams,
        prepared_controls: Dict[str, Any],
        generator: Optional[torch.Generator]
    ) -> Image.Image:
        """
        Выполняет AI генерацию с Union ControlNet.
        Использует правильный API согласно документации.
        
        Args:
            params: Параметры генерации
            prepared_controls: Подготовленные control inputs
            generator: Генератор для seed
            
        Returns:
            Image.Image: Сгенерированное изображение
        """
        try:
            logger.debug(f"Running Union ControlNet inference with prompt: '{params.prompt[:50]}...'")
            
            # FIXED: Используем правильный API для Union ControlNet
            pipeline_args = {
                "prompt": [params.prompt],  # Список промптов
                "width": params.width,
                "height": params.height,
                "generator": generator,
                "crops_coords_top_left": (0, 0),
                "target_size": (params.width, params.height),
                "original_size": (params.width * 2, params.height * 2),
                "num_inference_steps": params.num_inference_steps,
                "guidance_scale": params.guidance_scale,
            }
            
            # Добавляем Union ControlNet параметры согласно документации
            if any(prepared_controls['union_control_type']):
                pipeline_args.update({
                    "image_list": prepared_controls['image_list'],
                    "union_control": True,
                    "union_control_type": prepared_controls['union_control_type'],
                })
                
                logger.debug(f"Union ControlNet active types: {prepared_controls['used_types']}")
            
            logger.info(f"pipeline_args={pipeline_args.keys()}")
            logger.info(f"pipeline_args[guidance_scale]={pipeline_args['guidance_scale']}")

            # Запускаем генерацию
            with torch.no_grad():
                result = self.pipeline(**pipeline_args)
            
            # Возвращаем первое изображение
            generated_image = result.images[0]
            
            logger.debug("✓ Union ControlNet inference completed successfully")
            return generated_image
            
        except Exception as e:
            logger.error(f"Error in Union ControlNet inference: {e}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Union ControlNet inference failed: {e}")
    
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
            logger.info("Unloading Union ControlNet pipeline...")
            
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
            logger.info("Union ControlNet pipeline unloaded successfully")
            
        except Exception as e:
            logger.error(f"Error unloading pipeline: {e}")
    
    def is_ready(self) -> bool:
        """Проверяет готовность pipeline к генерации."""
        return self._is_loaded and self.pipeline is not None
    
    def get_supported_controlnet_types(self) -> List[str]:
        """Возвращает поддерживаемые типы ControlNet."""
        return ["canny", "depth", "segmentation", "scribble"]
    
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
            "available_controlnets": ["union"],
            "controlnet_type": "union"
        }
    