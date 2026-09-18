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

# Ключи авторизации — тестовые, заведомо не боевые. Задаются ПРИНУДИТЕЛЬНО, а не
# «если не задано»: иначе common/auth_keys прочёл бы настоящий .env, и когда на
# сервере включат AUTH_MODE=enforce, все прежние тесты (они шлют запросы без
# удостоверений) разом упали бы с 401. Тесты не должны зависеть от боевой
# настройки. Принуждение проверяется отдельно, в test_auth_guard.py.
os.environ["AUTH_SECRET"] = "test-auth-secret-not-for-production"
os.environ["SERVICE_KEY"] = "test-service-key-not-for-production"
os.environ["AUTH_MODE"] = "log"
