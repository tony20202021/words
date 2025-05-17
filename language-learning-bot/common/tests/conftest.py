"""
Конфигурация для запуска pytest с поддержкой тестирования общего модуля.
Этот файл автоматически обнаруживается pytest и загружает определенные здесь фикстуры.
"""

import pytest
import asyncio
import logging
import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Настройка логгирования для тестов
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)

# Импортируем и переэкспортируем mark.asyncio для поддержки асинхронных тестов
pytest_mark_asyncio = pytest.mark.asyncio
