"""
Unit tests for hint handlers of the Language Learning Bot.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from aiogram.types import Message, User
from aiogram.fsm.context import FSMContext

class TestHintHandlers:
    """Tests for the hint handlers."""
    
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
        message.bot = MagicMock()
        
        # Mock state
        state = MagicMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={})
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()
        state.clear = AsyncMock()
        
        # Mock API client
        api_client = AsyncMock()
        api_client.get_user_by_telegram_id = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [{"id": "user123"}],
            "error": None
        })
        
        return message, state, api_client
    
    @pytest.mark.asyncio
    async def test_cmd_hint(self, setup_mocks):
        """Test the /hint command handler."""
        message, state, api_client = setup_mocks
        
        # Патчим все зависимости с помощью patch.object
        with patch('app.bot.handlers.user.hint_handlers.process_hint', AsyncMock()) as mock_process_hint:
            
            # Вызываем тестируемую функцию
            import app.bot.handlers.user.hint_handlers as hint_handlers_module
            await hint_handlers_module.cmd_hint(message, state)
            
            mock_process_hint.assert_called_once()
            
            