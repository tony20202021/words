"""
AI Generation Result
Результат AI генерации изображения.
"""

import io
import base64
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from PIL import Image

from app.ai.core.generation_config import AIGenerationConfig


@dataclass 
class AIGenerationResult:
    """Результат AI генерации изображения"""
    success: bool
    generated_image_base64: Optional[str] = None
    
    # Промежуточные результаты
    base_image_base64: Optional[str] = None
    conditioning_images_base64: Optional[Dict[str, Dict[str, str]]] = None
    
    # Промпты
    prompt_used: Optional[str] = None
    
    # Translation данные
    translation_used: Optional[str] = None
    translation_source: Optional[str] = None  # "ai_model", "cache", "fallback", etc.
    translation_time_ms: Optional[int] = None
    
    # Метаданные
    generation_metadata: Optional[Dict[str, Any]] = None
    
    # Ошибки и предупреждения
    error_message: Optional[str] = None
    warnings: Optional[List[str]] = None
    
    def __post_init__(self):
        """Инициализация после создания"""
        if self.warnings is None:
            self.warnings = []
    
    @staticmethod
    def _to_base64(image: Image.Image) -> str:
        """Конвертирует изображение в base64"""
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    @staticmethod
    def _conditioning_to_base64(conditioning_images: Dict[str, Dict[str, Image.Image]]) -> Dict[str, Dict[str, str]]:
        """Конвертирует conditioning изображения в base64"""
        result = {}
        for cond_type, cond_data in conditioning_images.items():
            result[cond_type] = {}
            for method, image in cond_data.items():
                if image is not None:
                    result[cond_type][method] = AIGenerationResult._to_base64(image)
                else:
                    result[cond_type][method] = None
        return result
    
    @classmethod
    def create_success_result(
        cls,
        generated_image: Image.Image,
        character: str,
        original_translation: str,
        english_translation: str,
        translation_metadata: Dict[str, Any],
        generation_time_ms: int,
        seed_used: Optional[int],
        model_config: AIGenerationConfig,
        base_image: Optional[Image.Image] = None,
        conditioning_images: Optional[Dict[str, Dict[str, Image.Image]]] = None,
        prompt_used: Optional[str] = None
    ) -> 'AIGenerationResult':
        """
        Создает успешный результат генерации.
        
        Args:
            generated_image: Сгенерированное изображение
            character: Иероглиф
            original_translation: Оригинальный русский перевод
            english_translation: Английский перевод
            translation_metadata: Метаданные перевода
            generation_time_ms: Время генерации
            seed_used: Использованный seed
            model_config: Конфигурация модели
            base_image: Базовое изображение (опционально)
            conditioning_images: Conditioning изображения (опционально)
            prompt_used: Использованный промпт (опционально)
            
        Returns:
            AIGenerationResult: Результат генерации
        """
        return cls(
            success=True,
            generated_image_base64=cls._to_base64(generated_image),
            base_image_base64=cls._to_base64(base_image) if base_image else None,
            conditioning_images_base64=cls._conditioning_to_base64(conditioning_images) if conditioning_images else None,
            prompt_used=prompt_used,
            translation_used=english_translation,
            translation_source=translation_metadata.get('source'),
            translation_time_ms=translation_metadata.get('time_ms'),
            generation_metadata={
                'character': character,
                'original_translation': original_translation,
                'english_translation': english_translation,
                'translation_metadata': translation_metadata,
                'conditioning_methods_used': {
                    conditioning_type: list(conditioning_images[conditioning_type].keys())
                    for conditioning_type in conditioning_images.keys()
                } if conditioning_images else {},
                'generation_time_ms': generation_time_ms,
                'seed_used': seed_used,
                'model_used': model_config.base_model,
                'controlnet_model': "union",
                'image_size': (model_config.width, model_config.height),
            }
        )
    
    @classmethod
    def create_error_result(
        cls,
        character: str,
        original_translation: str,
        error_message: str,
        generation_time_ms: int
    ) -> 'AIGenerationResult':
        """
        Создает результат с ошибкой.
        
        Args:
            character: Иероглиф
            original_translation: Оригинальный перевод
            error_message: Сообщение об ошибке
            generation_time_ms: Время до ошибки
            
        Returns:
            AIGenerationResult: Результат с ошибкой
        """
        return cls(
            success=False,
            error_message=error_message,
            generation_metadata={
                'character': character,
                'original_translation': original_translation,
                'generation_time_ms': generation_time_ms,
                'error_occurred': True
            }
        )
    