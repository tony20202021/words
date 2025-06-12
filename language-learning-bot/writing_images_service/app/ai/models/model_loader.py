"""
Model loader for AI image generation.
Загрузчик моделей для AI генерации изображений.
"""

import logging
import torch
import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

from transformers import CLIPImageProcessor, SiglipImageProcessor

@dataclass
class ModelStatus:
    """Статус загрузки модели"""
    loaded: bool
    model_name: str
    memory_usage_mb: float = 0.0
    load_time_seconds: float = 0.0
    error_message: Optional[str] = None


class ModelLoader:
    """
    Загрузчик AI моделей для генерации изображений.
    """
    
    def __init__(self):
        """Инициализация загрузчика моделей."""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.loaded_models = {}
        self.model_status = {}
        self._loading_lock = asyncio.Lock()
        
        # Проверяем доступность CUDA
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA not available. GPU is required for AI image generation.")
        
        # Проверяем доступность необходимых библиотек
        try:
            import diffusers
            import transformers
            import accelerate
        except ImportError as e:
            raise RuntimeError(f"Required AI libraries not installed: {e}")
        
        logger.info(f"ModelLoader initialized on device: {self.device}")
        logger.info(f"CUDA device: {torch.cuda.get_device_name()}")
        logger.info(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
    
    async def load_stable_diffusion_xl(
        self, 
        model_name: str = "stabilityai/stable-diffusion-xl-base-1.0"
    ):
        """
        Загружает Stable Diffusion XL модель.
        
        Args:
            model_name: Название модели на HuggingFace
            
        Returns:
            Загруженная модель
            
        Raises:
            RuntimeError: Если загрузка не удалась
        """
        async with self._loading_lock:
            if "stable_diffusion_xl" in self.loaded_models:
                return self.loaded_models["stable_diffusion_xl"]
            
            start_time = time.time()
            memory_before = self._get_memory_usage()
            
            try:
                logger.info(f"Loading Stable Diffusion XL: {model_name}")
                
                from diffusers import StableDiffusionXLPipeline
                
                # Загружаем с оптимизациями
                pipeline = StableDiffusionXLPipeline.from_pretrained(
                    model_name,
                    torch_dtype=torch.float16,
                    use_safetensors=True,
                    variant="fp16"
                )
                
                # Перемещаем на GPU
                pipeline = pipeline.to(self.device)
                
                # Применяем базовые оптимизации
                # pipeline.enable_memory_efficient_attention()
                pipeline.enable_xformers_memory_efficient_attention
                
                # Проверяем размер GPU памяти для дополнительных оптимизаций
                total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
                if total_memory < 24:  # Меньше 24GB
                    pipeline.enable_attention_slicing()
                    pipeline.enable_vae_slicing()
                    logger.info("Applied memory optimizations for smaller GPU")
                
                load_time = time.time() - start_time
                memory_after = self._get_memory_usage()
                memory_used = memory_after - memory_before
                
                self.loaded_models["stable_diffusion_xl"] = pipeline
                self.model_status["stable_diffusion_xl"] = ModelStatus(
                    loaded=True,
                    model_name=model_name,
                    memory_usage_mb=memory_used,
                    load_time_seconds=load_time
                )
                
                logger.info(f"Stable Diffusion XL loaded successfully in {load_time:.1f}s "
                           f"(Memory used: {memory_used:.1f}MB)")
                return pipeline
                    
            except Exception as e:
                logger.error(f"Failed to load Stable Diffusion XL: {e}")
                self.model_status["stable_diffusion_xl"] = ModelStatus(
                    loaded=False,
                    model_name=model_name,
                    error_message=str(e)
                )
                raise RuntimeError(f"Failed to load Stable Diffusion XL: {e}")
    
    async def load_controlnet_models(self, model_configs: Dict[str, str]):
        """
        Загружает ControlNet модели.
        
        Args:
            model_configs: Словарь {тип: модель_id}
            
        Returns:
            Словарь загруженных ControlNet моделей
            
        Raises:
            RuntimeError: Если загрузка критичных моделей не удалась
        """
        async with self._loading_lock:
            if "controlnets" in self.loaded_models:
                return self.loaded_models["controlnets"]
            
            controlnets = {}
            failed_models = []
            
            try:
                from diffusers import ControlNetModel
                
                # UPDATED: Handle Union ControlNet model
                if "union" in model_configs:
                    # Single Union ControlNet model
                    model_id = model_configs["union"]
                    start_time = time.time()
                    memory_before = self._get_memory_usage()
                    
                    try:
                        logger.info(f"Loading Union ControlNet: {model_id}")
                        
                        controlnet = ControlNetModel.from_pretrained(
                            model_id,
                            torch_dtype=torch.float16,
                            use_safetensors=True
                        )
                        
                        controlnet = controlnet.to(self.device)
                        
                        load_time = time.time() - start_time
                        memory_after = self._get_memory_usage()
                        memory_used = memory_after - memory_before
                        
                        controlnets["union"] = controlnet
                        self.model_status["controlnet_union"] = ModelStatus(
                            loaded=True,
                            model_name=model_id,
                            memory_usage_mb=memory_used,
                            load_time_seconds=load_time
                        )
                        
                        logger.info(f"Union ControlNet loaded in {load_time:.1f}s "
                                   f"(Memory: {memory_used:.1f}MB)")
                        
                    except Exception as e:
                        logger.error(f"Failed to load Union ControlNet: {e}")
                        failed_models.append("union")
                        self.model_status["controlnet_union"] = ModelStatus(
                            loaded=False,
                            model_name=model_id,
                            error_message=str(e)
                        )
                        raise RuntimeError(f"Failed to load Union ControlNet: {e}")
                        
                else:
                    # Fallback: Load separate ControlNet models
                    for control_type, model_id in model_configs.items():
                        start_time = time.time()
                        memory_before = self._get_memory_usage()
                        
                        try:
                            logger.info(f"Loading ControlNet {control_type}: {model_id}")
                            
                            controlnet = ControlNetModel.from_pretrained(
                                model_id,
                                torch_dtype=torch.float16,
                                use_safetensors=True
                            )
                            
                            controlnet = controlnet.to(self.device)
                            
                            load_time = time.time() - start_time
                            memory_after = self._get_memory_usage()
                            memory_used = memory_after - memory_before
                            
                            controlnets[control_type] = controlnet
                            self.model_status[f"controlnet_{control_type}"] = ModelStatus(
                                loaded=True,
                                model_name=model_id,
                                memory_usage_mb=memory_used,
                                load_time_seconds=load_time
                            )
                            
                            logger.info(f"ControlNet {control_type} loaded in {load_time:.1f}s "
                                       f"(Memory: {memory_used:.1f}MB)")
                            
                        except Exception as e:
                            logger.error(f"Failed to load ControlNet {control_type}: {e}")
                            failed_models.append(control_type)
                            self.model_status[f"controlnet_{control_type}"] = ModelStatus(
                                loaded=False,
                                model_name=model_id,
                                error_message=str(e)
                            )
                
                # Проверяем что хотя бы одна ControlNet модель загружена
                if not controlnets:
                    raise RuntimeError("No ControlNet models could be loaded")
                
                if failed_models:
                    logger.warning(f"Some ControlNet models failed to load: {failed_models}")
                
                self.loaded_models["controlnets"] = controlnets
                
                # UPDATED: Log for Union vs separate models
                if "union" in controlnets:
                    logger.info("Loaded Union ControlNet model successfully")
                else:
                    logger.info(f"Loaded {len(controlnets)} separate ControlNet models successfully")
                    
                return controlnets
                
            except Exception as e:
                logger.error(f"Critical error loading ControlNet models: {e}")
                raise RuntimeError(f"Failed to load ControlNet models: {e}")
    
    async def setup_multi_controlnet_pipeline(self, controlnets: Dict):
        """
        Настраивает Multi-ControlNet pipeline.
        
        Args:
            controlnets: Словарь загруженных ControlNet моделей
            
        Returns:
            Multi-ControlNet pipeline
            
        Raises:
            RuntimeError: Если настройка pipeline не удалась
        """
        try:
            if not controlnets:
                raise RuntimeError("No ControlNet models available for pipeline")
            
            from diffusers import StableDiffusionXLControlNetPipeline, MultiControlNetModel
            
            base_pipeline = self.loaded_models.get("stable_diffusion_xl")
            if not base_pipeline:
                raise RuntimeError("Base Stable Diffusion XL not loaded")
            
            start_time = time.time()
            logger.info("Setting up Multi-ControlNet pipeline...")
            
            # UPDATED: Handle Union ControlNet vs multiple separate models
            if "union" in controlnets:
                # Single Union ControlNet
                controlnet = controlnets["union"]
                logger.info("Using Union ControlNet model")
            else:
                # Multiple separate ControlNet models
                controlnet_list = list(controlnets.values())
                if len(controlnet_list) > 1:
                    controlnet = MultiControlNetModel(controlnet_list)
                    logger.info(f"Created MultiControlNet with {len(controlnet_list)} models")
                else:
                    controlnet = controlnet_list[0]
                    logger.info("Using single ControlNet model")
            
            # Создаем pipeline с ControlNet
            # Используем компоненты из уже загруженного base pipeline
            pipeline = StableDiffusionXLControlNetPipeline(
                vae=base_pipeline.vae,
                text_encoder=base_pipeline.text_encoder,
                text_encoder_2=base_pipeline.text_encoder_2,
                tokenizer=base_pipeline.tokenizer,
                tokenizer_2=base_pipeline.tokenizer_2,
                unet=base_pipeline.unet,
                controlnet=controlnet,
                scheduler=base_pipeline.scheduler,
            )
            
            # Перемещаем на GPU
            pipeline = pipeline.to(self.device)
            
            # Применяем оптимизации
            # pipeline.enable_memory_efficient_attention()
            pipeline.enable_xformers_memory_efficient_attention
            
            # Проверяем размер GPU памяти
            total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
            if total_memory < 24:  # Меньше 24GB
                pipeline.enable_attention_slicing()
                pipeline.enable_vae_slicing()
                logger.info("Applied memory optimizations for Multi-ControlNet pipeline")
            
            setup_time = time.time() - start_time
            
            # UPDATED: Pipeline naming for Union vs MultiControlNet
            pipeline_name = "union_controlnet_pipeline" if "union" in controlnets else "multi_controlnet_pipeline"
            model_description = "union_controlnet_sdxl" if "union" in controlnets else "multi_controlnet_sdxl"
            
            self.loaded_models[pipeline_name] = pipeline
            self.model_status[pipeline_name] = ModelStatus(
                loaded=True,
                model_name=model_description,
                load_time_seconds=setup_time
            )
            
            logger.info(f"Multi-ControlNet pipeline setup successfully in {setup_time:.1f}s")
            return pipeline
            
        except Exception as e:
            logger.error(f"Failed to setup Multi-ControlNet pipeline: {e}")
            pipeline_name = "union_controlnet_pipeline" if "union" in controlnets else "multi_controlnet_pipeline"
            model_description = "union_controlnet_sdxl" if "union" in controlnets else "multi_controlnet_sdxl"
            
            self.model_status[pipeline_name] = ModelStatus(
                loaded=False,
                model_name=model_description,
                error_message=str(e)
            )
            raise RuntimeError(f"Failed to setup Multi-ControlNet pipeline: {e}")
    
    def _get_memory_usage(self) -> float:
        """Возвращает использование GPU памяти в MB."""
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated() / 1024**2
        return 0.0
    
    def get_model_status(self) -> Dict[str, ModelStatus]:
        """Возвращает статус всех моделей."""
        return self.model_status.copy()
    
    def get_loaded_models(self) -> Dict[str, Any]:
        """Возвращает загруженные модели."""
        return self.loaded_models.copy()
    
    def is_model_loaded(self, model_name: str) -> bool:
        """Проверяет загружена ли модель."""
        status = self.model_status.get(model_name)
        return status.loaded if status else False
    
    async def unload_model(self, model_name: str):
        """Выгружает модель для освобождения памяти."""
        if model_name in self.loaded_models:
            del self.loaded_models[model_name]
            if model_name in self.model_status:
                self.model_status[model_name].loaded = False
            
            # Очищаем GPU память
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info(f"Model {model_name} unloaded")
    
    async def unload_all_models(self):
        """Выгружает все модели."""
        self.loaded_models.clear()
        for status in self.model_status.values():
            status.loaded = False
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("All models unloaded")
    
    def get_total_memory_usage(self) -> Dict[str, float]:
        """Возвращает общую статистику использования памяти."""
        if not torch.cuda.is_available():
            return {"total_mb": 0, "available_mb": 0, "used_mb": 0}
        
        total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**2
        allocated_memory = torch.cuda.memory_allocated() / 1024**2
        cached_memory = torch.cuda.memory_reserved() / 1024**2
        
        return {
            "total_mb": total_memory,
            "allocated_mb": allocated_memory,
            "cached_mb": cached_memory,
            "free_mb": total_memory - cached_memory
        }
        