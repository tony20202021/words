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

    def test_format_column_settings(self):
        """Test the format_column_settings function."""
        # Test with all column settings present
        user_data = {
            "column_number": 0,
            "column_word": 1,
            "column_transcription": 2,
            "column_translation": 3
        }
        
        from app.bot.handlers.admin.file_upload.settings_management import format_column_settings
        
        result = format_column_settings(user_data)
        
        # Check that the result contains all column settings
        assert "Настройки колонок:" in result
        assert "✅ Колонка number: 0" in result
        assert "✅ Колонка word: 1" in result
        assert "✅ Колонка transcription: 2" in result
        assert "✅ Колонка translation: 3" in result
        
        # Test with no column settings
        empty_user_data = {}
        empty_result = format_column_settings(empty_user_data)
        assert empty_result == ""
        
        # Test with partial column settings
        partial_user_data = {
            "column_word": 1,
            "column_translation": 3
        }
        partial_result = format_column_settings(partial_user_data)
        assert "Настройки колонок:" in partial_result
        assert "✅ Колонка word: 1" in partial_result
        assert "✅ Колонка translation: 3" in partial_result
        assert "Колонка number" not in partial_result
        assert "Колонка transcription" not in partial_result

    def test_get_column_info_text(self):
        """Test the get_column_info_text function."""
        # Test with all column settings present
        user_data = {
            "column_number": 0,
            "column_word": 1,
            "column_transcription": 2,
            "column_translation": 3
        }
        
        from app.bot.handlers.admin.file_upload.settings_management import get_column_info_text
        
        result = get_column_info_text(user_data)
        
        # Check that the result contains all column values
        assert result == "(сейчас: 0, 1, 2, 3)"
        
        # Test with no column settings
        empty_user_data = {}
        empty_result = get_column_info_text(empty_user_data)
        assert empty_result == ""
        
        # Test with partial column settings
        partial_user_data = {
            "column_word": 1,
            "column_translation": 3
        }
        partial_result = get_column_info_text(partial_user_data)
        assert partial_result == "(сейчас: 1, 3)"

    @pytest.mark.asyncio
    async def test_toggle_headers_setting(self, setup_mocks):
        """Test the toggle_headers_setting handler."""
        _, state, api_client, callback, _ = setup_mocks
        
        # Set callback data
        callback.data = "toggle_headers"
        
        # Set initial state data (has_headers is initially False)
        initial_state_data = {
            "has_headers": False,
            "clear_existing": False,
            "selected_language_id": "lang1",
            "column_word": 1,
            "column_translation": 2,
            "column_transcription": 3,
            "column_number": 0
        }
        state.get_data.return_value = initial_state_data
        
        # Mock message edit_text
        callback.message.edit_text = AsyncMock()
        
        # Set AdminStates.configuring_columns
        await state.set_state(AdminStates.configuring_columns)
        
        # Важно: обновляем return_value для state.get_data, чтобы имитировать реальное поведение
        # Это имитирует обновление данных после вызова state.update_data
        def side_effect():
            # Обновляем has_headers на True после вызова update_data
            updated_data = initial_state_data.copy()
            updated_data["has_headers"] = True
            state.get_data.return_value = updated_data
            return updated_data
        
        state.update_data.side_effect = lambda **kwargs: side_effect() if "has_headers" in kwargs else None
        
        # Patch required modules
        with patch('app.bot.handlers.admin.file_upload.settings_management.logger'), \
            patch('app.bot.handlers.admin.file_upload.settings_management.InlineKeyboardBuilder') as mock_builder, \
            patch('app.bot.handlers.admin.file_upload.settings_management.InlineKeyboardButton') as mock_button, \
            patch('app.bot.handlers.admin.file_upload.settings_management.format_column_settings', 
                return_value="Настройки колонок:\n✅ Колонка number: 0\n✅ Колонка word: 1\n✅ Колонка transcription: 3\n✅ Колонка translation: 2\n"), \
            patch('app.bot.handlers.admin.file_upload.settings_management.get_column_info_text', 
                return_value="(сейчас: 0, 1, 3, 2)"):
            
            # Setup mock builder
            mock_instance = MagicMock()
            mock_builder.return_value = mock_instance
            mock_instance.add.return_value = mock_instance
            mock_instance.adjust.return_value = mock_instance
            mock_instance.as_markup.return_value = MagicMock()
            
            # Call the handler
            from app.bot.handlers.admin.file_upload.settings_management import toggle_headers_setting
            await toggle_headers_setting(callback, state)
            
            # Check that state was updated (has_headers should now be True)
            state.update_data.assert_called_once_with(has_headers=True)
            
            # Check that the builder was used correctly
            mock_builder.assert_called_once()
            assert mock_instance.add.call_count >= 4  # At least 4 buttons
            mock_instance.adjust.assert_called_once_with(1)  # One button per row
            mock_instance.as_markup.assert_called_once()
            
            # Check that message was edited with updated settings
            callback.message.edit_text.assert_called_once()
            args, kwargs = callback.message.edit_text.call_args
            assert "Настройки загрузки файла" in args[0]
            assert "Файл содержит заголовки: \"Да\"" in args[0]  # has_headers is now True
            assert "Очистить существующие слова: \"Нет\"" in args[0]  # clear_existing is still False
            assert kwargs["reply_markup"] == mock_instance.as_markup.return_value
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_toggle_clear_existing_setting(self, setup_mocks):
        """Test the toggle_clear_existing_setting handler."""
        _, state, api_client, callback, _ = setup_mocks
        
        # Set callback data
        callback.data = "toggle_clear_existing"
        
        # Set initial state data (clear_existing is initially False)
        initial_state_data = {
            "has_headers": True,
            "clear_existing": False,
            "selected_language_id": "lang1",
            "column_word": 1,
            "column_translation": 2,
            "column_transcription": 3,
            "column_number": 0
        }
        state.get_data.return_value = initial_state_data
        
        # Mock message edit_text
        callback.message.edit_text = AsyncMock()
        
        # Set AdminStates.configuring_columns
        await state.set_state(AdminStates.configuring_columns)
        
        # Важно: обновляем return_value для state.get_data, чтобы имитировать реальное поведение
        # Это имитирует обновление данных после вызова state.update_data
        def side_effect():
            # Обновляем clear_existing на True после вызова update_data
            updated_data = initial_state_data.copy()
            updated_data["clear_existing"] = True
            state.get_data.return_value = updated_data
            return updated_data
        
        state.update_data.side_effect = lambda **kwargs: side_effect() if "clear_existing" in kwargs else None
        
        # Patch required modules
        with patch('app.bot.handlers.admin.file_upload.settings_management.logger'), \
            patch('app.bot.handlers.admin.file_upload.settings_management.InlineKeyboardBuilder') as mock_builder, \
            patch('app.bot.handlers.admin.file_upload.settings_management.InlineKeyboardButton') as mock_button, \
            patch('app.bot.handlers.admin.file_upload.settings_management.format_column_settings', 
                return_value="Настройки колонок:\n✅ Колонка number: 0\n✅ Колонка word: 1\n✅ Колонка transcription: 3\n✅ Колонка translation: 2\n"), \
            patch('app.bot.handlers.admin.file_upload.settings_management.get_column_info_text', 
                return_value="(сейчас: 0, 1, 3, 2)"):
            
            # Setup mock builder
            mock_instance = MagicMock()
            mock_builder.return_value = mock_instance
            mock_instance.add.return_value = mock_instance
            mock_instance.adjust.return_value = mock_instance
            mock_instance.as_markup.return_value = MagicMock()
            
            # Call the handler
            from app.bot.handlers.admin.file_upload.settings_management import toggle_clear_existing_setting
            await toggle_clear_existing_setting(callback, state)
            
            # Check that state was updated (clear_existing should now be True)
            state.update_data.assert_called_once_with(clear_existing=True)
            
            # Check that the builder was used correctly
            mock_builder.assert_called_once()
            assert mock_instance.add.call_count >= 4  # At least 4 buttons
            mock_instance.adjust.assert_called_once_with(1)  # One button per row
            mock_instance.as_markup.assert_called_once()
            
            # Check that message was edited with updated settings
            callback.message.edit_text.assert_called_once()
            args, kwargs = callback.message.edit_text.call_args
            assert "Настройки загрузки файла" in args[0]
            assert "Файл содержит заголовки: \"Да\"" in args[0]  # has_headers is still True
            assert "Очистить существующие слова: \"Да\"" in args[0]  # clear_existing is now True
            assert kwargs["reply_markup"] == mock_instance.as_markup.return_value
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()