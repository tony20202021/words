"""
Unit tests for user handlers of the Language Learning Bot.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from aiogram import Dispatcher
from aiogram.types import Message, User, CallbackQuery
from aiogram.fsm.context import FSMContext
import app.bot.handlers.user_handlers as user_handlers


class TestUserHandlers:
    @pytest.fixture
    def setup_mocks(self):
        """Set up common mocks for tests."""
        # Mock message
        message = MagicMock(spec=Message)
        message.answer = AsyncMock()
        message.from_user = MagicMock(spec=User)
        message.from_user.id = 12345
        message.from_user.username = "test_user"
        message.from_user.first_name = "Test"
        message.from_user.last_name = "User"
        message.from_user.full_name = "Test User"
        
        # Mock state
        state = MagicMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={})
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()
        state.clear = AsyncMock()
        
        # Mock API client с корректным форматом ответов
        api_client = AsyncMock()
        api_client.get_user_by_telegram_id = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [],  # Пустой список, будет интерпретирован как отсутствие пользователя
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
        
        api_client.get_user_progress = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": None,
            "error": None
        })
        
        return message, state, api_client
    
    @pytest.fixture
    def setup_callback_mock(self):
        """Set up common mock for callback."""
        callback = MagicMock(spec=CallbackQuery)
        callback.answer = AsyncMock()
        callback.message = MagicMock(spec=Message)
        callback.message.answer = AsyncMock()
        callback.from_user = MagicMock(spec=User)
        callback.from_user.id = 12345
        callback.from_user.username = "test_user"
        callback.from_user.full_name = "Test User"
        
        return callback

    @pytest.mark.asyncio
    async def test_process_back_to_main(self, setup_mocks, setup_callback_mock):
        """Test the process_back_to_main callback handler."""
        _, state, api_client = setup_mocks
        callback = setup_callback_mock
        
        # Импортируем модуль, где определена тестируемая функция
        import app.bot.handlers.user.basic_handlers as basic_handlers_module
        
        # Патчим все зависимости с помощью patch.object
        with patch.object(basic_handlers_module, 'get_api_client_from_bot', return_value=api_client), \
            patch.object(basic_handlers_module, 'logger'), \
            patch.object(basic_handlers_module, 'handle_start_command', AsyncMock()) as mock_handle_start:
            
            # Вызываем тестируемую функцию
            await basic_handlers_module.process_back_to_main(callback, state)
            
            # Проверяем, что был вызван handle_start_command с правильными параметрами
            mock_handle_start.assert_called_once()
            assert mock_handle_start.call_args.args[0] == callback.message
            assert mock_handle_start.call_args.args[1] == state
            assert mock_handle_start.call_args.kwargs['user_id'] == callback.from_user.id
            assert mock_handle_start.call_args.kwargs['username'] == callback.from_user.username
            assert mock_handle_start.call_args.kwargs['full_name'] == callback.from_user.full_name
            assert mock_handle_start.call_args.kwargs['is_callback'] == True
            
            # Проверяем, что callback.answer был вызван
            callback.answer.assert_called_once()