"""
AI Generation Configuration
Конфигурация для AI генерации изображений.
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class AIGenerationConfig:
    """Конфигурация AI генерации"""
    # Модели
    base_model: str = "stabilityai/stable-diffusion-xl-base-1.0"
    controlnet_models: Optional[Dict[str, str]] = None
    
    # Параметры генерации
    num_inference_steps: int = 30
    guidance_scale: float = 7.5
    width: int = 1024
    height: int = 1024
    batch_size: int = 1
    
    # Conditioning веса по умолчанию
    conditioning_weights: Optional[Dict[str, float]] = None
    
    # GPU настройки
    device: str = "cuda"
    memory_efficient: bool = True
    enable_attention_slicing: bool = True
    enable_cpu_offload: bool = False
    
    # Translation настройки
    enable_translation: bool = True
    translation_fallback_to_original: bool = True
    
    def __post_init__(self):
        """Инициализация значений по умолчанию"""
        if self.controlnet_models is None:
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
            