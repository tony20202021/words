"""
Model loader for AI image generation.
Загрузчик моделей для AI генерации изображений.
"""

import logging
import torch
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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
        logger.info(f"ModelLoader initialized on device: {self.device}")
    
    async def load_stable_diffusion_xl(self, model_name: str = "stabilityai/stable-diffusion-xl-base-1.0"):
        """
        Загружает Stable Diffusion XL модель.
        
        Args:
            model_name: Название модели на HuggingFace
            
        Returns:
            Загруженная модель или None при ошибке
        """
        async with self._loading_lock:
            if "stable_diffusion_xl" in self.loaded_models:
                return self.loaded_models["stable_diffusion_xl"]
            
            try:
                logger.info(f"Loading Stable Diffusion XL: {model_name}")
                
                # Попытка загрузки из diffusers
                try:
                    from diffusers import StableDiffusionXLPipeline
                    
                    pipeline = StableDiffusionXLPipeline.from_pretrained(
                        model_name,
                        torch_dtype=torch.float16,
                        use_safetensors=True,
                        variant="fp16"
                    )
                    
                    if self.device == "cuda":
                        pipeline = pipeline.to(self.device)
                        pipeline.enable_memory_efficient_attention()
                    
                    self.loaded_models["stable_diffusion_xl"] = pipeline
                    self.model_status["stable_diffusion_xl"] = ModelStatus(
                        loaded=True,
                        model_name=model_name,
                        memory_usage_mb=self._get_model_memory_usage()
                    )
                    
                    logger.info("Stable Diffusion XL loaded successfully")
                    return pipeline
                    
                except ImportError:
                    logger.warning("diffusers not available, using development mode")
                    self.model_status["stable_diffusion_xl"] = ModelStatus(
                        loaded=False,
                        model_name=model_name,
                        error_message="diffusers not installed"
                    )
                    return None
                    
            except Exception as e:
                logger.error(f"Error loading Stable Diffusion XL: {e}")
                self.model_status["stable_diffusion_xl"] = ModelStatus(
                    loaded=False,
                    model_name=model_name,
                    error_message=str(e)
                )
                return None
    
    async def load_controlnet_models(self, model_configs: Dict[str, str]):
        """
        Загружает ControlNet модели.
        
        Args:
            model_configs: Словарь {тип: модель_id}
            
        Returns:
            Словарь загруженных ControlNet моделей
        """
        async with self._loading_lock:
            controlnets = {}
            
            try:
                from diffusers import ControlNetModel
                
                for control_type, model_id in model_configs.items():
                    try:
                        logger.info(f"Loading ControlNet {control_type}: {model_id}")
                        
                        controlnet = ControlNetModel.from_pretrained(
                            model_id,
                            torch_dtype=torch.float16,
                            use_safetensors=True
                        )
                        
                        if self.device == "cuda":
                            controlnet = controlnet.to(self.device)
                        
                        controlnets[control_type] = controlnet
                        self.model_status[f"controlnet_{control_type}"] = ModelStatus(
                            loaded=True,
                            model_name=model_id,
                            memory_usage_mb=self._get_model_memory_usage()
                        )
                        
                        logger.info(f"ControlNet {control_type} loaded successfully")
                        
                    except Exception as e:
                        logger.error(f"Error loading ControlNet {control_type}: {e}")
                        self.model_status[f"controlnet_{control_type}"] = ModelStatus(
                            loaded=False,
                            model_name=model_id,
                            error_message=str(e)
                        )
                
                self.loaded_models["controlnets"] = controlnets
                return controlnets
                
            except ImportError:
                logger.warning("diffusers not available for ControlNet")
                return {}
    
    async def load_auxiliary_models(self):
        """Загружает вспомогательные модели для conditioning."""
        auxiliary_models = {}
        
        # HED Edge Detection
        try:
            logger.info("Loading HED edge detection model")
            # Заглушка - в реальности здесь будет загрузка HED модели
            auxiliary_models["hed"] = None
            self.model_status["hed"] = ModelStatus(
                loaded=False,
                model_name="hed_pretrained",
                error_message="HED model not implemented yet"
            )
        except Exception as e:
            logger.error(f"Error loading HED model: {e}")
        
        # MiDaS Depth Estimation
        try:
            logger.info("Loading MiDaS depth estimation model")
            # Заглушка - в реальности здесь будет загрузка MiDaS модели
            auxiliary_models["midas"] = None
            self.model_status["midas"] = ModelStatus(
                loaded=False,
                model_name="midas_v3_large",
                error_message="MiDaS model not implemented yet"
            )
        except Exception as e:
            logger.error(f"Error loading MiDaS model: {e}")
        
        # SAM Segmentation
        try:
            logger.info("Loading SAM segmentation model")
            # Заглушка - в реальности здесь будет загрузка SAM модели
            auxiliary_models["sam"] = None
            self.model_status["sam"] = ModelStatus(
                loaded=False,
                model_name="sam_vit_h",
                error_message="SAM model not implemented yet"
            )
        except Exception as e:
            logger.error(f"Error loading SAM model: {e}")
        
        self.loaded_models["auxiliary"] = auxiliary_models
        return auxiliary_models
    
    async def setup_multi_controlnet_pipeline(self, controlnets: Dict):
        """
        Настраивает Multi-ControlNet pipeline.
        
        Args:
            controlnets: Словарь загруженных ControlNet моделей
            
        Returns:
            Multi-ControlNet pipeline или None
        """
        try:
            if not controlnets:
                logger.warning("No ControlNet models available for pipeline")
                return None
            
            from diffusers import StableDiffusionXLControlNetPipeline, MultiControlNetModel
            
            base_pipeline = self.loaded_models.get("stable_diffusion_xl")
            if not base_pipeline:
                logger.error("Base Stable Diffusion XL not loaded")
                return None
            
            # Создаем MultiControlNet
            controlnet_list = list(controlnets.values())
            if len(controlnet_list) > 1:
                multi_controlnet = MultiControlNetModel(controlnet_list)
            else:
                multi_controlnet = controlnet_list[0]
            
            # Создаем pipeline с MultiControlNet
            pipeline = StableDiffusionXLControlNetPipeline.from_pretrained(
                "stabilityai/stable-diffusion-xl-base-1.0",
                controlnet=multi_controlnet,
                torch_dtype=torch.float16,
                use_safetensors=True
            )
            
            if self.device == "cuda":
                pipeline = pipeline.to(self.device)
                pipeline.enable_memory_efficient_attention()
            
            self.loaded_models["multi_controlnet_pipeline"] = pipeline
            self.model_status["multi_controlnet_pipeline"] = ModelStatus(
                loaded=True,
                model_name="multi_controlnet_sdxl",
                memory_usage_mb=self._get_model_memory_usage()
            )
            
            logger.info("Multi-ControlNet pipeline setup successfully")
            return pipeline
            
        except ImportError:
            logger.warning("diffusers not available for Multi-ControlNet pipeline")
            return None
        except Exception as e:
            logger.error(f"Error setting up Multi-ControlNet pipeline: {e}")
            self.model_status["multi_controlnet_pipeline"] = ModelStatus(
                loaded=False,
                model_name="multi_controlnet_sdxl",
                error_message=str(e)
            )
            return None
    
    def _get_model_memory_usage(self) -> float:
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
        