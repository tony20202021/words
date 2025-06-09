"""
Etymology analyzer for Chinese characters.
Этимологический анализатор китайских иероглифов.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EtymologyResult:
    """Результат этимологического анализа"""
    success: bool
    analysis_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class EtymologyAnalyzer:
    """
    Этимологический анализатор китайских иероглифов.
    """
    
    def __init__(self):
        """Инициализация этимологического анализатора."""
        self.etymology_data = self._init_etymology_data()
        logger.info("EtymologyAnalyzer initialized")
    
    def _init_etymology_data(self) -> Dict[str, Dict[str, Any]]:
        """Инициализирует базовые этимологические данные."""
        return {
            "火": {
                "type": "pictographic",
                "original_meaning": "fire, flames",
                "visual_origin": "stylized representation of flickering flames",
                "evolution": ["ancient pictograph", "seal script", "modern form"],
                "historical_period": "ancient",
                "is_pictographic": True,
                "is_ideographic": False,
                "is_compound": False
            },
            "水": {
                "type": "pictographic", 
                "original_meaning": "water, flowing liquid",
                "visual_origin": "curved lines representing flowing water",
                "evolution": ["ancient pictograph", "seal script", "modern form"],
                "historical_period": "ancient",
                "is_pictographic": True,
                "is_ideographic": False,
                "is_compound": False
            },
            "木": {
                "type": "pictographic",
                "original_meaning": "tree, wood",
                "visual_origin": "tree with trunk, branches and roots",
                "evolution": ["ancient pictograph", "seal script", "modern form"],
                "historical_period": "ancient",
                "is_pictographic": True,
                "is_ideographic": False,
                "is_compound": False
            },
            "人": {
                "type": "pictographic",
                "original_meaning": "person, human being",
                "visual_origin": "side view of a walking person",
                "evolution": ["ancient pictograph", "seal script", "modern form"],
                "historical_period": "ancient",
                "is_pictographic": True,
                "is_ideographic": False,
                "is_compound": False
            },
            "日": {
                "type": "pictographic",
                "original_meaning": "sun, day",
                "visual_origin": "circular shape representing the sun",
                "evolution": ["ancient pictograph", "seal script", "modern form"],
                "historical_period": "ancient",
                "is_pictographic": True,
                "is_ideographic": False,
                "is_compound": False
            },
            "月": {
                "type": "pictographic",
                "original_meaning": "moon, month",
                "visual_origin": "crescent moon shape",
                "evolution": ["ancient pictograph", "seal script", "modern form"],
                "historical_period": "ancient",
                "is_pictographic": True,
                "is_ideographic": False,
                "is_compound": False
            },
            "明": {
                "type": "compound_ideographic",
                "original_meaning": "bright, clear, intelligent",
                "visual_origin": "sun and moon together representing brightness",
                "evolution": ["compound formation", "seal script", "modern form"],
                "historical_period": "ancient",
                "is_pictographic": False,
                "is_ideographic": True,
                "is_compound": True,
                "components": ["日", "月"]
            },
            "好": {
                "type": "compound_ideographic",
                "original_meaning": "good, well",
                "visual_origin": "woman and child representing goodness",
                "evolution": ["compound formation", "seal script", "modern form"],
                "historical_period": "ancient",
                "is_pictographic": False,
                "is_ideographic": True,
                "is_compound": True,
                "components": ["女", "子"]
            }
        }
    
    async def analyze_etymology(self, character: str) -> EtymologyResult:
        """
        Анализирует этимологию иероглифа.
        
        Args:
            character: Иероглиф для анализа
            
        Returns:
            EtymologyResult: Результат этимологического анализа
        """
        try:
            etymology = self.etymology_data.get(character, {})
            
            if not etymology:
                # Базовый анализ для неизвестных иероглифов
                etymology = {
                    "type": "unknown",
                    "original_meaning": "unknown",
                    "visual_origin": "unknown",
                    "evolution": ["unknown"],
                    "historical_period": "unknown",
                    "is_pictographic": False,
                    "is_ideographic": False,
                    "is_compound": False
                }
            
            analysis_data = {
                "character": character,
                "etymology_type": etymology.get("type", "unknown"),
                "original_meaning": etymology.get("original_meaning", ""),
                "visual_origin": etymology.get("visual_origin", ""),
                "character_evolution": etymology.get("evolution", []),
                "historical_period": etymology.get("historical_period", ""),
                "formation_type": {
                    "is_pictographic": etymology.get("is_pictographic", False),
                    "is_ideographic": etymology.get("is_ideographic", False),
                    "is_compound": etymology.get("is_compound", False)
                },
                "components": etymology.get("components", []),
                "modern_meanings": self._get_derived_meanings(character, etymology)
            }
            
            return EtymologyResult(
                success=True,
                analysis_data=analysis_data
            )
            
        except Exception as e:
            logger.error(f"Error analyzing etymology for {character}: {e}")
            return EtymologyResult(
                success=False,
                error_message=str(e)
            )
    
    def _get_derived_meanings(self, character: str, etymology: Dict[str, Any]) -> List[str]:
        """Получает производные значения на основе этимологии."""
        derived_meanings = []
        
        original = etymology.get("original_meaning", "")
        if original:
            derived_meanings.append(original)
        
        # Простые производные значения
        meaning_extensions = {
            "fire": ["heat", "energy", "passion", "anger"],
            "water": ["liquid", "flow", "pure", "calm"],
            "tree": ["wood", "plant", "growth", "nature"],
            "person": ["human", "people", "individual", "character"],
            "sun": ["light", "day", "bright", "warm"],
            "moon": ["night", "cycle", "feminine", "gentle"]
        }
        
        for base, extensions in meaning_extensions.items():
            if base in original.lower():
                derived_meanings.extend(extensions)
        
        return derived_meanings[:5]  # Ограничиваем до 5 значений
    
    def get_etymology_info(self, character: str) -> Optional[Dict[str, Any]]:
        """Возвращает этимологическую информацию о конкретном иероглифе."""
        return self.etymology_data.get(character)
    
    def is_pictographic(self, character: str) -> bool:
        """Проверяет является ли иероглиф пиктограммой."""
        etymology = self.etymology_data.get(character, {})
        return etymology.get("is_pictographic", False)
    
    def is_compound(self, character: str) -> bool:
        """Проверяет является ли иероглиф составным."""
        etymology = self.etymology_data.get(character, {})
        return etymology.get("is_compound", False)
    