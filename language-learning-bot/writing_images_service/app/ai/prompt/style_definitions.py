"""
Style Definitions - определения стилей для AI генерации изображений.
Содержит шаблоны промптов, модификаторы и параметры для разных художественных стилей.
"""

from typing import Dict, Any, List, Optional
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
    style_modifiers: List[str]
    negative_prompt_additions: List[str]
    
    # Качественные модификаторы
    quality_boosters: List[str]
    composition_hints: List[str]
    
    # Технические параметры
    recommended_steps: int = 30
    recommended_cfg: float = 7.5
    recommended_size: tuple = (1024, 1024)
    
    # ControlNet веса для этого стиля
    controlnet_weights: Dict[str, float] = None
    
    # Постобработка
    postprocessing_filters: List[str] = None
    
    def __post_init__(self):
        """Инициализация значений по умолчанию"""
        if self.controlnet_weights is None:
            self.controlnet_weights = {
                "canny": 0.8,
                "depth": 0.6,
                "segmentation": 0.5,
                "scribble": 0.4
            }
        
        if self.postprocessing_filters is None:
            self.postprocessing_filters = []


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
            
            style_modifiers=[
                "bold outlines",
                "vibrant colors", 
                "pop art style",
                "graphic novel aesthetic",
                "dynamic lighting",
                "cel shading",
                "high contrast",
                "saturated colors"
            ],
            
            negative_prompt_additions=[
                "realistic",
                "photographic", 
                "dark",
                "gloomy",
                "monochrome",
                "muted colors",
                "soft edges",
                "watercolor"
            ],
            
            quality_boosters=[
                "masterpiece",
                "best quality",
                "highly detailed",
                "professional artwork",
                "trending on artstation"
            ],
            
            composition_hints=[
                "dynamic composition",
                "bold perspective", 
                "dramatic angles",
                "action-packed scene"
            ],
            
            recommended_steps=25,
            recommended_cfg=8.0,
            
            controlnet_weights={
                "canny": 0.9,      # Сильные контуры для комиксов
                "depth": 0.5,      # Умеренная объемность
                "segmentation": 0.7, # Четкие цветовые зоны
                "scribble": 0.3    # Минимальная художественность
            },
            
            postprocessing_filters=[
                "enhance_contrast",
                "sharpen_edges", 
                "boost_saturation"
            ]
        )
        
        # Watercolor Style
        self.styles["watercolor"] = StyleDefinition(
            name="watercolor",
            display_name="Watercolor Painting",
            description="Мягкая акварельная живопись с плавными переходами и художественными мазками",
            
            base_template="A soft watercolor painting depicting {meaning}, with flowing brushstrokes inspired by the Chinese character {character}, featuring delicate washes and artistic spontaneity",
            
            style_modifiers=[
                "soft edges",
                "bleeding colors",
                "artistic brushstrokes", 
                "delicate washes",
                "organic textures",
                "transparent layers",
                "fluid movements",
                "natural pigments"
            ],
            
            negative_prompt_additions=[
                "sharp edges",
                "digital art",
                "3d render", 
                "cartoon",
                "harsh lighting",
                "mechanical",
                "geometric",
                "bold outlines"
            ],
            
            quality_boosters=[
                "masterpiece",
                "fine art",
                "museum quality",
                "artistic excellence",
                "expressive technique"
            ],
            
            composition_hints=[
                "balanced composition",
                "natural flow",
                "organic arrangement",
                "harmony of colors"
            ],
            
            recommended_steps=35,
            recommended_cfg=6.5,
            
            controlnet_weights={
                "canny": 0.4,      # Размытые контуры
                "depth": 0.3,      # Мягкая объемность
                "segmentation": 0.3, # Плавные переходы
                "scribble": 0.8    # Максимальная художественная свобода
            },
            
            postprocessing_filters=[
                "soft_blur",
                "edge_smoothing",
                "color_bleeding_effect"
            ]
        )
        
        # Realistic Style
        self.styles["realistic"] = StyleDefinition(
            name="realistic",
            display_name="Photorealistic",
            description="Детализированная реалистичная иллюстрация с естественным освещением",
            
            base_template="A detailed realistic illustration representing {meaning}, maintaining the essence of the Chinese character {character}, with photorealistic quality and natural lighting",
            
            style_modifiers=[
                "photorealistic",
                "detailed textures",
                "natural lighting",
                "high definition",
                "realistic materials",
                "accurate proportions",
                "fine details",
                "lifelike appearance"
            ],
            
            negative_prompt_additions=[
                "cartoon",
                "anime",
                "stylized",
                "abstract",
                "unrealistic",
                "exaggerated",
                "simplified",
                "fantasy elements"
            ],
            
            quality_boosters=[
                "masterpiece",
                "8k resolution",
                "ultra realistic",
                "professional photography",
                "award winning"
            ],
            
            composition_hints=[
                "perfect lighting",
                "professional composition",
                "depth of field",
                "realistic perspective"
            ],
            
            recommended_steps=40,
            recommended_cfg=7.5,
            
            controlnet_weights={
                "canny": 0.8,      # Точные контуры
                "depth": 0.9,      # Сильная объемность
                "segmentation": 0.6, # Реалистичные цвета
                "scribble": 0.2    # Минимальная стилизация
            },
            
            postprocessing_filters=[
                "noise_reduction",
                "detail_enhancement",
                "color_correction"
            ]
        )
        
        # Anime Style
        self.styles["anime"] = StyleDefinition(
            name="anime",
            display_name="Anime Art",
            description="Японский анимационный стиль с яркими цветами и выразительным дизайном",
            
            base_template="An anime-style artwork showing {meaning}, stylized after the Chinese character {character}, featuring cel shading and expressive design",
            
            style_modifiers=[
                "cel shading",
                "bright colors",
                "expressive style",
                "manga influence",
                "clean lines",
                "stylized features",
                "dramatic lighting",
                "vibrant atmosphere"
            ],
            
            negative_prompt_additions=[
                "realistic",
                "photographic",
                "western style",
                "3d render",
                "rough textures",
                "dull colors",
                "messy lines"
            ],
            
            quality_boosters=[
                "masterpiece",
                "best quality",
                "studio quality",
                "professional anime art",
                "trending on pixiv"
            ],
            
            composition_hints=[
                "dynamic pose",
                "expressive composition",
                "anime perspective",
                "stylistic arrangement"
            ],
            
            recommended_steps=28,
            recommended_cfg=7.0,
            
            controlnet_weights={
                "canny": 0.7,      # Четкие, но стилизованные контуры
                "depth": 0.4,      # Легкая объемность
                "segmentation": 0.8, # Четкие цветовые зоны
                "scribble": 0.5    # Средняя стилизация
            },
            
            postprocessing_filters=[
                "enhance_contrast",
                "boost_saturation"
            ]
        )
        
        # Traditional Chinese Ink Style
        self.styles["ink"] = StyleDefinition(
            name="ink",
            display_name="Chinese Ink Painting",
            description="Традиционная китайская живопись тушью с философской глубиной",
            
            base_template="A traditional Chinese ink painting of {meaning}, capturing the spirit of the character {character}, with flowing brushstrokes and philosophical depth",
            
            style_modifiers=[
                "Chinese ink painting",
                "traditional brushwork",
                "flowing lines",
                "minimalist composition",
                "philosophical depth",
                "monochromatic tones",
                "artistic restraint",
                "cultural authenticity"
            ],
            
            negative_prompt_additions=[
                "colorful",
                "western style",
                "digital art",
                "modern",
                "cartoon",
                "bright colors",
                "complex details"
            ],
            
            quality_boosters=[
                "masterpiece",
                "traditional art",
                "cultural heritage",
                "artistic mastery",
                "timeless beauty"
            ],
            
            composition_hints=[
                "zen composition",
                "negative space",
                "balanced harmony",
                "spiritual essence"
            ],
            
            recommended_steps=32,
            recommended_cfg=6.0,
            
            controlnet_weights={
                "canny": 0.6,      # Плавные контуры
                "depth": 0.3,      # Минимальная объемность
                "segmentation": 0.2, # Простые формы
                "scribble": 0.9    # Максимальная художественность
            },
            
            postprocessing_filters=[
                "ink_effect",
                "paper_texture",
                "traditional_aging"
            ]
        )
        
        # Digital Art Style
        self.styles["digital"] = StyleDefinition(
            name="digital",
            display_name="Digital Art",
            description="Современное цифровое искусство с техническим совершенством",
            
            base_template="A modern digital artwork representing {meaning}, inspired by the Chinese character {character}, with contemporary digital techniques and polished finish",
            
            style_modifiers=[
                "digital art",
                "contemporary style",
                "polished finish",
                "modern techniques",
                "clean aesthetics",
                "technical precision",
                "digital painting",
                "professional quality"
            ],
            
            negative_prompt_additions=[
                "traditional",
                "hand drawn",
                "rough sketch",
                "unfinished",
                "amateur",
                "low resolution",
                "pixelated"
            ],
            
            quality_boosters=[
                "masterpiece",
                "digital masterpiece",
                "trending on artstation",
                "concept art quality",
                "professional digital art"
            ],
            
            composition_hints=[
                "modern composition",
                "digital perspective",
                "contemporary layout",
                "technical excellence"
            ],
            
            recommended_steps=30,
            recommended_cfg=7.5,
            
            controlnet_weights={
                "canny": 0.7,
                "depth": 0.7,
                "segmentation": 0.6,
                "scribble": 0.4
            },
            
            postprocessing_filters=[
                "digital_enhancement",
                "color_grading",
                "sharpening"
            ]
        )
        
        # Fantasy Style
        self.styles["fantasy"] = StyleDefinition(
            name="fantasy",
            display_name="Fantasy Art",
            description="Фэнтезийный стиль с магическими элементами и мистической атмосферой",
            
            base_template="A mystical fantasy artwork depicting {meaning}, embodying the magical essence of the Chinese character {character}, with ethereal atmosphere and enchanting details",
            
            style_modifiers=[
                "fantasy art",
                "mystical atmosphere",
                "magical elements",
                "ethereal lighting",
                "enchanting details",
                "otherworldly beauty",
                "legendary quality",
                "mythical inspiration"
            ],
            
            negative_prompt_additions=[
                "realistic",
                "mundane",
                "ordinary",
                "scientific",
                "technical",
                "modern",
                "everyday objects"
            ],
            
            quality_boosters=[
                "masterpiece",
                "epic fantasy art",
                "legendary artwork",
                "mythical quality",
                "enchanted masterpiece"
            ],
            
            composition_hints=[
                "epic composition",
                "magical perspective",
                "mystical arrangement",
                "legendary scale"
            ],
            
            recommended_steps=35,
            recommended_cfg=8.0,
            
            controlnet_weights={
                "canny": 0.6,
                "depth": 0.8,
                "segmentation": 0.5,
                "scribble": 0.7
            },
            
            postprocessing_filters=[
                "magical_glow",
                "fantasy_enhancement",
                "mystical_effects"
            ]
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
            style_name = "comic"
        
        style_def = self.styles[style_name]
        
        return {
            "name": style_def.name,
            "display_name": style_def.display_name,
            "description": style_def.description,
            "base_template": style_def.base_template,
            "style_modifiers": style_def.style_modifiers,
            "negative_prompt_additions": style_def.negative_prompt_additions,
            "quality_boosters": style_def.quality_boosters,
            "composition_hints": style_def.composition_hints,
            "recommended_steps": style_def.recommended_steps,
            "recommended_cfg": style_def.recommended_cfg,
            "recommended_size": style_def.recommended_size,
            "controlnet_weights": style_def.controlnet_weights,
            "postprocessing_filters": style_def.postprocessing_filters
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
    
    def get_style_recommendations(self, character_analysis: Dict[str, Any]) -> List[Tuple[str, float]]:
        """
        Рекомендует стили на основе анализа иероглифа.
        
        Args:
            character_analysis: Семантический анализ иероглифа
            
        Returns:
            List[Tuple[str, float]]: Список (стиль, оценка_подходящести)
        """
        recommendations = []
        
        # Анализируем семантику для рекомендаций
        meanings = character_analysis.get("meanings", [])
        cultural_context = character_analysis.get("cultural_context", {})
        color_associations = character_analysis.get("color_associations", [])
        
        for style_name, style_def in self.styles.items():
            score = 0.5  # Базовая оценка
            
            # Стиль-специфичные рекомендации
            if style_name == "ink":
                # Традиционный стиль для традиционных концепций
                traditional_keywords = ["wisdom", "virtue", "harmony", "traditional", "philosophy"]
                if any(keyword in " ".join(meanings).lower() for keyword in traditional_keywords):
                    score += 0.3
                
                # Лучше для простых концепций
                if len(meanings) <= 2:
                    score += 0.2
            
            elif style_name == "fantasy":
                # Фэнтези для мистических концепций
                mystical_keywords = ["dragon", "phoenix", "magic", "spirit", "divine", "celestial"]
                if any(keyword in " ".join(meanings).lower() for keyword in mystical_keywords):
                    score += 0.4
            
            elif style_name == "comic":
                # Комикс для динамичных концепций
                dynamic_keywords = ["action", "power", "strong", "fast", "energy"]
                if any(keyword in " ".join(meanings).lower() for keyword in dynamic_keywords):
                    score += 0.3
                
                # Хорошо для ярких цветов
                bright_colors = ["red", "yellow", "orange", "bright"]
                if any(color in color_associations for color in bright_colors):
                    score += 0.2
            
            elif style_name == "watercolor":
                # Акварель для природных концепций
                nature_keywords = ["water", "flower", "tree", "wind", "cloud", "gentle"]
                if any(keyword in " ".join(meanings).lower() for keyword in nature_keywords):
                    score += 0.3
                
                # Хорошо для мягких цветов
                soft_colors = ["blue", "green", "soft", "gentle"]
                if any(color in color_associations for color in soft_colors):
                    score += 0.2
            
            elif style_name == "realistic":
                # Реалистичный для конкретных объектов
                concrete_keywords = ["person", "house", "tool", "animal", "object"]
                if any(keyword in " ".join(meanings).lower() for keyword in concrete_keywords):
                    score += 0.3
            
            # Wu Xing элементы
            wu_xing_elements = cultural_context.get("wu_xing_elements", [])
            if wu_xing_elements:
                if style_name == "ink" and "water" in wu_xing_elements:
                    score += 0.2
                elif style_name == "comic" and "fire" in wu_xing_elements:
                    score += 0.2
                elif style_name == "realistic" and "earth" in wu_xing_elements:
                    score += 0.2
            
            recommendations.append((style_name, min(1.0, score)))
        
        # Сортируем по оценке
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations
   