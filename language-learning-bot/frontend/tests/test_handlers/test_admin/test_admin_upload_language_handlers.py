"""
Unit tests for file upload admin handlers.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from aiogram import Dispatcher
from aiogram.types import Message, User, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.bot.states.centralized_states import AdminStates

class TestUploadAdminHandlers:
    """Tests for the file upload admin handlers."""
    
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
        message.document = None
        
        # Mock state
        state = MagicMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={})
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()
        state.clear = AsyncMock()
        
        # Mock API client with new response format
        api_client = AsyncMock()
        api_client.get_user_by_telegram_id = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": None,
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
        api_client.upload_words_file = AsyncMock(return_value={
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
        callback.data = "upload_to_lang_lang1"
        
        # Mock document message
        document_message = MagicMock(spec=Message)
        document_message.answer = AsyncMock()
        document_message.from_user = message.from_user
        document_message.bot = message.bot
        document_message.document = MagicMock()
        document_message.document.file_name = "words.xlsx"
        document_message.document.file_id = "file123"
        document_message.bot.get_file = AsyncMock()
        document_message.bot.download_file = AsyncMock()
        
        return message, state, api_client, callback, document_message

    @pytest.mark.asyncio
    async def test_process_language_selection_for_upload(self, setup_mocks):
        """Test the process_language_selection_for_upload handler."""
        _, state, api_client, callback, _ = setup_mocks
        
        # Set callback data
        callback.data = "upload_to_lang_lang1"
        
        # Mock API responses - successful language retrieval
        api_client.get_language.return_value = {
            "success": True,
            "status": 200,
            "result": {
                "id": "lang1",
                "name_ru": "Английский",
                "name_foreign": "English"
            },
            "error": None
        }
        
        # Patch the logger and API client
        with patch('app.bot.handlers.admin.file_upload.language_selection.get_api_client_from_bot', return_value=api_client), \
            patch('app.bot.handlers.admin.file_upload.language_selection.logger'):
            
            # Call the handler
            from app.bot.handlers.admin.file_upload.language_selection import process_language_selection_for_upload
            await process_language_selection_for_upload(callback, state)
            
            # Verify API calls
            api_client.get_language.assert_called_once_with("lang1")
            
            # Check that state was updated with selected language ID
            state.update_data.assert_called_once_with(selected_language_id="lang1")
            
            # Check that state was set to waiting_file
            state.set_state.assert_called_once_with(AdminStates.waiting_file)
            
            # Check that the message contains instructions for file upload
            callback.message.answer.assert_called_once()
            answer_text = callback.message.answer.call_args.args[0]
            assert "Отправьте Excel-файл со списком слов для языка: Английский" in answer_text
            assert "Формат: .xlsx" in answer_text
            assert "Требования к файлу" in answer_text
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()