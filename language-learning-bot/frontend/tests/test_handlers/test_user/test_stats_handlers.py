"""
Unit tests for stats handlers of the Language Learning Bot.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from aiogram.types import Message, User
from aiogram.fsm.context import FSMContext

class TestStatsHandlers:
    """Tests for the stats handlers."""
    
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
        state.get_data = AsyncMock(return_value={"db_user_id": "user123"})
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()
        
        # Mock API client
        api_client = AsyncMock()
        api_client.get_user_by_telegram_id = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [{"id": "user123"}],
            "error": None
        })
        
        api_client.get_languages = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [
                {"id": "lang1", "name_ru": "Английский", "name_foreign": "English"},
                {"id": "lang2", "name_ru": "Испанский", "name_foreign": "Español"}
            ],
            "error": None
        })
        
        api_client.get_word_count_by_language = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {"count": 1000},
            "error": None
        })
        
        api_client.get_user_progress = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {
                "language_id": "lang1",
                "language_name_ru": "Английский",
                "language_name_foreign": "English",
                "total_words": 1000,
                "words_studied": 50,
                "words_known": 30,
                "words_skipped": 20,
                "progress_percentage": 3.0,
                "last_study_date": "2023-04-15T12:30:45.123Z"
            },
            "error": None
        })
        
        return message, state, api_client

    @pytest.mark.asyncio
    async def test_cmd_stats(self, setup_mocks):
        """Test the /stats command handler."""
        message, state, api_client = setup_mocks
        
        # Изменим возвращаемое значение для get_user_progress, чтобы для второго языка 
        # не было статистики, что более соответствует реальной ситуации
        user_progress_mock = AsyncMock()
        # Для первого языка возвращаем статистику
        user_progress_mock.side_effect = [
            {
                "success": True,
                "status": 200,
                "result": {
                    "language_id": "lang1",
                    "language_name_ru": "Английский",
                    "language_name_foreign": "English",
                    "total_words": 1000,
                    "words_studied": 50,
                    "words_known": 30,
                    "words_skipped": 20,
                    "progress_percentage": 3.0,
                    "last_study_date": "2023-04-15T12:30:45.123Z"
                },
                "error": None
            },
            # Для второго языка возвращаем пустую статистику
            {
                "success": True,
                "status": 200,
                "result": None,
                "error": None
            }
        ]
        api_client.get_user_progress = user_progress_mock
        
        # Импортируем модуль, где определена тестируемая функция
        import app.bot.handlers.user.stats_handlers as stats_handlers_module
        
        # Патчим все зависимости с помощью patch.object
        with patch.object(stats_handlers_module, 'get_api_client_from_bot', return_value=api_client), \
            patch.object(stats_handlers_module, 'logger'):
            
            # Вызываем тестируемую функцию
            await stats_handlers_module.cmd_stats(message, state)
            
            # Проверяем, что данные состояния были сохранены
            state.set_state.assert_called_once()
            
            # Проверяем, что API клиент был вызван с правильными аргументами
            api_client.get_user_by_telegram_id.assert_called_once_with(message.from_user.id)
            api_client.get_languages.assert_called_once()
            
            # Проверяем, что был вызван get_word_count_by_language хотя бы раз
            assert api_client.get_word_count_by_language.called
            
            # Проверяем, что был вызван get_user_progress хотя бы раз
            assert api_client.get_user_progress.called
            
            # Проверяем, что бот отправил ответное сообщение
            assert message.answer.call_count == 3
            
            # Проверяем, что сообщение содержит информацию о статистике
            answer_text = message.answer.call_args.args[0]
            assert "Статистика" in answer_text
            
            # Проверка наличия данных о языке с прогрессом
            assert "Английский" in answer_text
            assert "Испанский" in answer_text
            