"""Пути импорта для тестов BLS.

Из четырёх остальных компонентов такой conftest есть у каждого, а у BLS не было.
Полный прогон это скрывал: `pytest` без аргументов подхватывает корневой
pyproject.toml и собирает всё, а вот `--specific tests/test_card_builder.py`
падал с `No module named 'common'`. То есть запустить один файл было нельзя,
и выглядело это как сломанный тест, а не как сломанный запуск.

Первая строка — сам компонент (`app.*`), вторая — корень репозитория
(`common.*`).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
