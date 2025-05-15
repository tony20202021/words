"""
Unit tests for API client word-related methods.
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


class TestWordClient:
    """Test cases for APIClient word methods."""

    @pytest.fixture
    def api_client(self):
        """Fixture to create API client instance."""
        return APIClient(base_url="http://testserver", timeout=5)

    @pytest.mark.asyncio
    async def test_get_words_by_language_success(self, api_client):
        """
        Проверяет успешное получение списка слов для определенного языка с пагинацией.
        
        Должен:
        - Вызвать _make_request с endpoint /languages/{language_id}/words и параметрами skip, limit
        - Вернуть список слов
        """
        # Подготовка данных для теста
        language_id = "123abc"
        skip = 10
        limit = 20
        
        expected_response = {
            "success": True,
            "status": 200,
            "result": [
                {"_id": "word1", "language_id": language_id, "word_foreign": "hello", "translation": "привет"},
                {"_id": "word2", "language_id": language_id, "word_foreign": "world", "translation": "мир"}
            ],
            "error": None
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод
        result = await api_client.get_words_by_language(language_id, skip, limit)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with(
            "GET", 
            f"/languages/{language_id}/words", 
            params={"skip": skip, "limit": limit}
        )
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_get_words_by_language_error(self, api_client):
        """
        Проверяет обработку ошибки при получении списка слов для определенного языка.
        
        Должен:
        - Вызвать _make_request с endpoint /languages/{language_id}/words и параметрами skip, limit
        - Вернуть структуру с информацией об ошибке
        """
        # Подготовка данных для теста
        language_id = "123abc"
        skip = 10
        limit = 20
        
        error_response = {
            "success": False,
            "status": 404,
            "result": None,
            "error": "Language not found"
        }
        
        # Создаем мок для метода _make_request, возвращающий структуру с ошибкой
        api_client._make_request = mock.AsyncMock(return_value=error_response)
        
        # Вызываем тестируемый метод
        result = await api_client.get_words_by_language(language_id, skip, limit)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with(
            "GET", 
            f"/languages/{language_id}/words", 
            params={"skip": skip, "limit": limit}
        )
        
        # Проверяем, что в случае ошибки возвращается структура с информацией об ошибке
        assert result == error_response
        assert result["success"] is False
        assert result["error"] == "Language not found"

    @pytest.mark.asyncio
    async def test_get_word_success(self, api_client):
        """
        Проверяет успешное получение информации о слове по ID.
        
        Должен:
        - Вызвать _make_request с endpoint /words/{word_id}
        - Вернуть данные слова
        """
        # Подготовка данных для теста
        word_id = "word123"
        expected_response = {
            "success": True,
            "status": 200,
            "result": {
                "_id": word_id,
                "language_id": "123abc",
                "word_foreign": "hello",
                "translation": "привет",
                "transcription": "həˈləʊ",
                "word_number": 1
            },
            "error": None
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод
        result = await api_client.get_word(word_id)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("GET", f"/words/{word_id}")
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_get_word_error(self, api_client):
        """
        Проверяет обработку ошибки при получении информации о слове по ID.
        
        Должен:
        - Вызвать _make_request с endpoint /words/{word_id}
        - Вернуть структуру с информацией об ошибке
        """
        # Подготовка данных для теста
        word_id = "word123"
        
        error_response = {
            "success": False,
            "status": 404,
            "result": None,
            "error": "Word not found"
        }
        
        # Создаем мок для метода _make_request, возвращающий структуру с ошибкой
        api_client._make_request = mock.AsyncMock(return_value=error_response)
        
        # Вызываем тестируемый метод
        result = await api_client.get_word(word_id)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("GET", f"/words/{word_id}")
        
        # Проверяем, что в случае ошибки возвращается структура с информацией об ошибке
        assert result == error_response
        assert result["success"] is False
        assert result["error"] == "Word not found"

    @pytest.mark.asyncio
    async def test_get_word_by_number_success(self, api_client, monkeypatch):
        """
        Проверяет успешное получение слова по номеру и ID языка.
        """
        # Подготовка данных для теста
        language_id = "123abc"
        word_number = 1
        
        # Подготавливаем результат, который должен вернуть метод _make_request
        mock_response = {
            "success": True,
            "status": 200,
            "result": [
                {
                    "_id": "word123",
                    "language_id": language_id,
                    "word_foreign": "hello",
                    "translation": "привет",
                    "word_number": word_number
                }
            ],
            "error": None
        }
        
        # Функция, возвращающая результат вместо _make_request
        async def mock_make_request(*args, **kwargs):
            return mock_response
        
        # Патчим метод _make_request
        monkeypatch.setattr(api_client, "_make_request", mock_make_request)
        
        # Вызываем тестируемый метод
        result = await api_client.get_word_by_number(language_id, word_number)
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == mock_response
        assert result["success"] is True
        assert result["status"] == 200
        assert len(result["result"]) == 1
        assert result["result"][0]["_id"] == "word123"
        assert result["result"][0]["word_foreign"] == "hello"

    @pytest.mark.asyncio
    async def test_get_word_by_number_not_found(self, api_client, monkeypatch):
        """
        Проверяет случай, когда слово с заданным номером не найдено.
        """
        # Подготовка данных для теста
        language_id = "123abc"
        word_number = 999  # Несуществующий номер
        
        # Подготавливаем пустой результат, который должен вернуть метод _make_request
        empty_response = {
            "success": True,
            "status": 200,
            "result": [],  # Пустой список результатов
            "error": None
        }
        
        # Функция, возвращающая пустой результат вместо _make_request
        async def mock_make_request(*args, **kwargs):
            return empty_response
        
        # Патчим метод _make_request
        monkeypatch.setattr(api_client, "_make_request", mock_make_request)
        
        # Вызываем тестируемый метод
        result = await api_client.get_word_by_number(language_id, word_number)
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == empty_response
        assert result["success"] is True
        assert result["status"] == 200
        assert len(result["result"]) == 0
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_get_word_by_number_error(self, api_client, monkeypatch):
        """
        Проверяет обработку ошибки при получении слова по номеру.
        """
        # Подготовка данных для теста
        language_id = "123abc"
        word_number = 1
        
        # Подготавливаем результат с ошибкой, который должен вернуть метод _make_request
        error_response = {
            "success": False,
            "status": 404,
            "result": None,
            "error": "Language not found"
        }
        
        # Функция, возвращающая ошибочный результат вместо _make_request
        async def mock_make_request(*args, **kwargs):
            return error_response
        
        # Патчим метод _make_request
        monkeypatch.setattr(api_client, "_make_request", mock_make_request)
        
        # Вызываем тестируемый метод
        result = await api_client.get_word_by_number(language_id, word_number)
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == error_response
        assert result["success"] is False
        assert result["status"] == 404
        assert result["result"] is None
        assert result["error"] == "Language not found"

    @pytest.mark.asyncio
    async def test_create_word_success(self, api_client):
        """
        Проверяет успешное создание нового слова.
        
        Должен:
        - Вызвать _make_request с методом POST, endpoint /words и данными слова
        - Вернуть созданное слово
        """
        # Подготовка данных для теста
        word_data = {
            "language_id": "123abc",
            "word_foreign": "goodbye",
            "translation": "до свидания",
            "transcription": "ɡʊdˈbaɪ",
            "word_number": 2
        }
        
        expected_response = {
            "success": True,
            "status": 201,
            "result": {
                "_id": "word456",
                "language_id": "123abc",
                "word_foreign": "goodbye",
                "translation": "до свидания",
                "transcription": "ɡʊdˈbaɪ",
                "word_number": 2,
                "created_at": "2023-06-16T15:30:00Z",
                "updated_at": "2023-06-16T15:30:00Z"
            },
            "error": None
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод
        result = await api_client.create_word(word_data)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("POST", "/words", data=word_data)
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_create_word_error(self, api_client):
        """
        Проверяет обработку ошибки при создании нового слова.
        
        Должен:
        - Вызвать _make_request с методом POST, endpoint /words и данными слова
        - Вернуть структуру с информацией об ошибке
        """
        # Подготовка данных для теста
        word_data = {
            "language_id": "123abc",
            "word_foreign": "goodbye",
            "translation": "до свидания",
            "transcription": "ɡʊdˈbaɪ",
            "word_number": 2
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
        result = await api_client.create_word(word_data)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("POST", "/words", data=word_data)
        
        # Проверяем, что в случае ошибки возвращается структура с информацией об ошибке
        assert result == error_response
        assert result["success"] is False
        assert result["error"] == "Validation error"

    @pytest.mark.asyncio
    async def test_update_word_success(self, api_client):
        """
        Проверяет успешное обновление слова по ID.
        
        Должен:
        - Вызвать _make_request с методом PUT, endpoint /words/{word_id} и данными для обновления
        - Вернуть обновленное слово
        """
        # Подготовка данных для теста
        word_id = "word123"
        update_data = {
            "translation": "здравствуйте",
            "transcription": "həˈləʊ (обновлено)"
        }
        
        expected_response = {
            "success": True,
            "status": 200,
            "result": {
                "_id": word_id,
                "language_id": "123abc",
                "word_foreign": "hello",
                "translation": "здравствуйте",
                "transcription": "həˈləʊ (обновлено)",
                "word_number": 1,
                "created_at": "2023-06-15T12:00:00Z",
                "updated_at": "2023-06-16T16:45:00Z"
            },
            "error": None
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод
        result = await api_client.update_word(word_id, update_data)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("PUT", f"/words/{word_id}", data=update_data)
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_update_word_error(self, api_client):
        """
        Проверяет обработку ошибки при обновлении слова по ID.
        
        Должен:
        - Вызвать _make_request с методом PUT, endpoint /words/{word_id} и данными для обновления
        - Вернуть структуру с информацией об ошибке
        """
        # Подготовка данных для теста
        word_id = "word123"
        update_data = {
            "translation": "здравствуйте",
            "transcription": "həˈləʊ (обновлено)"
        }
        
        error_response = {
            "success": False,
            "status": 404,
            "result": None,
            "error": "Word not found"
        }
        
        # Создаем мок для метода _make_request, возвращающий структуру с ошибкой
        api_client._make_request = mock.AsyncMock(return_value=error_response)
        
        # Вызываем тестируемый метод
        result = await api_client.update_word(word_id, update_data)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("PUT", f"/words/{word_id}", data=update_data)
        
        # Проверяем, что в случае ошибки возвращается структура с информацией об ошибке
        assert result == error_response
        assert result["success"] is False
        assert result["error"] == "Word not found"

    @pytest.mark.asyncio
    async def test_delete_word_success(self, api_client):
        """
        Проверяет успешное удаление слова по ID.
        
        Должен:
        - Вызвать _make_request с методом DELETE и endpoint /words/{word_id}
        - Вернуть успешный результат удаления
        """
        # Подготовка данных для теста
        word_id = "word123"
        
        expected_response = {
            "success": True,
            "status": 200,
            "result": {
                "message": "Word deleted successfully",
                "deleted": True
            },
            "error": None
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод
        result = await api_client.delete_word(word_id)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("DELETE", f"/words/{word_id}")
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response
        assert result["success"] is True
        assert "deleted" in result["result"]
        assert result["result"]["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_word_error(self, api_client):
        """
        Проверяет обработку ошибки при удалении слова по ID.
        
        Должен:
        - Вызвать _make_request с методом DELETE и endpoint /words/{word_id}
        - Вернуть структуру с информацией об ошибке
        """
        # Подготовка данных для теста
        word_id = "word123"
        
        error_response = {
            "success": False,
            "status": 404,
            "result": None,
            "error": "Word not found"
        }
        
        # Создаем мок для метода _make_request, возвращающий структуру с ошибкой
        api_client._make_request = mock.AsyncMock(return_value=error_response)
        
        # Вызываем тестируемый метод
        result = await api_client.delete_word(word_id)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("DELETE", f"/words/{word_id}")
        
        # Проверяем, что в случае ошибки возвращается структура с информацией об ошибке
        assert result == error_response
        assert result["success"] is False
        assert result["error"] == "Word not found"