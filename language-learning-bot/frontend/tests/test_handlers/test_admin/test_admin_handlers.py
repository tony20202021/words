"""
Unit tests for main admin handlers module.
"""

import pytest
from unittest.mock import MagicMock, patch
from aiogram import Dispatcher
import app.bot.handlers.admin_handlers as admin_handlers


class TestAdminHandlersMain:
    """Tests for the main admin handlers module."""
    
    def test_register_handlers(self):
        """Test the register_handlers function."""
        # Create a mock dispatcher
        dp = MagicMock(spec=Dispatcher)
        dp.include_router = MagicMock()
        
        # Call the register_handlers function
        admin_handlers.register_handlers(dp)
        
        # Check that include_router was called with the admin_router
        dp.include_router.assert_called_once_with(admin_handlers.admin_router)