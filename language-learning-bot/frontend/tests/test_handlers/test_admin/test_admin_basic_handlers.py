"""
Unit tests for basic admin handlers.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from aiogram import Dispatcher
from aiogram.types import Message, User, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.bot.handlers.admin.admin_basic_handlers import cmd_admin, cmd_bot_stats


class TestBasicAdminHandlers:
    """Tests for the basic admin handlers."""

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
        
        # Mock API client с новой структурой ответа
        api_client = MagicMock()
        
        # Mock для get_user_by_telegram_id
        api_client.get_user_by_telegram_id = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [],  # Пустой список, будет интерпретирован как отсутствие пользователя
            "error": None
        })
        
        # Mock для create_user
        api_client.create_user = AsyncMock(return_value={
            "success": True,
            "status": 201,
            "result": {"id": "user123", "is_admin": False},
            "error": None
        })
        
        # Mock для get_languages
        api_client.get_languages = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [],
            "error": None
        })
        
        # Mock для get_words_by_language
        api_client.get_words_by_language = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [],
            "error": None
        })
        
        # Mock для get_user_progress
        api_client.get_user_progress = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": None,
            "error": None
        })
        
        # Добавляем моки для статистики
        api_client.get_users_count = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {"count": 10},
            "error": None
        })
        
        api_client.get_word_count_by_language = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {"count": 100},
            "error": None
        })
        
        api_client.get_language_active_users = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {"count": 5},
            "error": None
        })
        
        return message, state, api_client

    @pytest.mark.asyncio
    async def test_cmd_admin_authorized(self, setup_mocks):
        """Test the /admin command handler for authorized admin."""
        message, state, api_client = setup_mocks
        mock_handle_admin = AsyncMock(return_value=True)
        
        # Patch the logger and API client
        with patch('app.bot.handlers.admin.admin_basic_handlers.handle_admin_mode', mock_handle_admin), \
            patch('app.bot.handlers.admin.admin_basic_handlers.logger'):
            # Call the handler
            await cmd_admin(message, state)
            
            # Check that handle_admin_mode was called with correct parameters
            mock_handle_admin.assert_called_once_with(message, state)
            
    @pytest.mark.asyncio
    async def test_cmd_bot_stats(self, setup_mocks):
        """Test the cmd_bot_stats handler."""
        message, state, api_client = setup_mocks
        mock_handle_stats = AsyncMock(return_value=True)

        # Patch the handle_admin_mode function to avoid sending additional messages
        with patch('app.bot.handlers.admin.admin_basic_handlers.handle_stats', mock_handle_stats), \
            patch('app.bot.handlers.admin.admin_basic_handlers.logger'):
            
            # Call the handler
            await cmd_bot_stats(message, state)
            
            # Verify API calls
            mock_handle_stats.assert_called_once_with(message, state, is_callback=False)

    @pytest.mark.asyncio
    async def test_handle_admin_mode(self, setup_mocks):
        """Test the handle_admin_mode function with authorized admin."""
        message, state, api_client = setup_mocks
        mock_is_user_admin = AsyncMock(return_value=True)
        mock_keyboard_result = MagicMock()  # Результат, который вернет функция
        mock_get_admin_keyboard = MagicMock(return_value=mock_keyboard_result)
        
        # Patch the logger, API client and keyboard function
        with patch('app.bot.handlers.admin.admin_basic_handlers.is_user_admin', mock_is_user_admin), \
            patch('app.bot.handlers.admin.admin_basic_handlers.logger'), \
            patch('app.bot.handlers.admin.admin_basic_handlers.get_admin_keyboard', mock_get_admin_keyboard):
            
            # Call the function
            from app.bot.handlers.admin.admin_basic_handlers import handle_admin_mode
            result = await handle_admin_mode(message, state)
            
            # Check result value
            assert result is True
            
            # Check that keyboard function was called
            mock_get_admin_keyboard.assert_called_once()
            
            # Check that message was sent with admin mode info
            message.answer.assert_called_once()
            args, kwargs = message.answer.call_args
            assert "Режим администратора активирован" in args[0]
            assert kwargs["reply_markup"] == mock_keyboard_result

    @pytest.mark.asyncio
    async def test_process_back_to_admin(self, setup_mocks):
        """Test the process_back_to_admin callback handler."""
        _, state, api_client = setup_mocks
        
        # Create a mock callback
        callback = AsyncMock()
        handle_admin_mode_result = MagicMock()
        mock_handle_admin_mode = AsyncMock(return_value=handle_admin_mode_result)
        
        # Patch the handle_admin_mode function to avoid duplicate testing
        with patch('app.bot.handlers.admin.admin_basic_handlers.handle_admin_mode', mock_handle_admin_mode):
            
            # Call the function
            from app.bot.handlers.admin.admin_basic_handlers import process_back_to_admin
            await process_back_to_admin(callback, state)
            
            # Check that handle_admin_mode was called with correct parameters
            mock_handle_admin_mode.assert_called_once_with(callback, state, is_callback=True)
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_back_to_main(self, setup_mocks):
        """Test the process_back_to_main callback handler."""
        _, state, _ = setup_mocks
        
        # Create a mock callback
        callback = AsyncMock()
        callback.message = AsyncMock()
        mock_handle_start = AsyncMock()
        
        with patch('app.bot.handlers.admin.admin_basic_handlers.logger'), \
            patch('app.bot.handlers.admin.admin_basic_handlers.handle_start_command', mock_handle_start):
            
            # Call the function
            from app.bot.handlers.admin.admin_basic_handlers import process_back_to_main
            await process_back_to_main(callback, state)
            
            # Check that message was sent about exiting admin mode
            callback.message.answer.assert_called_once_with("✅ Вы вышли из режима администратора")
            
            # Check that handle_start_command was called with correct parameters
            mock_handle_start.assert_called_once()
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_process_admin_languages(self, setup_mocks):
        """Test the process_admin_languages callback handler."""
        _, state, _ = setup_mocks
        
        # Create a mock callback
        callback = MagicMock()
        callback.from_user = MagicMock()
        callback.from_user.id = 12345
        callback.from_user.username = "admin_user"
        callback.from_user.full_name = "Admin User"
        callback.answer = AsyncMock()
        
        # Patch the handle_language_management function to avoid duplicate testing
        with patch('app.bot.handlers.admin.admin_basic_handlers.handle_language_management', AsyncMock(return_value=True)) as mock_handle_languages:
            
            # Call the function
            from app.bot.handlers.admin.admin_basic_handlers import process_admin_languages
            await process_admin_languages(callback, state)
            
            # Check that handle_language_management was called with correct parameters
            mock_handle_languages.assert_called_once_with(callback, state, is_callback=True)
            
            # Check that callback.answer was called
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_stats(self, setup_mocks):
        """Test the handle_stats function."""
        message, state, api_client = setup_mocks
        get_api_client_from_bot_mock = MagicMock(return_value=api_client)
        mock_is_user_admin = AsyncMock(return_value=True)
        mock_handle_admin_mode = AsyncMock(return_value=True)
        
        api_client.get_languages.return_value = {
            "success": True,
            "status": 200,
            "result": [
                {"id": "lang1", "name_ru": "Английский", "name_foreign": "English"}
            ],
            "error": None
        }
        
        api_client.get_users_count.return_value = {
            "success": True,
            "status": 200,
            "result": {"count": 10},
            "error": None
        }
        
        api_client.get_word_count_by_language.return_value = {
            "success": True,
            "status": 200,
            "result": {"count": 1000},
            "error": None
        }
        
        api_client.get_language_active_users.return_value = {
            "success": True,
            "status": 200,
            "result": {"count": 5},
            "error": None
        }
        
        # Patch dependencies
        with patch('app.bot.handlers.admin.admin_basic_handlers.get_api_client_from_bot', get_api_client_from_bot_mock), \
            patch('app.bot.handlers.admin.admin_basic_handlers.is_user_admin', mock_is_user_admin), \
            patch('app.bot.handlers.admin.admin_basic_handlers.logger'), \
            patch('app.bot.handlers.admin.admin_basic_handlers.handle_admin_mode', mock_handle_admin_mode):
            
            # Call the function
            from app.bot.handlers.admin.admin_basic_handlers import handle_stats
            from app.bot.states.centralized_states import AdminStates

            result = await handle_stats(message, state)

            # Check result
            assert result is True
            
            state.set_state.assert_called_once_with(AdminStates.viewing_admin_stats)
            get_api_client_from_bot_mock.assert_called_once_with(message.bot)
            mock_is_user_admin.assert_called_once_with(message, state)

            api_client.get_languages.assert_called_once()
            
            api_client.get_users_count.assert_called_once()
            api_client.get_word_count_by_language.assert_called_once_with("lang1")
            api_client.get_language_active_users.assert_called_once_with("lang1")
            
            # Check that statistics message was sent
            message.answer.assert_called_once()
            args, _ = message.answer.call_args
            assert "Статистика использования бота" in args[0]
            assert "Всего пользователей: 10" in args[0]
            assert "Английский" in args[0]
            
            # Check that handle_admin_mode was called to redisplay admin panel
            mock_handle_admin_mode.assert_called_once_with(message, state, is_callback=False)
