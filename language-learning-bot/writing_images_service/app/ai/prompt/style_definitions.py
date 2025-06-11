"""
Style Definitions - определения стилей для AI генерации изображений.
Содержит шаблоны промптов, модификаторы и параметры для разных художественных стилей.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging

from app.utils.logger import get_module_logger

logger = get_module_logger(__name__)


@dataclass
class StyleDefinition:
    """Определение художественного стиля"""
    # Основная информация
    name: str
    display_name: str
    description: str
    
    # Шаблоны промптов
    base_template: str
    
    # Технические параметры
    recommended_steps: int = 30
    recommended_cfg: float = 7.5
    recommended_size: tuple = (1024, 1024)
    
    # ControlNet веса для этого стиля
    controlnet_weights: Dict[str, float] = None
    
    def __post_init__(self):
        """Инициализация значений по умолчанию"""
        if self.controlnet_weights is None:
            self.controlnet_weights = {
                "canny": 0.8,
                "depth": 0.6,
                "segmentation": 0.5,
                "scribble": 0.4
            }
        

class StyleDefinitions:
    """
    Система определений стилей для AI генерации.
    Управляет шаблонами промптов и параметрами для разных художественных стилей.
    """
    
    def __init__(self):
        """Инициализация системы стилей."""
        self.styles = {}
        self._initialize_default_styles()
        logger.info(f"StyleDefinitions initialized with {len(self.styles)} styles")
    
    def _initialize_default_styles(self):
        """Инициализирует стандартные стили."""
        
        # Comic Book Style
        self.styles["comic"] = StyleDefinition(
            name="comic",
            display_name="Comic Book",
            description="Яркий комиксовый стиль с четкими контурами и насыщенными цветами",
            base_template="A vibrant comic book style illustration of {meaning}, inspired by the Chinese character {character}, featuring bold outlines and dynamic composition",
            recommended_steps=25,
            recommended_cfg=8.0,
            controlnet_weights={
                "canny": 0.9,      # Сильные контуры для комиксов
                "depth": 0.5,      # Умеренная объемность
                "segmentation": 0.7, # Четкие цветовые зоны
                "scribble": 0.3    # Минимальная художественность
            },
        )
        
        # Watercolor Style
        self.styles["watercolor"] = StyleDefinition(
            name="watercolor",
            display_name="Watercolor Painting",
            description="Мягкая акварельная живопись с плавными переходами и художественными мазками",
            base_template="A soft watercolor painting depicting {meaning}, with flowing brushstrokes inspired by the Chinese character {character}, featuring delicate washes and artistic spontaneity",
            recommended_steps=35,
            recommended_cfg=6.5,
            controlnet_weights={
                "canny": 0.4,      # Размытые контуры
                "depth": 0.3,      # Мягкая объемность
                "segmentation": 0.3, # Плавные переходы
                "scribble": 0.8    # Максимальная художественная свобода
            },
        )
        
        # Realistic Style
        self.styles["realistic"] = StyleDefinition(
            name="realistic",
            display_name="Photorealistic",
            description="Детализированная реалистичная иллюстрация с естественным освещением",
            base_template="A detailed realistic illustration representing {meaning}, maintaining the essence of the Chinese character {character}, with photorealistic quality and natural lighting",
            recommended_steps=40,
            recommended_cfg=7.5,
            controlnet_weights={
                "canny": 0.8,      # Точные контуры
                "depth": 0.9,      # Сильная объемность
                "segmentation": 0.6, # Реалистичные цвета
                "scribble": 0.2    # Минимальная стилизация
            },
        )
        
        # Anime Style
        self.styles["anime"] = StyleDefinition(
            name="anime",
            display_name="Anime Art",
            description="Японский анимационный стиль с яркими цветами и выразительным дизайном",
            base_template="An anime-style artwork showing {meaning}, stylized after the Chinese character {character}, featuring cel shading and expressive design",
            recommended_steps=28,
            recommended_cfg=7.0,
            controlnet_weights={
                "canny": 0.7,      # Четкие, но стилизованные контуры
                "depth": 0.4,      # Легкая объемность
                "segmentation": 0.8, # Четкие цветовые зоны
                "scribble": 0.5    # Средняя стилизация
            },
        )
        
        # Traditional Chinese Ink Style
        self.styles["ink"] = StyleDefinition(
            name="ink",
            display_name="Chinese Ink Painting",
            description="Традиционная китайская живопись тушью с философской глубиной",
            base_template="A traditional Chinese ink painting of {meaning}, capturing the spirit of the character {character}, with flowing brushstrokes and philosophical depth",
            recommended_steps=32,
            recommended_cfg=6.0,
            controlnet_weights={
                "canny": 0.6,      # Плавные контуры
                "depth": 0.3,      # Минимальная объемность
                "segmentation": 0.2, # Простые формы
                "scribble": 0.9    # Максимальная художественность
            },
        )
        
        # Digital Art Style
        self.styles["digital"] = StyleDefinition(
            name="digital",
            display_name="Digital Art",
            description="Современное цифровое искусство с техническим совершенством",
            base_template="A modern digital artwork representing {meaning}, inspired by the Chinese character {character}, with contemporary digital techniques and polished finish",
            recommended_steps=30,
            recommended_cfg=7.5,
            controlnet_weights={
                "canny": 0.7,
                "depth": 0.7,
                "segmentation": 0.6,
                "scribble": 0.4
            },
        )
        
        # Fantasy Style
        self.styles["fantasy"] = StyleDefinition(
            name="fantasy",
            display_name="Fantasy Art",
            description="Фэнтезийный стиль с магическими элементами и мистической атмосферой",
            base_template="A mystical fantasy artwork depicting {meaning}, embodying the magical essence of the Chinese character {character}, with ethereal atmosphere and enchanting details",
            recommended_steps=35,
            recommended_cfg=8.0,
            controlnet_weights={
                "canny": 0.6,
                "depth": 0.8,
                "segmentation": 0.5,
                "scribble": 0.7
            },
        )
    
    def get_style_definition(self, style_name: str) -> Dict[str, Any]:
        """
        Получает определение стиля.
        
        Args:
            style_name: Название стиля
            
        Returns:
            Dict[str, Any]: Определение стиля
        """
        if style_name not in self.styles:
            logger.warning(f"Style '{style_name}' not found, returning default comic style")
            return None
        
        style_def = self.styles[style_name]
        
        return {
            "name": style_def.name,
            "display_name": style_def.display_name,
            "description": style_def.description,
            "base_template": style_def.base_template,
            "recommended_steps": style_def.recommended_steps,
            "recommended_cfg": style_def.recommended_cfg,
            "recommended_size": style_def.recommended_size,
            "controlnet_weights": style_def.controlnet_weights,
        }
    
    def get_available_styles(self) -> List[Dict[str, str]]:
        """
        Возвращает список доступных стилей.
        
        Returns:
            List[Dict[str, str]]: Список стилей с основной информацией
        """
        return [
            {
                "name": style.name,
                "display_name": style.display_name,
                "description": style.description
            }
            for style in self.styles.values()
        ]
    
    def get_style_names(self) -> List[str]:
        """
        Возвращает список названий стилей.
        
        Returns:
            List[str]: Названия стилей
        """
        return list(self.styles.keys())
    
    def is_valid_style(self, style_name: str) -> bool:
        """
        Проверяет является ли стиль валидным.
        
        Args:
            style_name: Название стиля
            
        Returns:
            bool: True если стиль существует
        """
        return style_name in self.styles
    
    def get_controlnet_weights_for_style(self, style_name: str) -> Dict[str, float]:
        """
        Получает веса ControlNet для конкретного стиля.
        
        Args:
            style_name: Название стиля
            
        Returns:
            Dict[str, float]: Веса ControlNet
        """
        style_def = self.get_style_definition(style_name)
        return style_def.get("controlnet_weights", {
            "canny": 0.8,
            "depth": 0.6,
            "segmentation": 0.5,
            "scribble": 0.4
        })
    
    def get_generation_params_for_style(self, style_name: str) -> Dict[str, Any]:
        """
        Получает рекомендуемые параметры генерации для стиля.
        
        Args:
            style_name: Название стиля
            
        Returns:
            Dict[str, Any]: Параметры генерации
        """
        style_def = self.get_style_definition(style_name)
        
        return {
            "num_inference_steps": style_def.get("recommended_steps", 30),
            "guidance_scale": style_def.get("recommended_cfg", 7.5),
            "width": style_def.get("recommended_size", (1024, 1024))[0],
            "height": style_def.get("recommended_size", (1024, 1024))[1]
        }
