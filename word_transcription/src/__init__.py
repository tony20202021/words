#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Инициализация модуля src
"""

# Импортируем модуль transcription_script для удобного доступа
from .transcription_script import main, process_words, load_json_file, save_json_file

# Импортируем TranscriptionManager
from .transcription_manager import TranscriptionManager

# Импортируем утилиты
from .utils import *

# Экспортируем основные функции и классы
__all__ = [
    'main',
    'process_words',
    'load_json_file',
    'save_json_file',
    'TranscriptionManager'
]
