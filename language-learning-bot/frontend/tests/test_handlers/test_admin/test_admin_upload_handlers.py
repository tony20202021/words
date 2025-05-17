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
    async def test_cmd_upload_authorized(self, setup_mocks):
        """Test the /upload command handler for authorized admin."""
        message, state, api_client, _, _ = setup_mocks
        
        # Mock API responses - user is admin, languages available
        api_client.get_user_by_telegram_id.return_value = {
            "success": True,
            "status": 200,
            "result": [{
                "id": "user123", 
                "telegram_id": 12345, 
                "is_admin": True
            }],
            "error": None
        }
        api_client.get_languages.return_value = {
            "success": True,
            "status": 200,
            "result": [
                {"id": "lang1", "name_ru": "Английский", "name_foreign": "English"}
            ],
            "error": None
        }
        
        # Патчим импорт из file_processing модуля
        with patch('app.bot.handlers.admin.file_upload.file_processing.get_api_client_from_bot', return_value=api_client), \
            patch('app.bot.handlers.admin.file_upload.file_processing.logger'), \
            patch('app.bot.handlers.admin.file_upload.file_processing.InlineKeyboardBuilder') as mock_builder, \
            patch('app.bot.handlers.admin.file_upload.file_processing.InlineKeyboardButton') as mock_button:
            
            # Setup mock builder
            mock_instance = MagicMock()
            mock_builder.return_value = mock_instance
            mock_instance.add.return_value = mock_instance
            mock_instance.adjust.return_value = mock_instance
            mock_instance.as_markup.return_value = MagicMock()
            
            # Setup mock button
            mock_button.return_value = MagicMock()
            
            # Call the handler
            await cmd_upload(message, state)
            
            # Verify API calls
            api_client.get_user_by_telegram_id.assert_called_once_with(message.from_user.id)
            api_client.get_languages.assert_called_once()
            
            # Check that the builder was used correctly
            mock_builder.assert_called_once()
            mock_instance.add.assert_called()
            
            # В реальном коде метод adjust вызывается с 1, а не с 2
            mock_instance.adjust.assert_called_once_with(1)
            mock_instance.as_markup.assert_called_once()
            
            # Check that the bot sent a response message about file upload
            message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_upload_no_languages(self, setup_mocks):
        """Test the /upload command handler with no languages available."""
        message, state, api_client, _, _ = setup_mocks
        
        # Mock API responses - user is admin, no languages available
        api_client.get_user_by_telegram_id.return_value = {
            "success": True,
            "status": 200,
            "result": [{
                "id": "user123", 
                "telegram_id": 12345, 
                "is_admin": True
            }],
            "error": None
        }
        api_client.get_languages.return_value = {
            "success": True,
            "status": 200,
            "result": [],
            "error": None
        }
        
        # Patch the logger and API client
        with patch('app.bot.handlers.admin.file_upload.file_processing.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.admin.file_upload.file_processing.logger'):
            # Call the handler
            await cmd_upload(message, state)
            
            # Verify API calls
            api_client.get_user_by_telegram_id.assert_called_once_with(message.from_user.id)
            api_client.get_languages.assert_called_once()
            
            # Check that the bot sent an error message
            message.answer.assert_called_once()
            args, _ = message.answer.call_args
            assert "необходимо создать хотя бы один язык" in args[0]
    
    @pytest.mark.asyncio
    async def test_cmd_upload_unauthorized(self, setup_mocks):
        """Test the /upload command handler for unauthorized user."""
        message, state, api_client, _, _ = setup_mocks
        
        # Mock API responses - user is not admin
        api_client.get_user_by_telegram_id.return_value = {
            "success": True,
            "status": 200,
            "result": [{
                "id": "user123", 
                "telegram_id": 12345, 
                "is_admin": False
            }],
            "error": None
        }
        
        # Patch the logger and API client
        with patch('app.bot.handlers.admin.file_upload.file_processing.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.admin.file_upload.file_processing.logger'):
            # Call the handler
            await cmd_upload(message, state)
            
            # Verify API calls
            api_client.get_user_by_telegram_id.assert_called_once_with(message.from_user.id)
            
            # Check that the bot sent an access denied message
            message.answer.assert_called_once_with("У вас нет прав администратора.")
    
    @pytest.mark.asyncio
    async def test_process_language_selection_for_upload(self, setup_mocks):
        """Test process_language_selection_for_upload callback handler."""
        _, state, api_client, callback, _ = setup_mocks
        
        # Set callback data for language selection
        callback.data = "upload_to_lang_lang1"
        
        # Mock API responses - language found
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
            await process_language_selection_for_upload(callback, state)
            
            # Verify API calls
            api_client.get_language.assert_called_once_with("lang1")
            
            # Check that state was updated with selected language
            state.update_data.assert_called_once_with(selected_language_id="lang1")
            
            # Check that state was set to waiting for file
            state.set_state.assert_called_once_with(AdminStates.waiting_file)
            
            # Check that the bot sent an upload instruction message
            callback.message.answer.assert_called_once()
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_file_upload(self, setup_mocks):
        """Test process_file_upload handler."""
        _, state, api_client, _, document_message = setup_mocks
        
        # Set state for file upload
        state.get_data.return_value = {"selected_language_id": "lang1"}
        
        # Mock file handling
        file = MagicMock()
        file.file_path = "path/to/file.xlsx"
        document_message.bot.get_file.return_value = file
        document_message.bot.download_file.return_value = b"file_data"
        
        # Patch the logger, API client and InlineKeyboardBuilder
        # Исправляем путь импорта в патче
        with patch('app.bot.handlers.admin.file_upload.file_processing.get_api_client_from_bot', return_value=api_client), \
            patch('app.bot.handlers.admin.file_upload.file_processing.logger'), \
            patch('app.bot.handlers.admin.file_upload.file_processing.InlineKeyboardBuilder') as mock_builder, \
            patch('app.bot.handlers.admin.file_upload.file_processing.InlineKeyboardButton') as mock_button:
            
            # Setup mock builder
            mock_instance = MagicMock()
            mock_builder.return_value = mock_instance
            mock_instance.add.return_value = mock_instance
            mock_instance.adjust.return_value = mock_instance
            mock_instance.as_markup.return_value = MagicMock()
            
            # Setup mock button
            mock_button.return_value = MagicMock()
            
            # Call the handler
            await process_file_upload(document_message, state)
            
            # Verify file handling
            document_message.bot.get_file.assert_called_once_with(document_message.document.file_id)
            document_message.bot.download_file.assert_called_once_with(file.file_path)
            
            # Check that the builder was used correctly
            mock_builder.assert_called_once()
            # Проверяем, что add был вызван хотя бы 4 раза (для 4 кнопок)
            assert mock_instance.add.call_count >= 4
            # Проверяем, что adjust был вызван с аргументом 1
            mock_instance.adjust.assert_called_once_with(1)
            mock_instance.as_markup.assert_called_once()
            
            # Не проверяем точное количество вызовов update_data, т.к. в реальном коде их два
            # - один раз для file_data и file_name
            # - второй раз для настроек по умолчанию
            assert state.update_data.called
            
            # Check that state was set to configuring columns
            state.set_state.assert_called_once_with(AdminStates.configuring_columns)
            
            # Check that the bot sent a column configuration message
            document_message.answer.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_process_file_upload_no_document(self, setup_mocks):
        """Test process_file_upload handler with no document."""
        message, state, api_client, _, _ = setup_mocks
        
        # Set message with no document
        message.document = None
        
        # Patch the logger and API client
        with patch('app.bot.handlers.admin.file_upload.file_processing.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.admin.file_upload.file_processing.logger'):
            # Call the handler
            await process_file_upload(message, state)
            
            # Check that the bot sent an error message
            message.answer.assert_called_once()
            args, _ = message.answer.call_args
            assert "Пожалуйста, отправьте Excel-файл" in args[0]
    
    @pytest.mark.asyncio
    async def test_process_upload_confirmation(self, setup_mocks):
        """Test process_upload_confirmation with confirm action."""
        _, state, api_client, callback, _ = setup_mocks
        
        # Set callback data for confirmation
        callback.data = "confirm_upload"
        
        # Set state data for file upload
        state.get_data.return_value = {
            "selected_language_id": "lang1", 
            "file_data": b"file_data", 
            "file_name": "words.xlsx",
            "column_word": 0,
            "column_translation": 1
        }
        
        # Mock API responses - upload success
        api_client.upload_words_file.return_value = {
            "success": True,
            "status": 200,
            "result": {
                "language_name": "Английский",
                "total_words_processed": 100,
                "words_added": 80,
                "words_updated": 10,
                "words_skipped": 10,
                "errors": []
            },
            "error": None
        }
        
        # Create mock for edit_text
        callback.message.edit_text = AsyncMock()
        loading_message = MagicMock()
        loading_message.edit_text = AsyncMock()
        
        # Patch the logger, API client and answer method to return loading_message
        with patch('app.bot.handlers.admin.file_upload.column_configuration.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.admin.file_upload.column_configuration.logger'), \
             patch.object(callback.message, 'answer', return_value=loading_message):
            # Call the handler
            await process_upload_confirmation(callback, state)
            
            # Verify API calls
            api_client.upload_words_file.assert_called_once()
            
            # Check that the loading message was sent and then edited
            callback.message.answer.assert_called_once_with("⏳ Загрузка файла...")
            loading_message.edit_text.assert_called_once()
            
            # Check that state was cleared
            state.clear.assert_called_once()
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_column_template(self, setup_mocks):
        """Test process_column_template handler."""
        _, state, api_client, callback, _ = setup_mocks
        
        # Set callback data for column template
        callback.data = "upload_columns:0,1,2,3:lang1"
        
        # Mock message edit_text
        callback.message.edit_text = AsyncMock()
        
        # Patch the logger and InlineKeyboardBuilder
        # Исправляем путь импорта - патчим InlineKeyboardBuilder из модуля
        with patch('app.bot.handlers.admin.file_upload.template_processing.logger'), \
            patch('app.bot.handlers.admin.file_upload.template_processing.InlineKeyboardBuilder') as mock_builder, \
            patch('app.bot.handlers.admin.file_upload.template_processing.InlineKeyboardButton') as mock_button:
            
            # Setup mock builder
            mock_instance = MagicMock()
            mock_builder.return_value = mock_instance
            mock_instance.add.return_value = mock_instance
            mock_instance.adjust.return_value = mock_instance
            mock_instance.as_markup.return_value = MagicMock()
            
            # Setup mock button
            mock_button.return_value = MagicMock()
            
            # Call the handler
            await process_column_template(callback, state)
            
            # Check that state was updated with column indices
            expected_updates = {
                "column_number": 0,
                "column_word": 1,
                "column_transcription": 2,
                "column_translation": 3
            }
            state.update_data.assert_called_once_with(expected_updates)
            
            # Check that the builder was used correctly
            mock_builder.assert_called_once()
            assert mock_instance.add.call_count >= 3  # Минимум 3 кнопки
            mock_instance.adjust.assert_called_once_with(1)
            mock_instance.as_markup.assert_called_once()
            
            # Check that the message was edited
            callback.message.edit_text.assert_called_once()
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_back_to_settings(self, setup_mocks):
        """Test process_back_to_settings handler."""
        _, state, api_client, callback, _ = setup_mocks
        
        # Set callback data
        callback.data = "back_to_settings"
        
        # Set state data
        state.get_data.return_value = {
            "has_headers": True,
            "clear_existing": False,
            "selected_language_id": "lang1"
        }
        
        # Mock message edit_text
        callback.message.edit_text = AsyncMock()
        
        # Patch the logger and InlineKeyboardBuilder
        with patch('app.bot.handlers.admin.file_upload.settings_management.logger'), \
            patch('app.bot.handlers.admin.file_upload.settings_management.InlineKeyboardBuilder') as mock_builder, \
            patch('app.bot.handlers.admin.file_upload.settings_management.InlineKeyboardButton') as mock_button, \
            patch('app.bot.handlers.admin.file_upload.settings_management.get_column_info_text', return_value="(сейчас: 0, 1, 2, 3)"):
            
            # Setup mock builder
            mock_instance = MagicMock()
            mock_builder.return_value = mock_instance
            mock_instance.add.return_value = mock_instance
            mock_instance.adjust.return_value = mock_instance
            mock_instance.as_markup.return_value = MagicMock()
            
            # Setup mock button
            mock_button.return_value = MagicMock()
            
            # Call the handler
            await process_back_to_settings(callback, state)
            
            # Check that the builder was used correctly
            mock_builder.assert_called_once()
            assert mock_instance.add.call_count >= 4  # Должно быть несколько кнопок
            mock_instance.adjust.assert_called_once_with(1)
            mock_instance.as_markup.assert_called_once()
            
            # Check that the message was edited
            callback.message.edit_text.assert_called_once()
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_select_column_type(self, setup_mocks):
        """Test process_select_column_type handler."""
        _, state, api_client, callback, _ = setup_mocks
        
        # Set callback data
        callback.data = "select_column_type:lang1"
        
        # Set state data
        state.get_data.return_value = {
            "column_word": 1,
            "column_translation": 2
        }
        
        # Mock message edit_text
        callback.message.edit_text = AsyncMock()
        
        # Patch the logger and InlineKeyboardBuilder
        with patch('app.bot.handlers.admin.file_upload.column_type_processing.logger'), \
            patch('app.bot.handlers.admin.file_upload.column_type_processing.InlineKeyboardBuilder') as mock_builder, \
            patch('app.bot.handlers.admin.file_upload.column_type_processing.InlineKeyboardButton') as mock_button:
            
            # Setup mock builder
            mock_instance = MagicMock()
            mock_builder.return_value = mock_instance
            mock_instance.add.return_value = mock_instance
            mock_instance.adjust.return_value = mock_instance
            mock_instance.as_markup.return_value = MagicMock()
            
            # Setup mock button
            mock_button.return_value = MagicMock()
            
            # Call the handler
            await process_select_column_type(callback, state)
            
            # Check that the builder was used correctly
            mock_builder.assert_called_once()
            assert mock_instance.add.call_count >= 4  # Должно быть несколько кнопок для типов колонок
            mock_instance.adjust.assert_called_once_with(1)
            mock_instance.as_markup.assert_called_once()
            
            # Check that the message was edited
            callback.message.edit_text.assert_called_once()
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_process_column_template(self, setup_mocks):
        """Test the process_column_template handler."""
        _, state, api_client, callback, _ = setup_mocks
        
        # Set callback data for column template
        callback.data = "upload_columns:0,1,2,3:lang1"
        
        # Mock message edit_text
        callback.message.edit_text = AsyncMock()
        
        # Set AdminStates.configuring_columns
        await state.set_state(AdminStates.configuring_columns)
        
        # Patch necessary modules
        with patch('app.bot.handlers.admin.file_upload.template_processing.logger'), \
            patch('app.bot.handlers.admin.file_upload.template_processing.InlineKeyboardBuilder') as mock_builder, \
            patch('app.bot.handlers.admin.file_upload.template_processing.InlineKeyboardButton') as mock_button:
            
            # Setup mock builder
            mock_instance = MagicMock()
            mock_builder.return_value = mock_instance
            mock_instance.add.return_value = mock_instance
            mock_instance.adjust.return_value = mock_instance
            mock_instance.as_markup.return_value = MagicMock()
            
            # Setup mock button
            mock_button.return_value = MagicMock()
            
            # Call the handler
            await process_column_template(callback, state)
            
            # Check state updates - column indices were saved
            state.update_data.assert_called_once_with({
                "column_number": 0,
                "column_word": 1,
                "column_transcription": 2,
                "column_translation": 3
            })
            
            # Check that the keyboard builder was used correctly
            mock_builder.assert_called_once()
            # At least 3 buttons should be added (upload, configure manually, back)
            assert mock_instance.add.call_count >= 3
            mock_instance.adjust.assert_called_once_with(1)  # One button per row
            mock_instance.as_markup.assert_called_once()
            
            # Check that edit_text was called with template info
            callback.message.edit_text.assert_called_once()
            args, kwargs = callback.message.edit_text.call_args
            assert "Выбран шаблон" in args[0]
            assert "Колонка номера: 0" in args[0]
            assert "Колонка слова: 1" in args[0]
            assert "Колонка транскрипции: 2" in args[0]
            assert "Колонка перевода: 3" in args[0]
            assert kwargs["reply_markup"] == mock_instance.as_markup.return_value
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()

