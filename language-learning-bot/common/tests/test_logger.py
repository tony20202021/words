"""
Tests for common.utils.logger module.
"""

import pytest
import os
import logging
from unittest.mock import MagicMock, patch, mock_open
import sys
from logging.handlers import RotatingFileHandler

from common.utils import logger as logger_module
from common.utils.logger import (
    setup_logger,
    get_module_logger
)


@pytest.fixture(autouse=True)
def reset_logger_module_state():
    """
    setup_logger хранит настройки уровня приложения в модульном состоянии.
    Сбрасываем его между тестами, чтобы тесты не зависели от порядка запуска.
    """
    saved_defaults = dict(logger_module._app_defaults)
    saved_managed = dict(logger_module._managed_loggers)
    logger_module._managed_loggers.clear()

    yield

    # Убираем хендлеры и уровни, выставленные тестом на настоящих логгерах
    for entry in logger_module._managed_loggers.values():
        configured = entry["logger"]
        for handler in list(getattr(configured, "handlers", []) or []):
            configured.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass
        configured.setLevel(logging.NOTSET)

    logger_module._managed_loggers.clear()
    logger_module._managed_loggers.update(saved_managed)
    logger_module._app_defaults.clear()
    logger_module._app_defaults.update(saved_defaults)


class TestSetupLogger:
    
    def test_setup_logger_basic(self):
        """Проверка базовой функциональности setup_logger."""
        # Setup
        logger_name = "test_logger"
        
        # Патчим logging.getLogger для возврата контролируемого логгера
        mock_logger = MagicMock(spec=logging.Logger)
        mock_logger.handlers = []  # Логгер без хендлеров (еще не настроен)
        
        # Создаем моки для хендлеров
        mock_console_handler = MagicMock()
        mock_file_handler = MagicMock()
        
        # Настраиваем патчи
        with patch('logging.getLogger', return_value=mock_logger) as mock_get_logger, \
             patch('logging.StreamHandler', return_value=mock_console_handler) as mock_stream_handler, \
             patch('os.makedirs') as mock_makedirs, \
             patch('common.utils.logger.RotatingFileHandler', return_value=mock_file_handler) as mock_rotating_handler:
        
            # Execute
            result = setup_logger(logger_name)
            
            # Verify
            mock_get_logger.assert_called_once_with(logger_name)
            assert result == mock_logger
            
            # Проверяем, что логгер настроен правильно
            mock_logger.setLevel.assert_called_once_with(logging.INFO)
            
            # Проверяем, что создатели хендлеров вызваны
            mock_stream_handler.assert_called_once()
            mock_rotating_handler.assert_called_once()
            
            # Проверяем, что оба хендлера добавлены
            mock_logger.addHandler.assert_any_call(mock_console_handler)
            mock_logger.addHandler.assert_any_call(mock_file_handler)
            assert mock_logger.addHandler.call_count == 2
            
            # Проверяем, что директория для логов создана
            mock_makedirs.assert_called_once_with("logs", exist_ok=True)
    
    def test_setup_logger_console_only(self):
        """Проверка setup_logger с отключенным файловым логированием."""
        # Setup
        logger_name = "test_logger"
        log_to_file = False
        
        # Патчим logging.getLogger для возврата контролируемого логгера
        mock_logger = MagicMock(spec=logging.Logger)
        mock_logger.handlers = []  # Логгер без хендлеров (еще не настроен)
        
        # Создаем мок для консольного хендлера
        mock_console_handler = MagicMock()
        
        # Настраиваем патчи
        with patch('logging.getLogger', return_value=mock_logger) as mock_get_logger, \
             patch('logging.StreamHandler', return_value=mock_console_handler) as mock_stream_handler, \
             patch('os.makedirs') as mock_makedirs, \
             patch('common.utils.logger.RotatingFileHandler') as mock_rotating_handler:
            
            # Execute
            result = setup_logger(logger_name, log_to_file=log_to_file)
            
            # Verify
            mock_get_logger.assert_called_once_with(logger_name)
            assert result == mock_logger
            
            # Проверяем, что логгер настроен правильно
            mock_logger.setLevel.assert_called_once_with(logging.INFO)
            
            # Проверяем, что только консольный хендлер создан и добавлен
            mock_stream_handler.assert_called_once()
            mock_rotating_handler.assert_not_called()
            
            # Проверяем, что добавлен только консольный хендлер
            mock_logger.addHandler.assert_called_once_with(mock_console_handler)
            
            # Проверяем, что директория для логов не создавалась
            mock_makedirs.assert_not_called()
    
    def test_setup_logger_with_custom_level(self):
        """Проверка setup_logger с настраиваемым уровнем логирования."""
        # Setup
        logger_name = "test_logger"
        log_level = logging.DEBUG
        
        # Патчим logging.getLogger для возврата контролируемого логгера
        mock_logger = MagicMock(spec=logging.Logger)
        mock_logger.handlers = []  # Логгер без хендлеров (еще не настроен)
        
        # Создаем моки для хендлеров
        mock_console_handler = MagicMock()
        mock_file_handler = MagicMock()
        
        # Настраиваем патчи
        with patch('logging.getLogger', return_value=mock_logger) as mock_get_logger, \
             patch('logging.StreamHandler', return_value=mock_console_handler) as mock_stream_handler, \
             patch('os.makedirs') as mock_makedirs, \
             patch('common.utils.logger.RotatingFileHandler', return_value=mock_file_handler) as mock_rotating_handler:
            
            # Execute
            result = setup_logger(logger_name, log_level=log_level)
            
            # Verify
            mock_get_logger.assert_called_once_with(logger_name)
            assert result == mock_logger
            
            # Проверяем, что логгер настроен правильно
            mock_logger.setLevel.assert_called_once_with(log_level)
            
            # Проверяем, что хендлеры добавлены
            assert mock_logger.addHandler.call_count == 2
    
    def test_setup_logger_with_string_level(self):
        """Проверка setup_logger с уровнем логирования в виде строки."""
        # Setup
        logger_name = "test_logger"
        log_level = "DEBUG"
        
        # Патчим logging.getLogger для возврата контролируемого логгера
        mock_logger = MagicMock(spec=logging.Logger)
        mock_logger.handlers = []  # Логгер без хендлеров (еще не настроен)
        
        # Создаем моки для хендлеров
        mock_console_handler = MagicMock()
        mock_file_handler = MagicMock()
        
        # Настраиваем патчи
        with patch('logging.getLogger', return_value=mock_logger) as mock_get_logger, \
             patch('logging.StreamHandler', return_value=mock_console_handler) as mock_stream_handler, \
             patch('os.makedirs') as mock_makedirs, \
             patch('common.utils.logger.RotatingFileHandler', return_value=mock_file_handler) as mock_rotating_handler:
            
            # Execute
            result = setup_logger(logger_name, log_level=log_level)
            
            # Verify
            mock_get_logger.assert_called_once_with(logger_name)
            assert result == mock_logger
            
            # Проверяем, что логгер настроен правильно с преобразованным уровнем логирования
            mock_logger.setLevel.assert_called_once_with(logging.DEBUG)
    
    def test_setup_logger_already_configured(self):
        """Проверка setup_logger с уже настроенным логгером."""
        # Setup
        logger_name = "test_logger"
        
        # Патчим logging.getLogger для возврата контролируемого логгера
        mock_logger = MagicMock(spec=logging.Logger)
        mock_logger.handlers = [MagicMock()]  # Логгер уже имеет хендлеры
        
        # Настраиваем патчи
        with patch('logging.getLogger', return_value=mock_logger) as mock_get_logger, \
             patch('logging.StreamHandler') as mock_stream_handler, \
             patch('common.utils.logger.RotatingFileHandler') as mock_rotating_handler:
            
            # Execute
            result = setup_logger(logger_name)
            
            # Verify
            mock_get_logger.assert_called_once_with(logger_name)
            assert result == mock_logger
            
            # Проверяем, что логгер не был настроен повторно
            mock_logger.setLevel.assert_not_called()
            mock_logger.addHandler.assert_not_called()
            mock_stream_handler.assert_not_called()
            mock_rotating_handler.assert_not_called()
    
    def test_setup_logger_file_error(self):
        """Проверка setup_logger с ошибкой при создании файлового логгера."""
        # Setup
        logger_name = "test_logger"
        
        # Патчим logging.getLogger для возврата контролируемого логгера
        mock_logger = MagicMock(spec=logging.Logger)
        mock_logger.handlers = []  # Логгер без хендлеров (еще не настроен)
        
        # Создаем мок для консольного хендлера
        mock_console_handler = MagicMock()
        
        # Настраиваем патчи
        with patch('logging.getLogger', return_value=mock_logger) as mock_get_logger, \
             patch('logging.StreamHandler', return_value=mock_console_handler) as mock_stream_handler, \
             patch('os.makedirs', side_effect=Exception("Test error")) as mock_makedirs:
            
            # Execute
            result = setup_logger(logger_name)
            
            # Verify
            mock_get_logger.assert_called_once_with(logger_name)
            assert result == mock_logger
            
            # Проверяем, что консольный хендлер добавлен
            assert mock_logger.addHandler.call_count == 1
            mock_logger.addHandler.assert_called_once_with(mock_console_handler)
            
            # Проверяем, что логируются ошибки
            mock_logger.error.assert_called_once()
            mock_logger.warning.assert_called_once()


