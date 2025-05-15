"""
Unit tests for API client statistics-related methods.
"""

import unittest
from unittest import mock
import os
import sys
import aiohttp
import pytest
from typing import Dict, List, Optional, Any

# Импортируем тестируемый модуль
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from app.api.client import APIClient


class TestStatisticsClient:
    """Test cases for APIClient statistics methods."""

    @pytest.fixture
    def api_client(self):
        """Fixture to create API client instance."""
        return APIClient(base_url="http://testserver", timeout=5)

    @pytest.mark.asyncio
    async def test_get_user_word_data_success(self, api_client):
        """
        Проверяет успешное получение данных пользователя для конкретного слова.
        
        Должен:
        - Вызвать _make_request с endpoint /users/{user_id}/word_data/{word_id}
        - Вернуть данные слова пользователя
        """
        # Подготовка данных для теста
        user_id = "user123"
        word_id = "word1"
        
        expected_response = {
            "success": True,
            "status": 200,
            "result": {
                "_id": "stat1",
                "user_id": user_id,
                "word_id": word_id,
                "language_id": "123abc",
                "hint_syllables": "hel-lo",
                "hint_association": "привет когда встречаешь друга",
                "hint_meaning": "приветствие при встрече",
                "hint_writing": "пишется с двумя l",
                "score": 1,
                "is_skipped": False,
                "next_check_date": "2023-06-20T00:00:00Z",
                "check_interval": 4,
                "created_at": "2023-06-15T12:00:00Z",
                "updated_at": "2023-06-16T15:30:00Z"
            },
            "error": None
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод
        result = await api_client.get_user_word_data(user_id, word_id)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with(
            "GET", 
            f"/users/{user_id}/word_data/{word_id}"
        )
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_get_user_word_data_error(self, api_client):
        """
        Проверяет обработку ошибки при получении данных пользователя для конкретного слова.
        
        Должен:
        - Вызвать _make_request с endpoint /users/{user_id}/word_data/{word_id}
        - Вернуть структуру с информацией об ошибке
        """
        # Подготовка данных для теста
        user_id = "user123"
        word_id = "word1"
        
        error_response = {
            "success": False,
            "status": 404,
            "result": None,
            "error": "User or word data not found"
        }
        
        # Создаем мок для метода _make_request, возвращающий структуру с ошибкой
        api_client._make_request = mock.AsyncMock(return_value=error_response)
        
        # Вызываем тестируемый метод
        result = await api_client.get_user_word_data(user_id, word_id)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with(
            "GET", 
            f"/users/{user_id}/word_data/{word_id}"
        )
        
        # Проверяем, что в случае ошибки возвращается структура с информацией об ошибке
        assert result == error_response
        assert result["success"] is False
        assert result["error"] == "User or word data not found"

    @pytest.mark.asyncio
    async def test_create_user_word_data_success(self, api_client):
        """
        Проверяет успешное создание данных слова для пользователя.
        
        Должен:
        - Вызвать _make_request с методом POST, endpoint /users/{user_id}/word_data
        - Вернуть созданные данные
        """
        # Подготовка данных для теста
        user_id = "user123"
        word_data = {
            "word_id": "word3",
            "language_id": "123abc",
            "hint_association": "новая подсказка",
            "score": 0,
            "is_skipped": False
        }
        
        expected_response = {
            "success": True,
            "status": 201,
            "result": {
                "_id": "stat3",
                "user_id": user_id,
                "word_id": "word3",
                "language_id": "123abc",
                "hint_syllables": None,
                "hint_association": "новая подсказка",
                "hint_meaning": None,
                "hint_writing": None,
                "score": 0,
                "is_skipped": False,
                "next_check_date": None,
                "check_interval": 0,
                "created_at": "2023-06-17T10:30:00Z",
                "updated_at": "2023-06-17T10:30:00Z"
            },
            "error": None
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод
        result = await api_client.create_user_word_data(user_id, word_data)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with(
            "POST", 
            f"/users/{user_id}/word_data", 
            data=word_data
        )
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_create_user_word_data_error(self, api_client):
        """
        Проверяет обработку ошибки при создании данных слова для пользователя.
        
        Должен:
        - Вызвать _make_request с методом POST, endpoint /users/{user_id}/word_data
        - Вернуть структуру с информацией об ошибке
        """
        # Подготовка данных для теста
        user_id = "user123"
        word_data = {
            "word_id": "word3",
            "language_id": "123abc",
            "hint_association": "новая подсказка",
            "score": 0,
            "is_skipped": False
        }
        
        error_response = {
            "success": False,
            "status": 400,
            "result": None,
            "error": "Validation error"
        }
        
        # Создаем мок для метода _make_request, возвращающий структуру с ошибкой
        api_client._make_request = mock.AsyncMock(return_value=error_response)
        
        # Вызываем тестируемый метод
        result = await api_client.create_user_word_data(user_id, word_data)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with(
            "POST", 
            f"/users/{user_id}/word_data", 
            data=word_data
        )
        
        # Проверяем, что в случае ошибки возвращается структура с информацией об ошибке
        assert result == error_response
        assert result["success"] is False
        assert result["error"] == "Validation error"

    @pytest.mark.asyncio
    async def test_update_user_word_data_success(self, api_client):
        """
        Проверяет успешное обновление данных слова для пользователя.
        
        Должен:
        - Вызвать _make_request с методом PUT, endpoint /users/{user_id}/word_data/{word_id}
        - Вернуть обновленные данные
        """
        # Подготовка данных для теста
        user_id = "user123"
        word_id = "word1"
        update_data = {
            "hint_association": "обновленная подсказка",
            "score": 1,
            "check_interval": 2
        }
        
        expected_response = {
            "success": True,
            "status": 200,
            "result": {
                "_id": "stat1",
                "user_id": user_id,
                "word_id": word_id,
                "language_id": "123abc",
                "hint_syllables": "hel-lo",
                "hint_association": "обновленная подсказка",
                "hint_meaning": "приветствие при встрече",
                "hint_writing": "пишется с двумя l",
                "score": 1,
                "is_skipped": False,
                "next_check_date": "2023-06-18T00:00:00Z",
                "check_interval": 2,
                "created_at": "2023-06-15T12:00:00Z",
                "updated_at": "2023-06-16T16:45:00Z"
            },
            "error": None
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод
        result = await api_client.update_user_word_data(user_id, word_id, update_data)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with(
            "PUT", 
            f"/users/{user_id}/word_data/{word_id}", 
            data=update_data
        )
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_update_user_word_data_error(self, api_client):
        """
        Проверяет обработку ошибки при обновлении данных слова для пользователя.
        
        Должен:
        - Вызвать _make_request с методом PUT, endpoint /users/{user_id}/word_data/{word_id}
        - Вернуть структуру с информацией об ошибке
        """
        # Подготовка данных для теста
        user_id = "user123"
        word_id = "word1"
        update_data = {
            "hint_association": "обновленная подсказка",
            "score": 1,
            "check_interval": 2
        }
        
        error_response = {
            "success": False,
            "status": 404,
            "result": None,
            "error": "User or word data not found"
        }
        
        # Создаем мок для метода _make_request, возвращающий структуру с ошибкой
        api_client._make_request = mock.AsyncMock(return_value=error_response)
        
        # Вызываем тестируемый метод
        result = await api_client.update_user_word_data(user_id, word_id, update_data)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with(
            "PUT", 
            f"/users/{user_id}/word_data/{word_id}", 
            data=update_data
        )
        
        # Проверяем, что в случае ошибки возвращается структура с информацией об ошибке
        assert result == error_response
        assert result["success"] is False
        assert result["error"] == "User or word data not found"