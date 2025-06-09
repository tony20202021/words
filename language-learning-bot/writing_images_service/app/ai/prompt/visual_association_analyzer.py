"""
Visual association analyzer for Chinese characters.
Анализатор визуальных ассоциаций китайских иероглифов.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VisualAssociationResult:
    """Результат анализа визуальных ассоциаций"""
    success: bool
    analysis_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class VisualAssociationAnalyzer:
    """
    Анализатор визуальных ассоциаций для китайских иероглифов.
    """
    
    def __init__(self):
        """Инициализация анализатора визуальных ассоциаций."""
        self.color_mappings = self._init_color_mappings()
        self.texture_mappings = self._init_texture_mappings()
        self.motion_mappings = self._init_motion_mappings()
        logger.info("VisualAssociationAnalyzer initialized")
    
    def _init_color_mappings(self) -> Dict[str, List[str]]:
        """Инициализирует цветовые ассоциации."""
        return {
            "fire": ["red", "orange", "yellow", "bright"],
            "water": ["blue", "cyan", "transparent", "clear"],
            "wood": ["brown", "green", "natural"],
            "metal": ["silver", "gold", "metallic", "shiny"],
            "earth": ["brown", "yellow", "muddy", "earthy"],
            "sun": ["yellow", "gold", "bright", "warm"],
            "moon": ["silver", "white", "pale", "soft"],
            "blood": ["red", "dark red", "crimson"],
            "grass": ["green", "fresh green", "vibrant"],
            "sky": ["blue", "light blue", "azure"],
            "night": ["black", "dark blue", "deep"],
            "snow": ["white", "pure white", "crystal"],
            "anger": ["red", "dark red", "fiery"],
            "peace": ["blue", "green", "soft"],
            "joy": ["yellow", "bright", "golden"],
            "sadness": ["blue", "gray", "muted"]
        }
    
    def _init_texture_mappings(self) -> Dict[str, List[str]]:
        """Инициализирует текстурные ассоциации."""
        return {
            "fire": ["flickering", "dancing", "glowing", "bright"],
            "water": ["flowing", "rippling", "smooth", "wet"],
            "wood": ["rough", "textured", "organic", "fibrous"],
            "metal": ["polished", "reflective", "smooth", "cold"],
            "earth": ["granular", "rocky", "solid", "dusty"],
            "rough": ["coarse", "bumpy", "uneven"],
            "smooth": ["polished", "sleek", "glossy"],
            "soft": ["gentle", "tender", "delicate"],
            "hard": ["solid", "firm", "rigid"],
            "liquid": ["flowing", "fluid", "wet"],
            "crystal": ["clear", "transparent", "sharp"],
            "fabric": ["woven", "textile", "soft"],
            "stone": ["hard", "solid", "rough"]
        }
    
    def _init_motion_mappings(self) -> Dict[str, List[str]]:
        """Инициализирует ассоциации движения."""
        return {
            "fire": ["upward", "dancing", "consuming", "spreading"],
            "water": ["flowing", "cascading", "rippling", "dripping"],
            "wind": ["swirling", "gentle", "strong", "directional"],
            "walk": ["steady", "rhythmic", "forward"],
            "run": ["fast", "dynamic", "energetic"],
            "fly": ["soaring", "floating", "graceful"],
            "fall": ["downward", "dropping", "descending"],
            "grow": ["expanding", "rising", "developing"],
            "rotate": ["spinning", "circular", "turning"],
            "vibrate": ["shaking", "trembling", "oscillating"]
        }
    
    async def analyze_visual_associations(self, character: str) -> VisualAssociationResult:
        """
        Анализирует визуальные ассоциации иероглифа.
        
        Args:
            character: Иероглиф для анализа
            
        Returns:
            VisualAssociationResult: Результат анализа визуальных ассоциаций
        """
        try:
            # Получаем базовые ассоциации на основе известных паттернов
            color_associations = self._analyze_colors(character)
            texture_associations = self._analyze_textures(character)
            motion_associations = self._analyze_motion(character)
            
            analysis_data = {
                "character": character,
                "color_mappings": color_associations,
                "texture_mappings": texture_associations,
                "motion_mappings": motion_associations,
                "primary_colors": color_associations[:3] if color_associations else [],
                "primary_textures": texture_associations[:2] if texture_associations else [],
                "primary_motions": motion_associations[:2] if motion_associations else [],
                "visual_complexity": self._assess_visual_complexity(character),
                "dominant_elements": self._get_dominant_elements(
                    color_associations, texture_associations, motion_associations
                )
            }
            
            return VisualAssociationResult(
                success=True,
                analysis_data=analysis_data
            )
            
        except Exception as e:
            logger.error(f"Error analyzing visual associations for {character}: {e}")
            return VisualAssociationResult(
                success=False,
                error_message=str(e)
            )
    
    def _analyze_colors(self, character: str) -> List[str]:
        """Анализирует цветовые ассоциации."""
        colors = []
        
        # Прямые ассоциации с известными элементами
        element_chars = {
            "火": "fire", "水": "water", "木": "wood", "金": "metal", "土": "earth",
            "日": "sun", "月": "moon", "血": "blood", "草": "grass", "天": "sky",
            "夜": "night", "雪": "snow", "怒": "anger", "和": "peace", "喜": "joy"
        }
        
        for char, element in element_chars.items():
            if char in character:
                colors.extend(self.color_mappings.get(element, []))
        
        # Удаляем дубликаты, сохраняя порядок
        return list(dict.fromkeys(colors))
    
    def _analyze_textures(self, character: str) -> List[str]:
        """Анализирует текстурные ассоциации."""
        textures = []
        
        # Прямые ассоциации с известными элементами
        element_chars = {
            "火": "fire", "水": "water", "木": "wood", "金": "metal", "土": "earth",
            "石": "stone", "布": "fabric", "冰": "crystal", "液": "liquid"
        }
        
        for char, element in element_chars.items():
            if char in character:
                textures.extend(self.texture_mappings.get(element, []))
        
        return list(dict.fromkeys(textures))
    
    def _analyze_motion(self, character: str) -> List[str]:
        """Анализирует ассоциации движения."""
        motions = []
        
        # Прямые ассоциации с известными действиями
        motion_chars = {
            "火": "fire", "水": "water", "风": "wind", "走": "walk", "跑": "run",
            "飞": "fly", "落": "fall", "长": "grow", "转": "rotate", "震": "vibrate"
        }
        
        for char, motion in motion_chars.items():
            if char in character:
                motions.extend(self.motion_mappings.get(motion, []))
        
        return list(dict.fromkeys(motions))
    
    def _assess_visual_complexity(self, character: str) -> str:
        """Оценивает визуальную сложность иероглифа."""
        stroke_count = len(character)  # Упрощенная оценка
        
        if stroke_count <= 3:
            return "simple"
        elif stroke_count <= 8:
            return "medium"
        else:
            return "complex"
    
    def _get_dominant_elements(self, colors: List[str], textures: List[str], motions: List[str]) -> Dict[str, str]:
        """Определяет доминирующие визуальные элементы."""
        return {
            "dominant_color": colors[0] if colors else "neutral",
            "dominant_texture": textures[0] if textures else "smooth",
            "dominant_motion": motions[0] if motions else "static"
        }
    
    def get_color_associations(self, meaning: str) -> List[str]:
        """Возвращает цветовые ассоциации для значения."""
        return self.color_mappings.get(meaning.lower(), [])
    
    def get_texture_associations(self, meaning: str) -> List[str]:
        """Возвращает текстурные ассоциации для значения."""
        return self.texture_mappings.get(meaning.lower(), [])
    
    def get_motion_associations(self, meaning: str) -> List[str]:
        """Возвращает ассоциации движения для значения."""
        return self.motion_mappings.get(meaning.lower(), [])
    