"""
Unit tests for file upload admin handlers.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from aiogram import Dispatcher
from aiogram.types import Message, User, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Импортируем роутеры вместо отдельных функций
from app.bot.handlers.admin.admin_upload_handlers import upload_router

# Импортируем функции из соответствующих модулей
from app.bot.handlers.admin.file_upload.file_processing import cmd_upload, process_file_upload
from app.bot.handlers.admin.file_upload.language_selection import process_language_selection_for_upload
from app.bot.handlers.admin.file_upload.column_configuration import process_upload_confirmation
from app.bot.handlers.admin.file_upload.template_processing import process_column_template
from app.bot.handlers.admin.file_upload.settings_management import process_back_to_settings
from app.bot.handlers.admin.file_upload.column_type_processing import process_select_column_type, process_column_type_selection

from app.bot.handlers.admin.admin_states import AdminStates
from app.bot.keyboards.admin_keyboards import get_admin_keyboard

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
    async def test_process_column_number_input(self, setup_mocks):
        """Test the process_column_number_input handler."""
        message, state, api_client, _, _ = setup_mocks
        
        # Set message text with column number
        message.text = "2"
        
        # Добавляем chat к message
        message.chat = MagicMock()
        message.chat.id = 67890
        
        # Set state data for column configuration
        state.get_data.return_value = {
            "selected_column_type": "word",
            "column_settings_message_id": 12345,
            "column_settings_chat_id": 67890,  # Совпадает с message.chat.id
            "selected_language_id": "lang1",
            "column_number": 0,
            "column_translation": 3
        }
        
        # Mock message bot methods
        message.bot.edit_message_text = AsyncMock()
        message.delete = AsyncMock()
        
        # Важно: сбросим счетчик вызовов set_state перед вызовом тестируемой функции
        # Set AdminStates.input_column_number
        await state.set_state(AdminStates.input_column_number)
        state.set_state.reset_mock()  # Сбрасываем счетчик вызовов после установки начального состояния
        
        # Patch required modules
        with patch('app.bot.handlers.admin.file_upload.column_type_processing.logger'), \
            patch('app.bot.handlers.admin.file_upload.column_type_processing.InlineKeyboardBuilder') as mock_builder, \
            patch('app.bot.handlers.admin.file_upload.column_type_processing.InlineKeyboardButton') as mock_button:
            
            # Setup mock builder
            mock_instance = MagicMock()
            mock_builder.return_value = mock_instance
            mock_instance.add.return_value = mock_instance
            mock_instance.adjust.return_value = mock_instance
            mock_instance.as_markup.return_value = MagicMock()
            
            # Call the handler
            from app.bot.handlers.admin.file_upload.column_type_processing import process_column_number_input
            await process_column_number_input(message, state)
            
            # Check that state was updated with column number for the selected type
            state.update_data.assert_called_once_with({"column_word": 2})
            
            # Check that state was set back to configuring_columns
            state.set_state.assert_called_once_with(AdminStates.configuring_columns)
            
            # Check that the original message was edited with updated settings
            message.bot.edit_message_text.assert_called_once()
            args, kwargs = message.bot.edit_message_text.call_args
            assert kwargs["chat_id"] == 67890
            assert kwargs["message_id"] == 12345
            assert "Колонка word установлена на 2" in kwargs["text"]
            assert "Текущие настройки колонок:" in kwargs["text"]
            assert kwargs["reply_markup"] == mock_instance.as_markup.return_value
            
            # Check that the input message was deleted
            message.delete.assert_called_once()
            