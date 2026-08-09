"""
Unified logging utilities for Language Learning Bot.

This module provides setup functions for configuring application logging,
supporting both console and file output with customizable log levels.
It is shared between frontend and backend components.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Union

# Маркер "аргумент не передан" — отличает явное значение от значения по умолчанию.
_UNSET = object()

DEFAULT_LOG_FORMAT = '%(asctime)s{%(levelname)s}[%(filename)s:%(lineno)d]: %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Настройки логирования уровня приложения.
#
# Модули зовут setup_logger(__name__) прямо на импорте, то есть ДО того, как
# точка входа успевает прочитать конфиг. Поэтому явно переданные общие настройки
# (уровень, каталог, формат, параметры ротации) считаются настройкой всего
# приложения: они становятся значениями по умолчанию для логгеров, созданных
# позже, и применяются к уже созданным. Локальный для вызова log_to_file сюда
# не входит: нужен ли конкретному логгеру файл — дело самого логгера.
_app_defaults = {
    "log_level": logging.INFO,
    "log_dir": "logs",
    "log_format": None,
    "log_file_max_size": 5 * 1024 * 1024,  # 5 MB
    "log_file_backup_count": 3,
}

# Логгеры, настроенные через setup_logger: name -> запись с логгером и его хендлерами.
_managed_loggers = {}


def _coerce_log_level(log_level: Union[int, str]) -> int:
    """Convert a string log level to its numeric value."""
    if isinstance(log_level, str):
        return getattr(logging, log_level.upper(), logging.INFO)
    return log_level


def _build_formatter(log_format: str = None) -> logging.Formatter:
    """Build a formatter for the given format string (or the default one)."""
    return logging.Formatter(log_format or DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)


def _build_file_handler(name: str, log_dir: str, formatter: logging.Formatter) -> RotatingFileHandler:
    """Create a rotating file handler for the given logger name."""
    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    # Determine log filename based on module name
    log_filename = os.path.join(log_dir, f"{name.split('.')[-1]}.log")

    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=_app_defaults["log_file_max_size"],
        backupCount=_app_defaults["log_file_backup_count"],
    )
    file_handler.setFormatter(formatter)
    return file_handler


def _move_file_handler(entry: dict) -> None:
    """Re-create the file handler of an already configured logger in the current log_dir."""
    file_handler = entry["file_handler"]
    new_log_dir = _app_defaults["log_dir"]
    if file_handler is None or entry["log_dir"] == new_log_dir:
        return

    logger = entry["logger"]
    try:
        new_handler = _build_file_handler(
            entry["name"], new_log_dir, _build_formatter(_app_defaults["log_format"])
        )
    except Exception as e:
        logger.error(f"Failed to move file logging to {new_log_dir}: {e}")
        return

    logger.removeHandler(file_handler)
    try:
        file_handler.close()
    except Exception:
        pass
    logger.addHandler(new_handler)
    entry["handlers"] = [h for h in entry["handlers"] if h is not file_handler] + [new_handler]
    entry["file_handler"] = new_handler
    entry["log_dir"] = new_log_dir


def _apply_app_defaults(skip: dict = None) -> None:
    """Apply the current application-wide settings to already configured loggers."""
    formatter = _build_formatter(_app_defaults["log_format"])
    for entry in list(_managed_loggers.values()):
        if entry is skip:
            continue
        entry["logger"].setLevel(_app_defaults["log_level"])
        for handler in entry["handlers"]:
            handler.setFormatter(formatter)
        _move_file_handler(entry)


def setup_logger(
    name: str,
    log_level: Union[int, str] = _UNSET,
    log_to_file: bool = True,
    log_dir: str = _UNSET,
    log_format: str = _UNSET,
    log_file_max_size: int = _UNSET,
    log_file_backup_count: int = _UNSET,
) -> logging.Logger:
    """
    Set up and configure a logger with custom formatting and handlers.

    Явно переданные общие настройки (log_level, log_dir, log_format, параметры
    ротации) задают конфигурацию всего приложения: они применяются и к логгерам,
    настроенным ранее (модули настраиваются на импорте, до чтения конфига точкой
    входа), и становятся значениями по умолчанию для логгеров, созданных позже.
    Без явных аргументов уже настроенный логгер не трогается.

    Args:
        name: Name of the logger, typically the module name using __name__
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL); default INFO
        log_to_file: Whether to log to a file or not (only for this logger)
        log_dir: Directory to store log files; default "logs"
        log_format: Custom format for log messages (optional)
        log_file_max_size: Maximum size of log file before rotation in bytes
        log_file_backup_count: Number of backup files to keep

    Returns:
        Configured logger instance
    """
    explicit = {
        key: value
        for key, value in (
            ("log_level", log_level),
            ("log_dir", log_dir),
            ("log_format", log_format),
            ("log_file_max_size", log_file_max_size),
            ("log_file_backup_count", log_file_backup_count),
        )
        if value is not _UNSET
    }
    if "log_level" in explicit:
        # Convert string log level to its numeric value if needed
        explicit["log_level"] = _coerce_log_level(explicit["log_level"])
    _app_defaults.update(explicit)

    # Create logger instance
    logger = logging.getLogger(name)

    skip = None
    if not logger.handlers:
        # Configure the logger: it has no handlers yet
        logger.setLevel(_app_defaults["log_level"])

        formatter = _build_formatter(_app_defaults["log_format"])

        # Setup console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        handlers = [console_handler]
        file_handler = None

        # Setup file handler if requested
        if log_to_file:
            try:
                file_handler = _build_file_handler(name, _app_defaults["log_dir"], formatter)
            except Exception as e:
                # Log error but continue without file logging
                file_handler = None
                logger.error(f"Failed to setup file logging: {e}")
                logger.warning("Continuing with console logging only")
            else:
                logger.addHandler(file_handler)
                handlers.append(file_handler)

        skip = {
            "name": name,
            "logger": logger,
            "handlers": handlers,
            "file_handler": file_handler,
            "log_dir": _app_defaults["log_dir"] if file_handler is not None else None,
        }
        _managed_loggers[name] = skip
    elif explicit and name not in _managed_loggers:
        # Логгер настроен не нами — хендлеры чужие, но уровень применить обязаны.
        logger.setLevel(_app_defaults["log_level"])

    if explicit:
        _apply_app_defaults(skip=skip)

    return logger


def get_module_logger(module_name: str) -> logging.Logger:
    """
    Get a logger for a specific module, using the default configuration.

    Args:
        module_name: Name of the module, typically __name__

    Returns:
        Configured logger instance
    """
    return setup_logger(module_name)
