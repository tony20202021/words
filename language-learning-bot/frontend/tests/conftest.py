"""
Конфигурация для запуска pytest с поддержкой асинхронного тестирования.
Этот файл автоматически обнаруживается pytest и загружает определенные здесь фикстуры.
"""

import pytest
import asyncio
import logging
import sys
import os

# Добавляем корневую директорию проекта в sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Настройка логгирования для тестов
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)

# Импортируем и переэкспортируем mark.asyncio
pytest_mark_asyncio = pytest.mark.asyncio