"""
Radical analyzer for Chinese characters.
Анализатор радикалов китайских иероглифов.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RadicalResult:
    """Результат анализа радикалов"""
    success: bool
    analysis_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class RadicalAnalyzer:
    """
    Анализатор радикалов Kangxi для китайских иероглифов.
    """
    
    def __init__(self):
        """Инициализация анализатора радикалов."""
        self.kangxi_radicals = self._init_kangxi_radicals()
        logger.info("RadicalAnalyzer initialized")
    
    def _init_kangxi_radicals(self) -> Dict[str, Dict[str, Any]]:
        """Инициализирует базовую базу радикалов Kangxi."""
        return {
            "人": {"number": 9, "strokes": 2, "meaning": "person", "variants": ["亻"]},
            "木": {"number": 75, "strokes": 4, "meaning": "tree", "variants": []},
            "水": {"number": 85, "strokes": 4, "meaning": "water", "variants": ["氵", "氺"]},
            "火": {"number": 86, "strokes": 4, "meaning": "fire", "variants": ["灬"]},
            "土": {"number": 32, "strokes": 3, "meaning": "earth", "variants": []},
            "金": {"number": 167, "strokes": 8, "meaning": "metal", "variants": ["钅"]},
            "日": {"number": 72, "strokes": 4, "meaning": "sun", "variants": []},
            "月": {"number": 74, "strokes": 4, "meaning": "moon", "variants": []},
            "心": {"number": 61, "strokes": 4, "meaning": "heart", "variants": ["忄", "㣺"]},
            "手": {"number": 64, "strokes": 4, "meaning": "hand", "variants": ["扌", "龵"]},
            "口": {"number": 30, "strokes": 3, "meaning": "mouth", "variants": []},
            "目": {"number": 109, "strokes": 5, "meaning": "eye", "variants": []},
            "言": {"number": 149, "strokes": 7, "meaning": "speech", "variants": ["讠"]},
            "山": {"number": 46, "strokes": 3, "meaning": "mountain", "variants": []},
            "川": {"number": 47, "strokes": 3, "meaning": "river", "variants": []},
            "女": {"number": 38, "strokes": 3, "meaning": "woman", "variants": []},
            "子": {"number": 39, "strokes": 3, "meaning": "child", "variants": []},
            "大": {"number": 37, "strokes": 3, "meaning": "big", "variants": []},
            "小": {"number": 42, "strokes": 3, "meaning": "small", "variants": []},
            "刀": {"number": 18, "strokes": 2, "meaning": "knife", "variants": ["刂", "⺈"]},
        }
    
    async def analyze_radicals(self, character: str) -> RadicalResult:
        """
        Анализирует радикалы в иероглифе.
        
        Args:
            character: Иероглиф для анализа
            
        Returns:
            RadicalResult: Результат анализа радикалов
        """
        try:
            detected_radicals = []
            semantic_contributions = []
            
            # Простой поиск известных радикалов в иероглифе
            for radical, info in self.kangxi_radicals.items():
                if radical in character:
                    detected_radicals.append({
                        "radical": radical,
                        "kangxi_number": info["number"],
                        "strokes": info["strokes"],
                        "meaning": info["meaning"],
                        "position": "detected"
                    })
                    
                    semantic_contributions.append({
                        "radical": radical,
                        "meaning": info["meaning"],
                        "semantic_weight": 0.8
                    })
                
                # Проверяем варианты радикала
                for variant in info.get("variants", []):
                    if variant in character:
                        detected_radicals.append({
                            "radical": variant,
                            "base_radical": radical,
                            "kangxi_number": info["number"],
                            "strokes": info["strokes"], 
                            "meaning": info["meaning"],
                            "position": "detected"
                        })
            
            # Если радикалы не найдены, считаем весь иероглиф радикалом
            if not detected_radicals:
                detected_radicals.append({
                    "radical": character,
                    "kangxi_number": 0,
                    "strokes": len(character),
                    "meaning": "unknown",
                    "position": "whole"
                })
            
            analysis_data = {
                "character": character,
                "detected_radicals": detected_radicals,
                "primary_radical": detected_radicals[0] if detected_radicals else None,
                "radical_count": len(detected_radicals),
                "semantic_contributions": semantic_contributions
            }
            
            return RadicalResult(
                success=True,
                analysis_data=analysis_data
            )
            
        except Exception as e:
            logger.error(f"Error analyzing radicals for {character}: {e}")
            return RadicalResult(
                success=False,
                error_message=str(e)
            )
    
    def get_radical_info(self, radical: str) -> Optional[Dict[str, Any]]:
        """Возвращает информацию о конкретном радикале."""
        return self.kangxi_radicals.get(radical)
    
    def get_all_radicals(self) -> Dict[str, Dict[str, Any]]:
        """Возвращает все доступные радикалы."""
        return self.kangxi_radicals.copy()
    