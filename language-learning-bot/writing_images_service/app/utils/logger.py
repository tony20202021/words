"""
Writing service logger wrapper for backward compatibility.
This file re-exports utilities from the common logger module.
"""

import sys
import os
from pathlib import Path

# Добавляем путь к корневой директории проекта для импорта common
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from common.utils.logger import setup_logger, get_module_logger

# Экспортируем функции для обратной совместимости
__all__ = ['setup_logger', 'get_module_logger']
