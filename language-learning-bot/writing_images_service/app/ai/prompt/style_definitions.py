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
    
    # Шаблоны промптов
    base_template: str

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
        
        self.styles["anime"] = StyleDefinition(
            name="anime",
            base_template="An anime-style artwork showing concept: '{meaning}', stylized in the form of the Chinese character '{character}'. {hint_writing}",
        )

        self.styles["cartoon"] = StyleDefinition(
            name="cartoon",
            base_template="A cartoon picture of concept: {meaning}, in the form of Chinese character {character}. {hint_writing}",
        )

        self.styles["comic"] = StyleDefinition(
            name="comic",
            base_template="A vibrant comic book style illustration of concept: '{meaning}', inspired by the form of the Chinese character '{character}'. {hint_writing}",
        )

        self.styles["cyberpunk"] = StyleDefinition(
            name="cyberpunk",
            base_template="A cyberpunk style picture of concept: {meaning}, in the form of Chinese character {character}. {hint_writing}",
        )

        self.styles["digital"] = StyleDefinition(
            name="digital",
            base_template="A modern digital artwork representing concept: '{meaning}', inspired by the form of the Chinese character '{character}'. {hint_writing}",
        )

        self.styles["disney"] = StyleDefinition(
            name="disney",
            base_template="A Disney animation style illustration of concept: {meaning}, in the form of Chinese character {character}. {hint_writing}",
        )

        self.styles["fantasy"] = StyleDefinition(
            name="fantasy",
            base_template="A mystical fantasy artwork depicting concept: '{meaning}', embodying the form of the Chinese character '{character}'. {hint_writing}",
        )

        self.styles["ink"] = StyleDefinition(
            name="ink",
            base_template="A traditional Chinese ink painting of concept: '{meaning}', capturing the form of the Chinese character '{character}'. {hint_writing}",
        )
        
        self.styles["realistic"] = StyleDefinition(
            name="realistic",
            base_template="A detailed realistic illustration representing concept: '{meaning}', maintaining the form of the Chinese character '{character}'. {hint_writing}",
        )

        self.styles["techno"] = StyleDefinition(
            name="techno",
            base_template="A modern techno style picture of concept: '{meaning}', in the form of the Chinese character '{character}'. {hint_writing}",
        )

        self.styles["watercolor"] = StyleDefinition(
            name="watercolor",
            base_template="A soft watercolor painting depicting concept: '{meaning}', with flowing brushstrokes inspired by the form of the Chinese character '{character}'. {hint_writing}",
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
            "base_template": style_def.base_template,
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
            "width": style_def.get("recommended_size", (1024, 1024))[0],
            "height": style_def.get("recommended_size", (1024, 1024))[1]
        }
