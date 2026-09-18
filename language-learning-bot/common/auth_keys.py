"""Ключи авторизации — одно место для всех сервисов.

Читаются из окружения, а если там нет — прямо из .env проекта. Второе нужно
потому, что systemd читает EnvironmentFile только при старте службы, а сервисы
перезапускаются сами при правке .py и старое окружение сохраняют: новый ключ
дошёл бы до них лишь после sudo systemctl restart. Отсюда он приходит при
первом же автоперезапуске.

Значения кешируются на время жизни процесса — так поведение не меняется
посреди работы, а перезапуск подхватывает новое.
"""

import os
from functools import lru_cache
from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
MODES = ("log", "enforce")


@lru_cache(maxsize=None)
def _file_values() -> dict:
    try:
        from dotenv import dotenv_values
        return dict(dotenv_values(_ENV_FILE)) if _ENV_FILE.exists() else {}
    except Exception:
        return {}


def _get(name: str) -> str:
    return os.environ.get(name) or _file_values().get(name) or ""


def auth_secret() -> str:
    """Ключ подписи токенов пользователей. Знает только BLS."""
    return _get("AUTH_SECRET")


def service_key() -> str:
    """Ключ служб — веба и телеграма. Живёт только на сервере, не в APK."""
    return _get("SERVICE_KEY")


def auth_mode() -> str:
    """log — нарушения пишутся и пропускаются; enforce — отвергаются."""
    mode = _get("AUTH_MODE").strip().lower()
    return mode if mode in MODES else "log"
