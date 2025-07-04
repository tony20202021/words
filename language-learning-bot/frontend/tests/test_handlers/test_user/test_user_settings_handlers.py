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
    """Tests for the user handlers."""
    
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
    async def test_process_settings_toggle_show_debug(self, setup_mocks, setup_callback_mock):
        """Test the process_settings_toggle_show_debug callback handler."""
        _, state, _ = setup_mocks
        callback = setup_callback_mock
        
        # Устанавливаем существующие данные состояния
        state.get_data.return_value = {
            "start_word": 5,
            "skip_marked": True,
            "use_check_date": True,
            "show_debug": False,  # Изначально отключено
            "current_language": {
                "id": "lang123",
                "name_ru": "Английский",
                "name_foreign": "English"
            }
        }
        
        # Импортируем модуль, где определена тестируемая функция
        import app.bot.handlers.user.settings_handlers as settings_handlers_module
        
        # Патчим все зависимости с помощью patch.object
        with patch.object(settings_handlers_module, 'logger'), \
            patch.object(settings_handlers_module, 'get_user_language_settings', AsyncMock(return_value={
                "start_word": 5,
                "skip_marked": True,
                "use_check_date": True,
                "show_debug": False
            })), \
            patch.object(settings_handlers_module, 'save_user_language_settings', AsyncMock(return_value=True)), \
            patch.object(settings_handlers_module, 'display_language_settings', AsyncMock()) as display_mock:
            
            # Вызываем тестируемую функцию
            await settings_handlers_module.process_toggle_show_debug(callback, state)
            
            # Проверяем, что была вызвана функция get_user_language_settings для получения текущих настроек
            assert settings_handlers_module.get_user_language_settings.called
            
            # Проверяем, что была вызвана функция save_user_language_settings с инвертированным значением show_debug
            settings_arg = settings_handlers_module.save_user_language_settings.call_args.args[2]
            assert settings_arg["show_debug"] is True
            
            # Проверяем, что была вызвана функция display_language_settings для показа обновленных настроек
            assert display_mock.called
            
            # Проверяем, что callback.answer был вызван
            callback.answer.assert_called_once()
