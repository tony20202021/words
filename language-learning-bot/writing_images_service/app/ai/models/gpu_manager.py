"""
GPU manager for AI model optimization.
Менеджер GPU для оптимизации AI моделей.
"""

import logging
import torch
import gc
import time
import psutil
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from contextlib import contextmanager

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
    temperature_celsius: Optional[float] = None
    power_usage_watts: Optional[float] = None


@dataclass
class OptimizationProfile:
    """Профиль оптимизации для GPU"""
    name: str
    memory_efficient: bool
    attention_slicing: bool
    vae_slicing: bool
    vae_tiling: bool
    cpu_offload: bool
    sequential_cpu_offload: bool
    torch_compile: bool
    channels_last: bool
    max_batch_size: int
    enable_xformers: bool


class GPUManager:
    """
    Менеджер GPU для оптимизации производительности AI моделей.
    Автоматически определяет оптимальные настройки в зависимости от доступных ресурсов.
    """
    
    def __init__(self):
        """Инициализация GPU менеджера."""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_cuda_available = torch.cuda.is_available()
        
        # GPU информация
        self.gpu_info = self._detect_gpu_info()
        self.optimization_profile = self._determine_optimization_profile()
        
        # Мониторинг
        self.memory_history = []
        self.performance_history = []
        
        if not self.is_cuda_available:
            raise RuntimeError("CUDA not available. GPU is required for AI image generation.")
        
        logger.info(f"GPUManager initialized - GPU: {self.gpu_info['name']}, "
                   f"Memory: {self.gpu_info['total_memory_gb']:.1f}GB, "
                   f"Profile: {self.optimization_profile.name}")
    
    def _detect_gpu_info(self) -> Dict[str, Any]:
        """Определяет информацию о GPU."""
        if not self.is_cuda_available:
            return {"name": "CPU", "total_memory_gb": 0, "compute_capability": None}
        
        try:
            device_props = torch.cuda.get_device_properties(0)
            
            gpu_info = {
                "name": device_props.name,
                "total_memory_gb": device_props.total_memory / 1024**3,
                "compute_capability": (device_props.major, device_props.minor),
                "multi_processor_count": device_props.multi_processor_count,
                "max_threads_per_multi_processor": device_props.max_threads_per_multi_processor,
                "device_count": torch.cuda.device_count(),
                "current_device": torch.cuda.current_device()
            }
            
            # Попробуем получить дополнительную информацию через nvidia-ml-py если доступно
            try:
                import pynvml
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                
                # Температура
                try:
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    gpu_info["temperature_celsius"] = temp
                except:
                    pass
                
                # Энергопотребление
                try:
                    power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # mW to W
                    gpu_info["power_usage_watts"] = power
                except:
                    pass
                
            except ImportError:
                logger.debug("pynvml not available, basic GPU info only")
            except Exception as e:
                logger.debug(f"Could not get extended GPU info: {e}")
            
            return gpu_info
            
        except Exception as e:
            logger.error(f"Error detecting GPU info: {e}")
            return {"name": "Unknown GPU", "total_memory_gb": 0, "compute_capability": None}
    
    def _determine_optimization_profile(self) -> OptimizationProfile:
        """Определяет профиль оптимизации на основе GPU."""
        total_memory = self.gpu_info["total_memory_gb"]
        gpu_name = self.gpu_info["name"].lower()
        
        # Профиль для очень больших GPU (80GB+)
        if total_memory >= 80:
            return OptimizationProfile(
                name="ultra_high_memory",
                memory_efficient=False,
                attention_slicing=False,
                vae_slicing=False,
                vae_tiling=False,
                cpu_offload=False,
                sequential_cpu_offload=False,
                torch_compile=True,
                channels_last=True,
                max_batch_size=8,
                enable_xformers=True
            )
        
        # Профиль для больших GPU (40-80GB)
        elif total_memory >= 40:
            return OptimizationProfile(
                name="high_memory",
                memory_efficient=False,
                attention_slicing=False,
                vae_slicing=False,
                vae_tiling=True,
                cpu_offload=False,
                sequential_cpu_offload=False,
                torch_compile=True,
                channels_last=True,
                max_batch_size=4,
                enable_xformers=True
            )
        
        # Профиль для средних GPU (24-40GB)
        elif total_memory >= 24:
            return OptimizationProfile(
                name="medium_memory",
                memory_efficient=True,
                attention_slicing=True,
                vae_slicing=True,
                vae_tiling=True,
                cpu_offload=False,
                sequential_cpu_offload=False,
                torch_compile=True,
                channels_last=True,
                max_batch_size=2,
                enable_xformers=True
            )
        
        # Профиль для малых GPU (12-24GB)
        elif total_memory >= 12:
            return OptimizationProfile(
                name="low_memory",
                memory_efficient=True,
                attention_slicing=True,
                vae_slicing=True,
                vae_tiling=True,
                cpu_offload=True,
                sequential_cpu_offload=False,
                torch_compile=False,  # Может быть нестабильно на малых GPU
                channels_last=True,
                max_batch_size=1,
                enable_xformers=True
            )
        
        # Профиль для очень малых GPU (<12GB)
        else:
            return OptimizationProfile(
                name="minimal_memory",
                memory_efficient=True,
                attention_slicing=True,
                vae_slicing=True,
                vae_tiling=True,
                cpu_offload=True,
                sequential_cpu_offload=True,
                torch_compile=False,
                channels_last=False,  # Может увеличить память
                max_batch_size=1,
                enable_xformers=False  # Может быть нестабильно
            )
    
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
                "cached_gb": 0.0,
                "percent_used": 0.0
            }
        
        try:
            total = torch.cuda.get_device_properties(0).total_memory / 1024**3
            allocated = torch.cuda.memory_allocated() / 1024**3
            cached = torch.cuda.memory_reserved() / 1024**3
            free = total - cached
            percent_used = (allocated / total) * 100 if total > 0 else 0
            
            memory_info = {
                "total_gb": round(total, 2),
                "used_gb": round(allocated, 2),
                "free_gb": round(free, 2),
                "cached_gb": round(cached, 2),
                "percent_used": round(percent_used, 1)
            }
            
            # Добавляем в историю
            self.memory_history.append({
                "timestamp": time.time(),
                "memory_info": memory_info.copy()
            })
            
            # Сохраняем только последние 100 записей
            if len(self.memory_history) > 100:
                self.memory_history = self.memory_history[-100:]
            
            return memory_info
            
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
            memory_info = self.get_memory_usage()
            
            # Пытаемся получить дополнительную информацию
            temperature = None
            power_usage = None
            
            try:
                import pynvml
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                
                try:
                    temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                except:
                    pass
                
                try:
                    power_usage = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
                except:
                    pass
                    
            except ImportError:
                pass
            except Exception as e:
                logger.debug(f"Could not get GPU sensors: {e}")
            
            return GPUStatus(
                available=True,
                device_name=self.gpu_info["name"],
                total_memory_gb=memory_info["total_gb"],
                used_memory_gb=memory_info["used_gb"],
                free_memory_gb=memory_info["free_gb"],
                utilization_percent=memory_info["percent_used"],
                temperature_celsius=temperature,
                power_usage_watts=power_usage
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
    
    def optimize_pipeline(self, pipeline) -> Dict[str, bool]:
        """
        Применяет оптимизации к pipeline на основе профиля GPU.
        
        Args:
            pipeline: Pipeline для оптимизации
            
        Returns:
            Dict с результатами применения оптимизаций
        """
        if not pipeline:
            logger.warning("No pipeline provided for optimization")
            return {}
        
        profile = self.optimization_profile
        applied_optimizations = {}
        
        logger.info(f"Applying {profile.name} optimization profile...")
        
        try:
            # Memory efficient attention
            # pipeline.enable_xformers_memory_efficient_attention
            if profile.memory_efficient and hasattr(pipeline, 'enable_memory_efficient_attention'):
                try:
                    pipeline.enable_memory_efficient_attention()
                    applied_optimizations["memory_efficient_attention"] = True
                    logger.debug("✓ Enabled memory efficient attention")
                except Exception as e:
                    logger.warning(f"Failed to enable memory efficient attention: {e}")
                    applied_optimizations["memory_efficient_attention"] = False
            
            # Attention slicing
            if profile.attention_slicing and hasattr(pipeline, 'enable_attention_slicing'):
                try:
                    pipeline.enable_attention_slicing()
                    applied_optimizations["attention_slicing"] = True
                    logger.debug("✓ Enabled attention slicing")
                except Exception as e:
                    logger.warning(f"Failed to enable attention slicing: {e}")
                    applied_optimizations["attention_slicing"] = False
            
            # VAE optimizations
            if profile.vae_slicing and hasattr(pipeline, 'enable_vae_slicing'):
                try:
                    pipeline.enable_vae_slicing()
                    applied_optimizations["vae_slicing"] = True
                    logger.debug("✓ Enabled VAE slicing")
                except Exception as e:
                    logger.warning(f"Failed to enable VAE slicing: {e}")
                    applied_optimizations["vae_slicing"] = False
            
            if profile.vae_tiling and hasattr(pipeline, 'enable_vae_tiling'):
                try:
                    pipeline.enable_vae_tiling()
                    applied_optimizations["vae_tiling"] = True
                    logger.debug("✓ Enabled VAE tiling")
                except Exception as e:
                    logger.warning(f"Failed to enable VAE tiling: {e}")
                    applied_optimizations["vae_tiling"] = False
            
            # CPU offload для экономии памяти
            if profile.cpu_offload and hasattr(pipeline, 'enable_model_cpu_offload'):
                try:
                    pipeline.enable_model_cpu_offload()
                    applied_optimizations["model_cpu_offload"] = True
                    logger.debug("✓ Enabled model CPU offload")
                except Exception as e:
                    logger.warning(f"Failed to enable model CPU offload: {e}")
                    applied_optimizations["model_cpu_offload"] = False
            
            if profile.sequential_cpu_offload and hasattr(pipeline, 'enable_sequential_cpu_offload'):
                try:
                    pipeline.enable_sequential_cpu_offload()
                    applied_optimizations["sequential_cpu_offload"] = True
                    logger.debug("✓ Enabled sequential CPU offload")
                except Exception as e:
                    logger.warning(f"Failed to enable sequential CPU offload: {e}")
                    applied_optimizations["sequential_cpu_offload"] = False
            
            # Torch compile (если доступно)
            if profile.torch_compile and hasattr(torch, 'compile') and hasattr(pipeline, 'unet'):
                try:
                    pipeline.unet = torch.compile(pipeline.unet, mode="reduce-overhead")
                    applied_optimizations["torch_compile"] = True
                    logger.debug("✓ Enabled torch.compile for UNet")
                except Exception as e:
                    logger.warning(f"Torch compile failed: {e}")
                    applied_optimizations["torch_compile"] = False
            
            # Channels last memory format
            if profile.channels_last and hasattr(pipeline, 'unet'):
                try:
                    pipeline.unet.to(memory_format=torch.channels_last)
                    applied_optimizations["channels_last"] = True
                    logger.debug("✓ Enabled channels_last memory format")
                except Exception as e:
                    logger.warning(f"Channels last failed: {e}")
                    applied_optimizations["channels_last"] = False
            
            # XFormers attention (если доступно)
            if profile.enable_xformers:
                try:
                    import xformers
                    if hasattr(pipeline, 'enable_xformers_memory_efficient_attention'):
                        pipeline.enable_xformers_memory_efficient_attention()
                        applied_optimizations["xformers"] = True
                        logger.debug("✓ Enabled XFormers memory efficient attention")
                except ImportError:
                    logger.debug("XFormers not available")
                    applied_optimizations["xformers"] = False
                except Exception as e:
                    logger.warning(f"XFormers failed: {e}")
                    applied_optimizations["xformers"] = False
            
            successful_optimizations = sum(applied_optimizations.values())
            total_optimizations = len(applied_optimizations)
            
            logger.info(f"✓ Applied {successful_optimizations}/{total_optimizations} optimizations "
                       f"for {profile.name} profile")
            
            return applied_optimizations
            
        except Exception as e:
            logger.error(f"Error applying optimizations: {e}")
            return applied_optimizations
    
    def clear_cache(self, aggressive: bool = False):
        """
        Очищает GPU кэш.
        
        Args:
            aggressive: Если True, выполняет более агрессивную очистку
        """
        if not self.is_cuda_available:
            return
        
        try:
            memory_before = self.get_memory_usage()
            
            # Стандартная очистка
            torch.cuda.empty_cache()
            
            if aggressive:
                # Агрессивная очистка
                gc.collect()
                torch.cuda.synchronize()
                torch.cuda.empty_cache()
                
                # Принудительная сборка мусора несколько раз
                for _ in range(3):
                    gc.collect()
            
            memory_after = self.get_memory_usage()
            freed_memory = memory_before.get("cached_gb", 0) - memory_after.get("cached_gb", 0)
            
            cache_type = "aggressive" if aggressive else "standard"
            logger.info(f"✓ {cache_type} GPU cache cleared (freed: {freed_memory:.2f}GB)")
            
        except Exception as e:
            logger.error(f"Error clearing GPU cache: {e}")
    
    def get_recommended_batch_size(self, image_size: int = 1024, model_type: str = "sdxl") -> int:
        """
        Рекомендует размер batch на основе доступной памяти и типа модели.
        
        Args:
            image_size: Размер изображения в пикселях
            model_type: Тип модели (sdxl, sd15, etc.)
            
        Returns:
            Рекомендуемый batch size
        """
        if not self.is_cuda_available:
            return 1
        
        try:
            memory_info = self.get_memory_usage()
            free_memory_gb = memory_info.get("free_gb", 0)
            
            # Базовое потребление памяти для SDXL с ControlNet (очень приблизительно)
            if model_type.lower() == "sdxl":
                if image_size >= 1024:
                    base_memory_gb = 8.0  # ~8GB для SDXL 1024x1024
                elif image_size >= 768:
                    base_memory_gb = 6.0  # ~6GB для SDXL 768x768
                else:
                    base_memory_gb = 4.0  # ~4GB для SDXL 512x512
            else:
                # SD 1.5 или другие модели
                if image_size >= 1024:
                    base_memory_gb = 4.0
                elif image_size >= 768:
                    base_memory_gb = 3.0
                else:
                    base_memory_gb = 2.0
            
            # Дополнительная память на ControlNet (4 типа)
            controlnet_memory_gb = 2.0
            
            # Общая память на одно изображение
            memory_per_image_gb = base_memory_gb + controlnet_memory_gb
            
            # Оставляем буфер
            buffer_gb = 2.0
            available_for_batch = max(0, free_memory_gb - buffer_gb)
            
            # Вычисляем batch size
            recommended_batch = max(1, int(available_for_batch / memory_per_image_gb))
            
            # Ограничиваем максимальным значением из профиля
            max_batch = self.optimization_profile.max_batch_size
            final_batch = min(recommended_batch, max_batch)
            
            logger.debug(f"Recommended batch size: {final_batch} "
                        f"(free: {free_memory_gb:.1f}GB, per_image: {memory_per_image_gb:.1f}GB, "
                        f"max_profile: {max_batch})")
            
            return final_batch
            
        except Exception as e:
            logger.error(f"Error calculating batch size: {e}")
            return 1
    
    @contextmanager
    def memory_monitor(self, operation_name: str = "operation"):
        """
        Контекстный менеджер для мониторинга использования памяти.
        
        Args:
            operation_name: Название операции для логирования
        """
        if not self.is_cuda_available:
            yield
            return
        
        start_time = time.time()
        memory_before = self.get_memory_usage()
        
        try:
            yield
        finally:
            end_time = time.time()
            memory_after = self.get_memory_usage()
            
            operation_time = end_time - start_time
            memory_diff = memory_after.get("used_gb", 0) - memory_before.get("used_gb", 0)
            peak_memory = memory_after.get("used_gb", 0)
            
            # Записываем в историю производительности
            perf_record = {
                "timestamp": start_time,
                "operation": operation_name,
                "duration_seconds": operation_time,
                "memory_before_gb": memory_before.get("used_gb", 0),
                "memory_after_gb": memory_after.get("used_gb", 0),
                "memory_diff_gb": memory_diff,
                "peak_memory_gb": peak_memory
            }
            
            self.performance_history.append(perf_record)
            
            # Сохраняем только последние 50 записей
            if len(self.performance_history) > 50:
                self.performance_history = self.performance_history[-50:]
            
            logger.debug(f"Memory monitor [{operation_name}]: "
                        f"time={operation_time:.2f}s, "
                        f"memory_diff={memory_diff:+.2f}GB, "
                        f"peak={peak_memory:.2f}GB")
    
    def get_optimization_recommendations(self) -> Dict[str, Any]:
        """Возвращает рекомендации по оптимизации на основе текущего состояния."""
        recommendations = {
            "current_profile": self.optimization_profile.name,
            "gpu_info": self.gpu_info,
            "memory_status": self.get_memory_usage(),
            "recommendations": []
        }
        
        memory_info = self.get_memory_usage()
        memory_usage_percent = memory_info.get("percent_used", 0)
        
        # Рекомендации на основе использования памяти
        if memory_usage_percent > 90:
            recommendations["recommendations"].append({
                "type": "critical",
                "message": "GPU memory usage is critical (>90%). Consider enabling more aggressive optimizations.",
                "actions": ["Enable CPU offload", "Reduce batch size", "Enable VAE tiling"]
            })
        elif memory_usage_percent > 75:
            recommendations["recommendations"].append({
                "type": "warning", 
                "message": "GPU memory usage is high (>75%). Monitor for potential issues.",
                "actions": ["Consider enabling attention slicing", "Monitor memory during generation"]
            })
        
        # Рекомендации на основе производительности
        if len(self.performance_history) >= 5:
            recent_operations = self.performance_history[-5:]
            avg_duration = sum(op["duration_seconds"] for op in recent_operations) / len(recent_operations)
            
            if avg_duration > 30:  # Более 30 секунд на генерацию
                recommendations["recommendations"].append({
                    "type": "performance",
                    "message": f"Generation time is slow (avg: {avg_duration:.1f}s). Consider optimizations.",
                    "actions": ["Enable torch.compile", "Check for CPU bottlenecks", "Ensure XFormers is enabled"]
                })
        
        return recommendations
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """Возвращает полную диагностическую информацию."""
        return {
            "gpu_info": self.gpu_info,
            "optimization_profile": {
                "name": self.optimization_profile.name,
                "settings": {
                    "memory_efficient": self.optimization_profile.memory_efficient,
                    "attention_slicing": self.optimization_profile.attention_slicing,
                    "vae_slicing": self.optimization_profile.vae_slicing,
                    "vae_tiling": self.optimization_profile.vae_tiling,
                    "cpu_offload": self.optimization_profile.cpu_offload,
                    "torch_compile": self.optimization_profile.torch_compile,
                    "max_batch_size": self.optimization_profile.max_batch_size
                }
            },
            "current_status": self.get_gpu_status().__dict__,
            "memory_history": self.memory_history[-10:],  # Последние 10 записей
            "performance_history": self.performance_history[-10:],
            "system_info": {
                "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
                "pytorch_version": torch.__version__,
                "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
            },
            "recommendations": self.get_optimization_recommendations()
        }
    