"""
Tests for logger module.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.utils.logger import (
    setup_logger,
    get_module_logger
)

import common.utils.logger

class TestLoggerModule:
    
    def test_setup_logger_is_reexported(self):
        # Verify that app.utils.logger.setup_logger is the same as common.utils.logger.setup_logger
        assert setup_logger is common.utils.logger.setup_logger
    
    def test_get_module_logger_is_reexported(self):
        # Verify that app.utils.logger.get_module_logger is the same as common.utils.logger.get_module_logger
        assert get_module_logger is common.utils.logger.get_module_logger
        