class TestApplicationWideSettings:
    """
    Модули зовут setup_logger(__name__) на импорте, точка входа читает конфиг
    позже. Явно переданные общие настройки должны догонять уже созданные логгеры
    и применяться к создаваемым дальше.
    """

    def test_explicit_level_applies_to_already_configured_loggers(self):
        """Уровень из конфига применяется к логгерам, настроенным до точки входа."""
        module_logger = setup_logger("llb_level_test.module", log_to_file=False)
        assert module_logger.level == logging.INFO

        # Точка входа прочитала конфиг и настроила логирование
        setup_logger("llb_level_test.main", log_level="DEBUG", log_to_file=False)

        assert module_logger.level == logging.DEBUG
        assert module_logger.isEnabledFor(logging.DEBUG)

    def test_explicit_level_becomes_default_for_later_loggers(self):
        """Уровень из конфига становится значением по умолчанию для новых логгеров."""
        setup_logger("llb_default_test.main", log_level="DEBUG", log_to_file=False)

        later_logger = setup_logger("llb_default_test.module", log_to_file=False)

        assert later_logger.level == logging.DEBUG

    def test_explicit_level_reconfigures_same_logger_without_duplicates(self):
        """Повторный вызов с явным уровнем меняет уровень, но не плодит хендлеры."""
        logger_name = "llb_reconfig_test.module"
        module_logger = setup_logger(logger_name, log_to_file=False)
        handlers_before = list(module_logger.handlers)
        assert module_logger.level == logging.INFO

        same_logger = setup_logger(logger_name, log_level="DEBUG", log_to_file=False)

        assert same_logger is module_logger
        assert module_logger.level == logging.DEBUG
        assert list(module_logger.handlers) == handlers_before

    def test_explicit_format_applies_to_already_configured_loggers(self):
        """Формат из конфига применяется к логгерам, настроенным до точки входа."""
        module_logger = setup_logger("llb_format_test.module", log_to_file=False)
        custom_format = "%(name)s :: %(message)s"

        setup_logger("llb_format_test.main", log_format=custom_format, log_to_file=False)

        assert module_logger.handlers
        for handler in module_logger.handlers:
            assert handler.formatter._fmt == custom_format

    def test_explicit_log_dir_moves_files_of_already_configured_loggers(self, tmp_path):
        """Каталог логов из конфига применяется к логгерам, настроенным до точки входа."""
        early_dir = tmp_path / "early"
        configured_dir = tmp_path / "configured"

        module_logger = setup_logger("llb_dir_test.module", log_dir=str(early_dir))
        file_handlers = [h for h in module_logger.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 1
        assert os.path.dirname(file_handlers[0].baseFilename) == os.path.abspath(str(early_dir))

        setup_logger("llb_dir_test.main", log_level="DEBUG", log_dir=str(configured_dir))

        file_handlers = [h for h in module_logger.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 1
        assert os.path.dirname(file_handlers[0].baseFilename) == os.path.abspath(str(configured_dir))
        assert os.path.basename(file_handlers[0].baseFilename) == "module.log"


class TestGetModuleLogger:
    
    def test_get_module_logger(self):
        """Проверка get_module_logger."""
        # Setup
        module_name = "test_module"
        mock_logger = MagicMock()
        
        # Патчим setup_logger для возврата контролируемого логгера
        with patch('common.utils.logger.setup_logger', return_value=mock_logger) as mock_setup_logger:
            # Execute
            result = get_module_logger(module_name)
            
            # Verify
            mock_setup_logger.assert_called_once_with(module_name)
            assert result == mock_logger
            