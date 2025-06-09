"""
GPU manager for AI model optimization.
Менеджер GPU для оптимизации AI моделей.
"""

import logging
import torch
import gc
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GPUStatus:
    """Статус GPU"""
    available: bool
    device_name: str
    total_memory_gb: float
    used_memory_gb: float
    free_memory_gb: float
    utilization_percent: float


class GPUManager:
    """
    Менеджер GPU для оптимизации производительности AI моделей.
    """
    
    def __init__(self):
        """Инициализация GPU менеджера."""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_cuda_available = torch.cuda.is_available()
        logger.info(f"GPUManager initialized - CUDA available: {self.is_cuda_available}")
    
    def get_memory_usage(self) -> Dict[str, float]:
        """
        Возвращает информацию об использовании GPU памяти.
        
        Returns:
            Словарь с информацией о памяти в GB
        """
        if not self.is_cuda_available:
            return {
                "total_gb": 0.0,
                "used_gb": 0.0,
                "free_gb": 0.0,
                "cached_gb": 0.0
            }
        
        try:
            total = torch.cuda.get_device_properties(0).total_memory / 1024**3
            allocated = torch.cuda.memory_allocated() / 1024**3
            cached = torch.cuda.memory_reserved() / 1024**3
            free = total - cached
            
            return {
                "total_gb": round(total, 2),
                "used_gb": round(allocated, 2),
                "free_gb": round(free, 2),
                "cached_gb": round(cached, 2)
            }
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {}
    
    def get_gpu_status(self) -> GPUStatus:
        """Возвращает полный статус GPU."""
        if not self.is_cuda_available:
            return GPUStatus(
                available=False,
                device_name="CPU",
                total_memory_gb=0.0,
                used_memory_gb=0.0,
                free_memory_gb=0.0,
                utilization_percent=0.0
            )
        
        try:
            device_props = torch.cuda.get_device_properties(0)
            memory_info = self.get_memory_usage()
            
            return GPUStatus(
                available=True,
                device_name=device_props.name,
                total_memory_gb=memory_info["total_gb"],
                used_memory_gb=memory_info["used_gb"],
                free_memory_gb=memory_info["free_gb"],
                utilization_percent=round((memory_info["used_gb"] / memory_info["total_gb"]) * 100, 1)
            )
        except Exception as e:
            logger.error(f"Error getting GPU status: {e}")
            return GPUStatus(
                available=False,
                device_name="Unknown",
                total_memory_gb=0.0,
                used_memory_gb=0.0,
                free_memory_gb=0.0,
                utilization_percent=0.0
            )
    
    def optimize_memory(self, pipeline) -> bool:
        """
        Применяет оптимизации памяти к pipeline.
        
        Args:
            pipeline: Pipeline для оптимизации
            
        Returns:
            True если оптимизации применены успешно
        """
        if not self.is_cuda_available or not pipeline:
            return False
        
        try:
            # Определяем доступную память
            memory_info = self.get_memory_usage()
            total_memory = memory_info["total_gb"]
            
            logger.info(f"Optimizing for {total_memory}GB GPU memory")
            
            # Для больших GPU (80GB+) - минимальные оптимизации
            if total_memory >= 80:
                logger.info("Large GPU detected - minimal optimizations")
                if hasattr(pipeline, 'enable_vae_tiling'):
                    pipeline.enable_vae_tiling()
                return True
            
            # Для средних GPU (24-80GB) - умеренные оптимизации  
            elif total_memory >= 24:
                logger.info("Medium GPU detected - moderate optimizations")
                if hasattr(pipeline, 'enable_attention_slicing'):
                    pipeline.enable_attention_slicing()
                if hasattr(pipeline, 'enable_vae_slicing'):
                    pipeline.enable_vae_slicing()
                return True
            
            # Для малых GPU (<24GB) - агрессивные оптимизации
            else:
                logger.info("Small GPU detected - aggressive optimizations")
                if hasattr(pipeline, 'enable_attention_slicing'):
                    pipeline.enable_attention_slicing()
                if hasattr(pipeline, 'enable_vae_slicing'):
                    pipeline.enable_vae_slicing()
                if hasattr(pipeline, 'enable_vae_tiling'):
                    pipeline.enable_vae_tiling()
                if hasattr(pipeline, 'enable_model_cpu_offload'):
                    pipeline.enable_model_cpu_offload()
                return True
                
        except Exception as e:
            logger.error(f"Error optimizing memory: {e}")
            return False
    
    def enable_optimizations(self, pipeline) -> Dict[str, bool]:
        """
        Включает различные оптимизации производительности.
        
        Args:
            pipeline: Pipeline для оптимизации
            
        Returns:
            Словарь с результатами применения оптимизаций
        """
        optimizations = {
            "memory_efficient_attention": False,
            "attention_slicing": False,
            "vae_slicing": False,
            "vae_tiling": False,
            "model_cpu_offload": False,
            "torch_compile": False,
            "channels_last": False
        }
        
        if not pipeline:
            return optimizations
        
        try:
            # Memory efficient attention
            if hasattr(pipeline, 'enable_memory_efficient_attention'):
                pipeline.enable_memory_efficient_attention()
                optimizations["memory_efficient_attention"] = True
            
            # Attention slicing
            if hasattr(pipeline, 'enable_attention_slicing'):
                pipeline.enable_attention_slicing()
                optimizations["attention_slicing"] = True
            
            # VAE optimizations
            if hasattr(pipeline, 'enable_vae_slicing'):
                pipeline.enable_vae_slicing()
                optimizations["vae_slicing"] = True
            
            if hasattr(pipeline, 'enable_vae_tiling'):
                pipeline.enable_vae_tiling()
                optimizations["vae_tiling"] = True
            
            # CPU offload для экономии памяти
            memory_info = self.get_memory_usage()
            if memory_info.get("total_gb", 0) < 24:  # Только для небольших GPU
                if hasattr(pipeline, 'enable_model_cpu_offload'):
                    pipeline.enable_model_cpu_offload()
                    optimizations["model_cpu_offload"] = True
            
            # Torch compile (если доступно)
            try:
                if hasattr(torch, 'compile') and hasattr(pipeline, 'unet'):
                    pipeline.unet = torch.compile(pipeline.unet, mode="reduce-overhead")
                    optimizations["torch_compile"] = True
            except Exception as e:
                logger.warning(f"Torch compile failed: {e}")
            
            # Channels last memory format
            try:
                if hasattr(pipeline, 'unet'):
                    pipeline.unet.to(memory_format=torch.channels_last)
                    optimizations["channels_last"] = True
            except Exception as e:
                logger.warning(f"Channels last failed: {e}")
            
            logger.info(f"Applied optimizations: {optimizations}")
            return optimizations
            
        except Exception as e:
            logger.error(f"Error applying optimizations: {e}")
            return optimizations
    
    def clear_cache(self):
        """Очищает GPU кэш."""
        if self.is_cuda_available:
            torch.cuda.empty_cache()
            gc.collect()
            logger.info("GPU cache cleared")
    
    def get_recommended_batch_size(self, image_size: int = 1024) -> int:
        """
        Рекомендует размер batch на основе доступной памяти.
        
        Args:
            image_size: Размер изображения в пикселях
            
        Returns:
            Рекомендуемый batch size
        """
        if not self.is_cuda_available:
            return 1
        
        try:
            memory_info = self.get_memory_usage()
            free_memory_gb = memory_info.get("free_gb", 0)
            
            # Оценка памяти на одно изображение (очень приблизительно)
            if image_size >= 1024:
                memory_per_image_gb = 3.0  # ~3GB на 1024x1024
            elif image_size >= 768:
                memory_per_image_gb = 2.0  # ~2GB на 768x768
            else:
                memory_per_image_gb = 1.0  # ~1GB на 512x512
            
            # Оставляем буфер 2GB
            available_for_batch = max(0, free_memory_gb - 2.0)
            recommended_batch = max(1, int(available_for_batch / memory_per_image_gb))
            
            # Ограничиваем максимум
            return min(recommended_batch, 4)
            
        except Exception as e:
            logger.error(f"Error calculating batch size: {e}")
            return 1
    
    def monitor_memory_usage(self) -> Dict[str, Any]:
        """
        Мониторинг использования памяти для отладки.
        
        Returns:
            Детальная информация о памяти
        """
        if not self.is_cuda_available:
            return {"cuda_available": False}
        
        try:
            return {
                "cuda_available": True,
                "device_count": torch.cuda.device_count(),
                "current_device": torch.cuda.current_device(),
                "device_name": torch.cuda.get_device_name(),
                "memory_info": self.get_memory_usage(),
                "memory_stats": torch.cuda.memory_stats() if hasattr(torch.cuda, 'memory_stats') else {}
            }
        except Exception as e:
            logger.error(f"Error monitoring memory: {e}")
            return {"error": str(e)}
    
    def check_memory_requirements(self, required_memory_gb: float) -> bool:
        """
        Проверяет достаточно ли памяти для операции.
        
        Args:
            required_memory_gb: Требуемая память в GB
            
        Returns:
            True если памяти достаточно
        """
        if not self.is_cuda_available:
            return False
        
        memory_info = self.get_memory_usage()
        free_memory = memory_info.get("free_gb", 0)
        
        return free_memory >= required_memory_gb
    