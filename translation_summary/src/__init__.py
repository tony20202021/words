#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Пакет для генерации кратких переводов китайских слов
с использованием языковых моделей из Hugging Face.
"""

from .llm_translator import LLMTranslator, get_available_models
from .model_config import AVAILABLE_MODELS, MODEL_TYPES

__version__ = "1.0.0"
__author__ = "Translation Team"

__all__ = [
    "LLMTranslator",
    "get_available_models", 
    "AVAILABLE_MODELS",
    "MODEL_TYPES"
]
