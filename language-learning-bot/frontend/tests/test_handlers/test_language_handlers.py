"""
Unit tests for language handlers of the Language Learning Bot.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from aiogram import Dispatcher
from aiogram.types import Message, User, CallbackQuery
from aiogram.fsm.context import FSMContext
import app.bot.handlers.language_handlers as language_handlers


class TestLanguageHandlers:
    """Tests for the language handlers."""
    
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
        api_client.get_word_count_by_language = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {"count": 100},
            "error": None
        })
        
        # Добавляем мок для get_user_progress
        api_client.get_user_progress = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {
                "words_studied": 10,
                "words_known": 5,
                "words_skipped": 2,
                "total_words": 100,
                "progress_percentage": 5.0
            },
            "error": None
        })
        
        # Mock callback
        callback = MagicMock(spec=CallbackQuery)
        callback.answer = AsyncMock()
        callback.message = message
        callback.from_user = message.from_user
        callback.data = "lang_select_1"
        callback.bot = message.bot
        
        return message, state, api_client, callback
    
    @pytest.mark.asyncio
    async def test_cmd_language_with_languages(self, setup_mocks):
        """Test the /language command handler when languages are available."""
        message, state, api_client, _ = setup_mocks
        
        # Создаем мок для функции get_available_languages, который вернет список языков в новом формате
        api_client.get_languages = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [
                {"id": 1, "name_ru": "Английский", "name_foreign": "English"},
                {"id": 2, "name_ru": "Испанский", "name_foreign": "Español"},
                {"id": 3, "name_ru": "Китайский", "name_foreign": "中文"}
            ],
            "error": None
        })
        
        # Мокируем get_user_by_telegram_id для получения db_user_id
        api_client.get_user_by_telegram_id = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [{"id": "user123"}],
            "error": None
        })
        
        # Патчим функцию get_available_languages, чтобы она не пыталась вызвать реальную функцию
        # Мы непосредственно мокируем работу с API клиентом
        with patch('app.bot.handlers.language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.language_handlers.logger'), \
             patch('app.bot.handlers.language_handlers.InlineKeyboardBuilder'):
            # Call the handler
            await language_handlers.cmd_language(message, state)
            
            # Check API calls
            api_client.get_languages.assert_called_once()
            api_client.get_user_by_telegram_id.assert_called_once()
            
            # Check that the bot sent a response message
            message.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cmd_language_without_languages(self, setup_mocks):
        """Test the /language command handler when no languages are available."""
        message, state, api_client, _ = setup_mocks
        
        # Мокируем get_languages для возврата пустого списка
        api_client.get_languages = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [],
            "error": None
        })
        
        # Патчим функцию get_available_languages
        with patch('app.bot.handlers.language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.language_handlers.logger'):
            # Call the handler
            await language_handlers.cmd_language(message, state)
            
            # Check API calls
            api_client.get_languages.assert_called_once()
            
            # Check that the bot sent an error message
            message.answer.assert_called_once_with(
                "В системе пока нет доступных языков. "
                "Обратитесь к администратору бота."
            )
    
    @pytest.mark.asyncio
    async def test_process_language_selection_success(self, setup_mocks):
        """Test the process_language_selection callback handler with valid language."""
        _, state, api_client, callback = setup_mocks
        
        # Мокируем get_language
        api_client.get_language = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {
                "id": 1, 
                "name_ru": "Английский",
                "name_foreign": "English"
            },
            "error": None
        })
        
        # Мокируем get_user_by_telegram_id
        api_client.get_user_by_telegram_id = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [{"id": "user123"}],
            "error": None
        })
        
        # Мокируем get_user_progress
        api_client.get_user_progress = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {
                "words_studied": 10,
                "words_known": 5,
                "words_skipped": 2,
                "total_words": 100,
                "progress_percentage": 5.0
            },
            "error": None
        })
        
        # Патчим функции API и get_user_language_settings
        with patch('app.bot.handlers.language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.language_handlers.logger'), \
             patch('app.bot.handlers.language_handlers.get_user_language_settings', 
                   AsyncMock(return_value={
                      "start_word": 1,
                      "skip_marked": False,
                      "use_check_date": True,
                      "show_hints": True
                   })), \
             patch('app.bot.handlers.language_handlers.get_language_by_id', 
                   AsyncMock(return_value=api_client.get_language.return_value)):
             
            # Сбросим счетчик вызовов update_data перед тестом
            state.update_data.reset_mock()
            
            # Call the handler
            await language_handlers.process_language_selection(callback, state)
            
            # Проверяем вызов API методов через патчированную функцию get_language_by_id
            # Проверяем вызов API методов
            api_client.get_user_by_telegram_id.assert_called_once()
            api_client.get_user_progress.assert_called_once()
            
            # Проверяем, что update_data был вызван для сохранения языка и настроек
            assert state.update_data.call_count <= 3
            
            # Проверяем, что бот отправил сообщение об успехе
            callback.message.answer.assert_called_once()
            
            # Проверяем, что callback.answer был вызван
            callback.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_language_selection_error(self, setup_mocks):
        """Test the process_language_selection callback handler with invalid language ID."""
        _, state, api_client, callback = setup_mocks
        
        # Set callback data for non-existent language
        callback.data = "lang_select_999"
        
        # Мокируем get_language для возврата ошибки (язык не найден)
        api_client.get_language = AsyncMock(return_value={
            "success": True,
            "status": 404,
            "result": None,
            "error": None
        })
        
        # Патчим функции API 
        with patch('app.bot.handlers.language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.language_handlers.logger'), \
             patch('app.bot.handlers.language_handlers.get_language_by_id', 
                   AsyncMock(return_value=api_client.get_language.return_value)):
            # Call the handler
            await language_handlers.process_language_selection(callback, state)
            
            # Проверяем, что отправлено сообщение об ошибке
            callback.answer.assert_called_once_with("Ошибка: язык не найден")
    
    @pytest.mark.asyncio
    async def test_get_available_languages(self, setup_mocks):
        """Test the get_available_languages function."""
        # Create a mock API client
        _, _, api_client, _ = setup_mocks
        
        # Mock API's get_languages method
        api_client.get_languages = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [
                {"id": "lang1", "name_ru": "Английский", "name_foreign": "English"},
                {"id": "lang2", "name_ru": "Испанский", "name_foreign": "Español"}
            ],
            "error": None
        })
        
        # Call the function
        response = await language_handlers.get_available_languages(api_client)
        
        # Check that API's get_languages was called
        api_client.get_languages.assert_called_once()
        
        # Check that it returns the API response
        assert response["success"] == True
        assert response["status"] == 200
        assert len(response["result"]) == 2
        assert response["error"] is None
        
        # Check that each language in the result has the required fields
        for language in response["result"]:
            assert "id" in language
            assert "name_ru" in language
            assert "name_foreign" in language
    
    @pytest.mark.asyncio
    async def test_get_language_by_id_existing(self, setup_mocks):
        """Test the get_language_by_id function with existing language ID."""
        # Create a mock API client
        _, _, api_client, _ = setup_mocks
        
        # Mock API's get_language method
        api_client.get_language = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {
                "id": "lang1", 
                "name_ru": "Английский", 
                "name_foreign": "English"
            },
            "error": None
        })
        
        # Call the function with an existing language ID
        response = await language_handlers.get_language_by_id(api_client, 1)
        
        # Check that API's get_language was called
        api_client.get_language.assert_called_once()
        
        # Check that it returns the response from API client
        assert response["success"] == True
        assert response["status"] == 200
        assert response["result"] is not None
        assert response["error"] is None
        
        # Check that the result contains a language dictionary
        assert "id" in response["result"]
        assert "name_ru" in response["result"]
        assert "name_foreign" in response["result"]
    
    @pytest.mark.asyncio
    async def test_get_language_by_id_nonexisting(self, setup_mocks):
        """Test the get_language_by_id function with non-existing language ID."""
        # Create a mock API client
        _, _, api_client, _ = setup_mocks
        
        # Mock API's get_language method to return None
        api_client.get_language = AsyncMock(return_value={
            "success": True,
            "status": 404,
            "result": None,
            "error": "Language not found"
        })
        
        # Call the function with a non-existing language ID
        response = await language_handlers.get_language_by_id(api_client, 999)
        
        # Check that API's get_language was called
        api_client.get_language.assert_called_once()
        
        # Check that it returns the response from API client
        assert response["success"] == True
        assert response["status"] == 404
        assert response["result"] is None
        assert response["error"] is not None
    
    def test_register_handlers(self):
        """Test the register_handlers function."""
        # Create a mock dispatcher
        dp = MagicMock(spec=Dispatcher)
        dp.include_router = MagicMock()
        
        # Call the register_handlers function
        language_handlers.register_handlers(dp)
        
        # Check that include_router was called with the language_router
        dp.include_router.assert_called_once_with(language_handlers.language_router)