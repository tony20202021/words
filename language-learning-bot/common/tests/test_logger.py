"""
Tests for common.utils.logger module.
"""

import pytest
import os
import logging
from unittest.mock import MagicMock, patch, mock_open
import sys
from logging.handlers import RotatingFileHandler

from common.utils.logger import (
    setup_logger,
    get_module_logger
)

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
            