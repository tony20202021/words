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
    width: int = 1024
    height: int = 1024
    batch_size: int = 1
    
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
        
