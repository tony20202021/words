"""
Unit tests for main admin upload handlers module.
"""

import pytest
from unittest.mock import MagicMock
from aiogram import Dispatcher, Router
import app.bot.handlers.admin.admin_upload_handlers as admin_upload_handlers

class TestAdminUploadHandlers:
    """Tests for the admin upload handlers module."""
    
    def test_upload_router_structure(self):
        """Test that upload_router has all necessary sub-routers."""
        # Check that the module has all expected router attributes
        assert hasattr(admin_upload_handlers, 'file_router')
        assert hasattr(admin_upload_handlers, 'language_router')
        assert hasattr(admin_upload_handlers, 'column_router')
        assert hasattr(admin_upload_handlers, 'column_type_router')
        assert hasattr(admin_upload_handlers, 'settings_router')
        assert hasattr(admin_upload_handlers, 'template_router')
        
        # Check that all routers are instances of aiogram Router
        assert isinstance(admin_upload_handlers.file_router, Router)
        assert isinstance(admin_upload_handlers.language_router, Router)
        assert isinstance(admin_upload_handlers.column_router, Router)
        assert isinstance(admin_upload_handlers.column_type_router, Router)
        assert isinstance(admin_upload_handlers.settings_router, Router)
        assert isinstance(admin_upload_handlers.template_router, Router)
        
        # Check that upload_router is also a Router
        assert isinstance(admin_upload_handlers.upload_router, Router)
    
    def test_register_handlers(self):
        """Test the register_handlers function in admin_handlers."""
        # Create a mock dispatcher
        dp = MagicMock(spec=Dispatcher)
        dp.include_router = MagicMock()
        
        # Import the register_handlers function from admin_handlers
        from app.bot.handlers.admin_handlers import register_handlers
        
        # Call the function
        register_handlers(dp)
        
        # Check that include_router was called
        dp.include_router.assert_called_once()
        