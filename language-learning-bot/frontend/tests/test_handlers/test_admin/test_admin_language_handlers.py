"""
Unit tests for language management admin handlers.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock

from aiogram import Dispatcher
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
    async def test_cmd_manage_languages_authorized(self, setup_mocks):
        """Test the /managelang command handler for authorized admin."""
        message, state, api_client, _ = setup_mocks
        
        # Mock API responses - user is admin
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
        
        # Patch the logger, API client and keyboard functions
        with patch('app.bot.handlers.admin.admin_language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.admin.admin_language_handlers.logger'), \
             patch('app.bot.handlers.admin.admin_language_handlers.get_languages_keyboard') as mock_get_languages_keyboard:
            
            # Setup mock keyboard function
            mock_get_languages_keyboard.return_value = MagicMock()
            
            # Call the handler
            await cmd_manage_languages(message, state)
            
            # Verify API calls
            api_client.get_user_by_telegram_id.assert_called_once_with(message.from_user.id)
            api_client.get_languages.assert_called_once()
            
            # Check that the keyboard function was used
            mock_get_languages_keyboard.assert_called_once()
            
            # Check that the bot sent a response message about language management
            message.answer.assert_called_once()
            args, _ = message.answer.call_args
            assert "Управление языками" in args[0]
    
    @pytest.mark.asyncio
    async def test_cmd_manage_languages_unauthorized(self, setup_mocks):
        """Test the /managelang command handler for unauthorized user."""
        message, state, api_client, _ = setup_mocks
        
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
        with patch('app.bot.handlers.admin.admin_language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.admin.admin_language_handlers.logger'):
            # Call the handler
            await cmd_manage_languages(message, state)
            
            # Verify API calls
            api_client.get_user_by_telegram_id.assert_called_once_with(message.from_user.id)
            
            # Check that the bot sent an access denied message
            message.answer.assert_called_once_with("У вас нет прав администратора.")
    
    @pytest.mark.asyncio
    async def test_process_create_language(self, setup_mocks):
        """Test the process_create_language callback handler."""
        _, state, api_client, callback = setup_mocks
        
        # Mock API responses - user is admin
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
        
        # Patch the logger and API client
        with patch('app.bot.handlers.admin.admin_language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.admin.admin_language_handlers.logger'):
            # Call the handler
            await process_create_language(callback, state)
            
            # Verify API calls
            api_client.get_user_by_telegram_id.assert_called_once_with(callback.from_user.id)
            
            # Check that state was set to creating language name
            state.set_state.assert_called_once_with(AdminStates.creating_language_name)
            
            # Check that the bot sent a creation message
            callback.message.answer.assert_called_once()
            args, _ = callback.message.answer.call_args
            assert "Создание нового языка" in args[0]
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_language_name(self, setup_mocks):
        """Test the process_language_name handler."""
        message, state, api_client, _ = setup_mocks
        
        # Set message text
        message.text = "Французский"
        
        # Patch the logger and API client
        with patch('app.bot.handlers.admin.admin_language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.admin.admin_language_handlers.logger'):
            # Call the handler
            await process_language_name(message, state)
            
            # Check that state was updated with language name
            state.update_data.assert_called_once_with(language_name_ru=message.text)
            
            # Check that state was set to creating language native name
            state.set_state.assert_called_once_with(AdminStates.creating_language_native_name)
            
            # Check that the bot sent a confirmation message
            message.answer.assert_called_once()
            args, _ = message.answer.call_args
            assert "Название на русском" in args[0]
    
    @pytest.mark.asyncio
    async def test_process_language_native_name(self, setup_mocks):
        """Test the process_language_native_name handler."""
        message, state, api_client, _ = setup_mocks
        
        # Set message text
        message.text = "Français"
        
        # Set state data
        state.get_data.return_value = {"language_name_ru": "Французский"}
        
        # Mock API responses - language created
        api_client.create_language.return_value = {
            "success": True,
            "status": 201,
            "result": {
                "id": "lang4",
                "name_ru": "Французский",
                "name_foreign": "Français"
            },
            "error": None
        }
        
        # Patch the logger and API client
        with patch('app.bot.handlers.admin.admin_language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.admin.admin_language_handlers.logger'):
            # Call the handler
            await process_language_native_name(message, state)
            
            # Verify API calls
            api_client.create_language.assert_called_once_with({
                "name_ru": "Французский",
                "name_foreign": "Français"
            })
            
            # Check that state was cleared
            state.clear.assert_called_once()
            
            # Check that the bot sent a success message
            message.answer.assert_called_once()
            args, _ = message.answer.call_args
            assert "Язык успешно создан" in args[0]
    
    @pytest.mark.asyncio
    async def test_process_edit_language(self, setup_mocks):
        """Test the process_edit_language callback handler."""
        _, state, api_client, callback = setup_mocks
        
        # Set callback data
        callback.data = "edit_language_lang1"
        
        # Mock API responses - user is admin, language found
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
        api_client.get_language.return_value = {
            "success": True,
            "status": 200,
            "result": {
                "id": "lang1", 
                "name_ru": "Английский", 
                "name_foreign": "English", 
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z"
            },
            "error": None
        }
        api_client.get_word_count_by_language.return_value = {
            "success": True,
            "result": {"count": 100}
        }
        
        # Patch the logger, API client, formatting utils and keyboard function
        with patch('app.bot.handlers.admin.admin_language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.admin.admin_language_handlers.logger'), \
             patch('app.bot.handlers.admin.admin_language_handlers.format_date_standard', return_value="1 января 2023"), \
             patch('app.bot.handlers.admin.admin_language_handlers.get_edit_language_keyboard') as mock_keyboard:
            
            # Setup mock keyboard function
            mock_keyboard.return_value = MagicMock()
            
            # Call the handler
            await process_edit_language(callback, state)
            
            # Verify API calls
            api_client.get_user_by_telegram_id.assert_called_once_with(callback.from_user.id)
            api_client.get_language.assert_called_once_with("lang1")
            api_client.get_word_count_by_language.assert_called_once_with("lang1")
            
            # Check that state was updated with editing language id
            state.update_data.assert_called_once_with(editing_language_id="lang1")
            
            # Check that the bot sent an edit options message
            callback.message.answer.assert_called_once()
            args, kwargs = callback.message.answer.call_args
            assert "Редактирование языка" in args[0]
            assert "Английский" in args[0]
            assert "English" in args[0]
            assert "100" in args[0]  # Word count
            assert kwargs["parse_mode"] == "HTML"
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_edit_name_ru(self, setup_mocks):
        """Test the process_edit_name_ru callback handler."""
        _, state, api_client, callback = setup_mocks
        
        # Set callback data
        callback.data = "edit_name_ru_lang1"
        
        # Patch the logger and API client
        with patch('app.bot.handlers.admin.admin_language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.admin.admin_language_handlers.logger'):
            # Call the handler
            await process_edit_name_ru(callback, state)
            
            # Check that state was updated with editing language id
            state.update_data.assert_called_once_with(editing_language_id="lang1")
            
            # Check that state was set to editing language name
            state.set_state.assert_called_once_with(AdminStates.editing_language_name)
            
            # Check that the bot sent an edit message
            callback.message.answer.assert_called_once()
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_edit_language_name(self, setup_mocks):
        """Test the process_edit_language_name handler."""
        message, state, api_client, _ = setup_mocks
        
        # Set message text
        message.text = "Обновленный Английский"
        
        # Set state data
        state.get_data.return_value = {"editing_language_id": "lang1"}
        
        # Mock API responses - language updated
        api_client.update_language.return_value = {
            "success": True,
            "status": 200,
            "result": {
                "id": "lang1",
                "name_ru": "Обновленный Английский",
                "name_foreign": "English",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-02T00:00:00Z"
            },
            "error": None
        }
        
        # Патчим также функцию process_edit_language_after_update, чтобы она ничего не делала
        # и не требовала дополнительных моков
        with patch('app.bot.handlers.admin.admin_language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.admin.admin_language_handlers.logger'), \
             patch('app.bot.handlers.admin.admin_language_handlers.process_edit_language_after_update', AsyncMock()):
            # Call the handler
            await process_edit_language_name(message, state)
            
            # Verify API calls
            api_client.update_language.assert_called_once_with("lang1", {"name_ru": "Обновленный Английский"})
            
            # Check that state was cleared
            state.clear.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_delete_language(self, setup_mocks):
        """Test the process_delete_language callback handler."""
        _, state, api_client, callback = setup_mocks
        
        # Set callback data
        callback.data = "delete_language_lang1"
        
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
        
        # Patch the logger, API client and keyboard builder
        with patch('app.bot.handlers.admin.admin_language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.admin.admin_language_handlers.logger'), \
             patch('app.bot.handlers.admin.admin_language_handlers.InlineKeyboardBuilder') as mock_builder, \
             patch('app.bot.handlers.admin.admin_language_handlers.InlineKeyboardButton') as mock_button:
            
            # Setup mock builder
            mock_instance = MagicMock()
            mock_builder.return_value = mock_instance
            mock_instance.add.return_value = mock_instance
            mock_instance.adjust.return_value = mock_instance
            mock_instance.as_markup.return_value = MagicMock()
            
            # Setup mock button
            mock_button.return_value = MagicMock()
            
            # Call the handler
            await process_delete_language(callback, state)
            
            # Verify API calls
            api_client.get_language.assert_called_once_with("lang1")
            
            # Check that the builder was used
            mock_builder.assert_called_once()
            mock_instance.add.assert_called()
            mock_instance.adjust.assert_called_once_with(2)  # Для кнопок в ряд
            mock_instance.as_markup.assert_called_once()
            
            # Check that the bot sent a confirmation message
            callback.message.answer.assert_called_once()
            args, _ = callback.message.answer.call_args
            assert "Вы действительно хотите удалить язык" in args[0]
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_confirm_delete_language(self, setup_mocks):
        """Test the process_confirm_delete_language callback handler."""
        _, state, api_client, callback = setup_mocks
        
        # Set callback data
        callback.data = "confirm_delete_lang1"
        
        # Mock API responses - deletion successful
        api_client.delete_language.return_value = {
            "success": True,
            "status": 200,
            "result": {
                "message": "Language with ID lang1 deleted successfully"
            },
            "error": None
        }
        
        # Patch the logger and API client
        with patch('app.bot.handlers.admin.admin_language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.admin.admin_language_handlers.logger'):
            # Call the handler
            await process_confirm_delete_language(callback, state)
            
            # Verify API calls
            api_client.delete_language.assert_called_once_with("lang1")
            
            # Check that the bot sent a success message
            callback.message.answer.assert_called_once()
            args, _ = callback.message.answer.call_args
            assert "Язык успешно удален" in args[0]
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_cancel_delete_language(self, setup_mocks):
        """Test the process_cancel_delete_language callback handler."""
        _, state, api_client, callback = setup_mocks
        
        # Set callback data
        callback.data = "cancel_delete_lang1"
        
        # Patch the logger and API client
        with patch('app.bot.handlers.admin.admin_language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.admin.admin_language_handlers.logger'):
            # Call the handler
            await process_cancel_delete_language(callback, state)
            
            # Check that the bot sent a cancellation message
            callback.message.answer.assert_called_once_with("🚫 Удаление языка отменено")
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_language_management(self, setup_mocks):
        """Test the handle_language_management function."""
        message, state, api_client, _ = setup_mocks
        
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
        
        # Patch the logger, API client and keyboard function
        with patch('app.bot.handlers.admin.admin_language_handlers.get_api_client_from_bot', return_value=api_client), \
            patch('app.bot.handlers.admin.admin_language_handlers.logger'), \
            patch('app.bot.handlers.admin.admin_language_handlers.get_languages_keyboard') as mock_keyboard:
            
            # Setup mock keyboard function
            mock_keyboard.return_value = MagicMock()
            
            # Call the function
            from app.bot.handlers.admin.admin_language_handlers import handle_language_management
            result = await handle_language_management(message, state)
            
            # Check result
            assert result is True
            
            # Verify API calls
            api_client.get_user_by_telegram_id.assert_called_once_with(message.from_user.id)
            api_client.get_languages.assert_called_once()
            
            # Check that keyboard function was called
            mock_keyboard.assert_called_once()
            
            # Check that message was sent with language management info
            message.answer.assert_called_once()
            args, kwargs = message.answer.call_args
            assert "Управление языками" in args[0]
            assert kwargs["reply_markup"] == mock_keyboard.return_value

    @pytest.mark.asyncio
    async def test_process_back_to_admin_from_languages(self, setup_mocks):
        """Test the process_back_to_admin_from_languages callback handler."""
        _, state, _, callback = setup_mocks
        
        # Вместо патча handle_admin_mode в admin_language_handlers, 
        # патчим его по правильному пути - admin_basic_handlers
        with patch('app.bot.handlers.admin.admin_basic_handlers.handle_admin_mode', AsyncMock(return_value=True)) as mock_handle_admin:
            
            # Call the function
            from app.bot.handlers.admin.admin_language_handlers import process_back_to_admin_from_languages
            await process_back_to_admin_from_languages(callback, state)
            
            # Check that handle_admin_mode was called with correct parameters
            mock_handle_admin.assert_called_once_with(callback, state, is_callback=True)
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_process_back_to_languages(self, setup_mocks):
        """Test the process_back_to_languages callback handler."""
        _, state, _, callback = setup_mocks
        
        # Patch the handle_language_management function to avoid duplicate testing
        with patch('app.bot.handlers.admin.admin_language_handlers.handle_language_management', AsyncMock(return_value=True)) as mock_handle_languages:
            
            # Call the function
            from app.bot.handlers.admin.admin_language_handlers import process_back_to_languages
            await process_back_to_languages(callback, state)
            
            # Check that handle_language_management was called with correct parameters
            mock_handle_languages.assert_called_once_with(callback, state, is_callback=True)
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_language_edit_screen(self, setup_mocks):
        """Test the show_language_edit_screen function."""
        message, _, api_client, _ = setup_mocks
        
        # Mock API responses - language found
        api_client.get_language.return_value = {
            "success": True,
            "status": 200,
            "result": {
                "id": "lang1", 
                "name_ru": "Английский", 
                "name_foreign": "English", 
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z"
            },
            "error": None
        }
        
        api_client.get_word_count_by_language.return_value = {
            "success": True,
            "status": 200,
            "result": {"count": 100},
            "error": None
        }
        
        # Patch the required functions and logger
        with patch('app.bot.handlers.admin.admin_language_handlers.get_api_client_from_bot', return_value=api_client), \
            patch('app.bot.handlers.admin.admin_language_handlers.logger'), \
            patch('app.bot.handlers.admin.admin_language_handlers.format_date_standard', return_value="1 января 2023"), \
            patch('app.bot.handlers.admin.admin_language_handlers.get_edit_language_keyboard') as mock_keyboard:
            
            # Setup mock keyboard function
            mock_keyboard.return_value = MagicMock()
            
            # Call the function
            from app.bot.handlers.admin.admin_language_handlers import show_language_edit_screen
            await show_language_edit_screen(message, "lang1")
            
            # Verify API calls
            api_client.get_language.assert_called_once_with("lang1")
            api_client.get_word_count_by_language.assert_called_once_with("lang1")
            
            # Check that keyboard function was called
            mock_keyboard.assert_called_once_with("lang1")
            
            # Check that message was sent with language edit info
            message.answer.assert_called_once()
            args, kwargs = message.answer.call_args
            assert "Редактирование языка" in args[0]
            assert "Английский" in args[0]
            assert "English" in args[0]
            assert "100" in args[0]  # word count
            assert kwargs["parse_mode"] == "HTML"
            assert kwargs["reply_markup"] == mock_keyboard.return_value
                                                
    @pytest.mark.asyncio
    async def test_process_edit_language_after_update(self, setup_mocks):
        """Test the process_edit_language_after_update function."""
        message, _, _, _ = setup_mocks
        
        # Patch the show_language_edit_screen function to avoid duplicate testing
        with patch('app.bot.handlers.admin.admin_language_handlers.show_language_edit_screen', AsyncMock()) as mock_show_screen:
            
            # Call the function
            from app.bot.handlers.admin.admin_language_handlers import process_edit_language_after_update
            await process_edit_language_after_update(message, "lang1")
            
            # Check that show_language_edit_screen was called with correct parameters
            mock_show_screen.assert_called_once_with(message, "lang1", is_callback=False)

    @pytest.mark.asyncio
    async def test_process_word_number_input(self, setup_mocks):
        """Test the process_word_number_input handler."""
        message, state, api_client, _ = setup_mocks
        
        # Set message text with word number
        message.text = "5"
        
        # Set state data
        state.get_data.return_value = {
            "language_id": "lang1",
            "db_user_id": "user123"
        }
        
        # ВАЖНО: Установить reply как AsyncMock
        message.reply = AsyncMock()
        
        # Mock API responses
        api_client.get_word_by_number.return_value = {
            "success": True,
            "status": 200,
            "result": [{
                "id": "word5", 
                "word_foreign": "apple", 
                "translation": "яблоко", 
                "transcription": "æpl", 
                "word_number": 5
            }],
            "error": None
        }
        
        api_client.get_language.return_value = {
            "success": True,
            "status": 200,
            "result": {
                "id": "lang1", 
                "name_ru": "Английский"
            },
            "error": None
        }
        
        api_client.get_user_word_data.return_value = {
            "success": True,
            "status": 200,
            "result": {
                "is_skipped": False,
                "check_interval": 2,
                "next_check_date": "2023-01-03T00:00:00Z"
            },
            "error": None
        }
        
        # Patch required functions
        with patch('app.bot.handlers.admin.admin_language_handlers.get_api_client_from_bot', return_value=api_client), \
            patch('app.bot.handlers.admin.admin_language_handlers.logger'), \
            patch('app.bot.handlers.admin.admin_language_handlers.format_date_standard', return_value="3 января 2023"), \
            patch('app.bot.handlers.admin.admin_language_handlers.get_word_actions_keyboard') as mock_keyboard, \
            patch('app.bot.handlers.admin.admin_language_handlers.show_language_edit_screen', AsyncMock()):
            
            # Setup mock keyboard function
            mock_keyboard.return_value = MagicMock()
            
            # Call the handler
            from app.bot.handlers.admin.admin_language_handlers import process_word_number_input
            await process_word_number_input(message, state)
            
            # Verify API calls
            api_client.get_word_by_number.assert_called_once_with("lang1", 5)
            api_client.get_language.assert_called_once_with("lang1")
            api_client.get_user_word_data.assert_called_once()
            
            # Check that state was cleared
            state.clear.assert_called_once()
            
            # Check that message was sent with word info
            message.reply.assert_called_once()
            args, kwargs = message.reply.call_args
            assert "Информация о слове" in args[0]
            assert "apple" in args[0]
            assert "яблоко" in args[0]
            assert "æpl" in args[0]
            assert "Английский" in args[0]
            assert "3 января 2023" in args[0]  # next check date
            assert kwargs["parse_mode"] == "HTML"
            assert kwargs["reply_markup"] == mock_keyboard.return_value
