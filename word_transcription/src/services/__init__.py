#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для импорта всех сервисов транскрипции
"""

# Базовый класс
from .base import TranscriptionService

# Основные сервисы
from .dictionary_service import DictionaryService
from .epitran_service import EpitranService
from .forvo_service import ForvoService
from .google_service import GoogleTranslateService
from .wiktionary_service import WiktionaryService

# Новые сервисы
from .g2p_service import G2PService
from .phonemize_service import PhonemizeService
from .easypronunciation_service import EasyPronunciationService
from .ibm_watson_service import IBMWatsonService
from .charsiu_g2p_service import CharsiuG2PService
from .openai_service import OpenAIService

# Экспортируем все классы сервисов
__all__ = [
    'TranscriptionService',
    'DictionaryService',
    'EpitranService',
    'ForvoService',
    'GoogleTranslateService',
    'WiktionaryService',
    'G2PService',
    'PhonemizeService',
    'EasyPronunciationService',
    'IBMWatsonService',
    'CharsiuG2PService',
    'OpenAIService'
]
