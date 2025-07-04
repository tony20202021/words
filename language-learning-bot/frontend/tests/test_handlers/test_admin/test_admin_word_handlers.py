"""
Unit tests for language management admin handlers.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from unittest.mock import MagicMock, AsyncMock, patch

from aiogram.types import Message, User, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.bot.handlers.admin.admin_language_handlers import (
    cmd_manage_languages, process_create_language, process_language_name,
    process_language_native_name, process_edit_language,
    process_edit_name_ru, process_edit_language_name,
    process_delete_language,
    process_confirm_delete_language, process_cancel_delete_language
)
from app.bot.states.centralized_states import AdminStates


class TestLanguageAdminHandlers:
    """Tests for the language management admin handlers."""
    
    @pytest.fixture
    def setup_mocks(self):
        """Set up common mocks for tests."""
        # Mock message
        message = MagicMock(spec=Message)
        message.answer = AsyncMock()
        message.from_user = MagicMock(spec=User)
        message.from_user.id = 12345
        message.from_user.username = "admin_user"
        message.from_user.first_name = "Admin"
        message.from_user.last_name = "User"
        message.from_user.full_name = "Admin User"
        message.bot = MagicMock()
        
        # Mock state
        state = MagicMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={})
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()
        state.clear = AsyncMock()
        
        # Mock API client с новым форматом ответа
        api_client = AsyncMock()
        api_client.get_user_by_telegram_id = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [],
            "error": None
        })
        api_client.create_user = AsyncMock(return_value={
            "success": True,
            "status": 201,
            "result": {"id": "user123"},
            "error": None
        })
        api_client.get_languages = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [],
            "error": None
        })
        api_client.get_language = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": None,
            "error": None
        })
        api_client.create_language = AsyncMock(return_value={
            "success": True,
            "status": 201,
            "result": {},
            "error": None
        })
        api_client.update_language = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {},
            "error": None
        })
        api_client.delete_language = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {},
            "error": None
        })
        
        # Mock callback
        callback = MagicMock(spec=CallbackQuery)
        callback.answer = AsyncMock()
        callback.message = message
        callback.from_user = message.from_user
        callback.data = "create_language"
        
        return message, state, api_client, callback
    
    @pytest.mark.asyncio
    async def test_process_word_number_input(self, setup_mocks):
        """Test the process_word_number_input handler."""
        message, state, api_client, _ = setup_mocks

        message.text = "5"
        
        # Patch required functions
        with patch('app.bot.handlers.admin.admin_word_handlers.process_word_field_update', return_value=api_client) as mock_process_word_field_update:
            
            # Call the handler
            from app.bot.handlers.admin.admin_word_handlers import process_word_number_input
            await process_word_number_input(message, state)
            
            # Verify API calls
            mock_process_word_field_update.assert_called_once()
