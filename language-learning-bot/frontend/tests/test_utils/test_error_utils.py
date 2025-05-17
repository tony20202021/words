"""
Tests for error_utils module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.utils.error_utils import (
    handle_api_error,
    validate_state_data,
    validate_word_data,
    get_word_id,
    is_command
)

class TestHandleApiError:
    
    @pytest.mark.asyncio
    async def test_handle_api_error_with_message(self):
        # Setup
        response = {
            "success": False,
            "status": 404,
            "error": "Ресурс не найден"
        }
        
        message = AsyncMock()
        log_prefix = "API Error"
        user_prefix = "Ошибка"
        
        # Execute
        result = await handle_api_error(response, message, log_prefix, user_prefix)
        
        # Verify
        assert result is True  # Функция вернула True, так как была ошибка
        message.answer.assert_called_once()  # Бот отправил сообщение
        
        # Проверяем, что в сообщении есть текст ошибки
        args, kwargs = message.answer.call_args
        error_message = args[0]
        assert user_prefix in error_message
        assert "Ресурс не найден" in error_message
        
    @pytest.mark.asyncio
    async def test_handle_api_error_with_callback_alternative(self):
        # Setup
        response = {
            "success": False,
            "status": 500,
            "error": "Ошибка сервера"
        }
        
        # Создаем мок для CallbackQuery
        callback = AsyncMock()
        callback.message = AsyncMock()
        
        # Execute
        result = await handle_api_error(response, callback)
        
        # Verify
        assert result is True  # Функция вернула True, так как была ошибка
        
        # Проверяем, что была попытка вызвать answer (либо на callback, либо на callback.message)
        assert callback.answer.called or callback.message.answer.called
        
        if callback.message.answer.called:
            args, kwargs = callback.message.answer.call_args
            error_message = args[0]
            assert "Ошибка: " in error_message
            assert "Ошибка сервера" in error_message

            args, kwargs = callback.answer.call_args
            assert "Произошла ошибка" in args[0]
            assert kwargs.get("show_alert") is True
        else:
            args, kwargs = callback.answer.call_args
            error_message = args[0]
            assert "Ошибка: " in error_message
            assert "Ошибка сервера" in error_message
        
    @pytest.mark.asyncio
    async def test_handle_api_error_no_error(self):
        # Setup
        response = {
            "success": True,
            "result": {"data": "some data"}
        }
        
        message = AsyncMock()
        
        # Execute
        result = await handle_api_error(response, message)
        
        # Verify
        assert result is False  # Функция вернула False, так как не было ошибки
        message.answer.assert_not_called()  # Бот не отправлял сообщение


class TestValidateStateData:
    
    @pytest.mark.asyncio
    async def test_validate_state_data_success(self):
        # Setup
        state = AsyncMock()
        state_data = {
            "user_id": "user123",
            "language_id": "lang123",
            "word_id": "word123"
        }
        state.get_data.return_value = state_data
        
        required_keys = ["user_id", "language_id"]
        message = AsyncMock()
        
        # Execute
        is_valid, data = await validate_state_data(state, required_keys, message)
        
        # Verify
        assert is_valid is True
        assert data == state_data
        message.answer.assert_not_called()  # Бот не отправлял сообщение об ошибке
    
    @pytest.mark.asyncio
    async def test_validate_state_data_missing_keys(self):
        # Setup
        state = AsyncMock()
        state_data = {
            "user_id": "user123",
            # language_id отсутствует
        }
        state.get_data.return_value = state_data
        
        required_keys = ["user_id", "language_id"]
        message = AsyncMock()
        
        # Execute
        is_valid, data = await validate_state_data(state, required_keys, message)
        
        # Verify
        assert is_valid is False
        assert data == state_data
        message.answer.assert_called_once()  # Бот отправил сообщение об ошибке
        
        # Проверяем, что в сообщении упоминается отсутствующий ключ
        args, kwargs = message.answer.call_args
        error_message = args[0]
        assert "language_id" in error_message


class TestValidateWordData:
    
    def test_validate_word_data_success(self):
        # Setup
        word = {
            "_id": "word123",
            "word_foreign": "Book",
            "translation": "Книга",
            "language_id": "lang123"
        }
        
        # Execute
        is_valid, missing = validate_word_data(word)
        
        # Verify
        assert is_valid is True
        assert missing == []
    
    def test_validate_word_data_missing_fields(self):
        # Setup
        word = {
            "_id": "word123",
            "word_foreign": "Book",
            # translation отсутствует
            # language_id отсутствует
        }
        
        # Execute
        is_valid, missing = validate_word_data(word)
        
        # Verify
        assert is_valid is False
        assert "translation" in missing
        assert "language_id" in missing


class TestGetWordId:
    
    def test_get_word_id_with_id(self):
        # Setup
        word = {"_id": "word123"}
        
        # Execute
        word_id = get_word_id(word)
        
        # Verify
        assert word_id == "word123"
    
    def test_get_word_id_with_alternate_fields(self):
        # Setup - проверка альтернативных полей
        word1 = {"id": "word123"}  # Поле id вместо _id
        word2 = {"word_id": "word123"}  # Поле word_id
        
        # Execute
        word_id1 = get_word_id(word1)
        word_id2 = get_word_id(word2)
        
        # Verify
        assert word_id1 == "word123"
        assert word_id2 == "word123"
    
    def test_get_word_id_not_found(self):
        # Setup
        word = {"some_field": "value"}  # Нет полей id, _id или word_id
        
        # Execute
        word_id = get_word_id(word)
        
        # Verify
        assert word_id is None


class TestIsCommand:
    
    def test_is_command_valid(self):
        # Setup
        text = "/start"
        
        # Execute
        result = is_command(text)
        
        # Verify
        assert result is True
    
    def test_is_command_with_bot_name(self):
        # Setup
        text = "/start@my_bot"
        
        # Execute
        result = is_command(text)
        
        # Verify
        assert result is True
    
    def test_is_command_invalid(self):
        # Setup
        text = "not a command"
        
        # Execute
        result = is_command(text)
        
        # Verify
        assert result is False
    
    def test_is_command_empty(self):
        # Setup
        text = ""
        
        # Execute
        result = is_command(text)
        
        # Verify
        assert result is False