"""
Unit tests for API client language-related methods.
"""

import unittest
from unittest import mock
import os
import sys
import aiohttp
import pytest
from typing import Dict, List, Optional, Any

# Импортируем тестируемый модуль
# (Предполагается, что файл находится в директории tests/test_api/)
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from app.api.client import APIClient


class TestLanguageClient:
    """Test cases for APIClient language methods."""

    @pytest.fixture
    def api_client(self):
        """Fixture to create API client instance."""
        return APIClient(base_url="http://testserver", timeout=5)

    @pytest.mark.asyncio
    async def test_get_languages_success(self, api_client):
        """
        Проверяет успешное получение списка языков.
        
        Должен:
        - Вызвать _make_request с правильными параметрами
        - Вернуть список языков
        """
        # Подготовка данных для теста
        expected_response = {
            "success": True,
            "status": 200,
            "result": [
                {"_id": "1", "name_ru": "Английский", "name_foreign": "English"},
                {"_id": "2", "name_ru": "Испанский", "name_foreign": "Español"}
            ],
            "error": None
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод
        result = await api_client.get_languages()
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("GET", "/languages")
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_get_languages_error(self, api_client):
        """
        Проверяет обработку ошибки при получении списка языков.
        
        Должен:
        - Вызвать _make_request с правильными параметрами
        - Вернуть словарь с информацией об ошибке
        """
        # Создаем мок для метода _make_request, возвращающий словарь с ошибкой
        error_response = {
            "success": False,
            "status": 500,
            "result": None,
            "error": "Internal Server Error"
        }
        api_client._make_request = mock.AsyncMock(return_value=error_response)
        
        # Вызываем тестируемый метод
        result = await api_client.get_languages()
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("GET", "/languages")
        
        # Проверяем, что в случае ошибки возвращается словарь с ошибкой
        assert result == error_response

    @pytest.mark.asyncio
    async def test_get_language_success(self, api_client):
        """
        Проверяет успешное получение информации о языке по ID.
        
        Должен:
        - Вызвать _make_request с правильным endpoint (/languages/{language_id})
        - Вернуть данные языка
        """
        # Подготовка данных для теста
        language_id = "123abc"
        expected_response = {
            "success": True,
            "status": 200,
            "result": {
                "_id": language_id,
                "name_ru": "Английский",
                "name_foreign": "English",
                "created_at": "2023-06-15T12:00:00Z",
                "updated_at": "2023-06-15T12:00:00Z"
            },
            "error": None
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод
        result = await api_client.get_language(language_id)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("GET", f"/languages/{language_id}")
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_get_language_error(self, api_client):
        """
        Проверяет обработку ошибки при получении информации о языке по ID.
        
        Должен:
        - Вызвать _make_request с правильным endpoint (/languages/{language_id})
        - Вернуть словарь с информацией об ошибке
        """
        # Подготовка данных для теста
        language_id = "123abc"
        error_response = {
            "success": False,
            "status": 404,
            "result": None,
            "error": "Language not found"
        }
        
        # Создаем мок для метода _make_request, возвращающий словарь с ошибкой
        api_client._make_request = mock.AsyncMock(return_value=error_response)
        
        # Вызываем тестируемый метод
        result = await api_client.get_language(language_id)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("GET", f"/languages/{language_id}")
        
        # Проверяем, что в случае ошибки возвращается словарь с ошибкой
        assert result == error_response

    @pytest.mark.asyncio
    async def test_create_language_success(self, api_client):
        """
        Проверяет успешное создание нового языка.
        
        Должен:
        - Вызвать _make_request с методом POST и данными языка
        - Вернуть созданный язык
        """
        # Подготовка данных для теста
        language_data = {
            "name_ru": "Французский",
            "name_foreign": "Français"
        }
        
        expected_response = {
            "success": True,
            "status": 201,
            "result": {
                "_id": "456def",
                "name_ru": "Французский",
                "name_foreign": "Français",
                "created_at": "2023-06-16T10:30:00Z",
                "updated_at": "2023-06-16T10:30:00Z"
            },
            "error": None
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод
        result = await api_client.create_language(language_data)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("POST", "/languages", data=language_data)
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_create_language_error(self, api_client):
        """
        Проверяет обработку ошибки при создании нового языка.
        
        Должен:
        - Вызвать _make_request с методом POST и данными языка
        - Вернуть словарь с информацией об ошибке
        """
        # Подготовка данных для теста
        language_data = {
            "name_ru": "Французский",
            "name_foreign": "Français"
        }
        
        error_response = {
            "success": False,
            "status": 400,
            "result": None,
            "error": "Validation Error"
        }
        
        # Создаем мок для метода _make_request, возвращающий словарь с ошибкой
        api_client._make_request = mock.AsyncMock(return_value=error_response)
        
        # Вызываем тестируемый метод
        result = await api_client.create_language(language_data)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("POST", "/languages", data=language_data)
        
        # Проверяем, что в случае ошибки возвращается словарь с ошибкой
        assert result == error_response

    @pytest.mark.asyncio
    async def test_update_language_success(self, api_client):
        """
        Проверяет успешное обновление языка по ID.
        
        Должен:
        - Вызвать _make_request с методом PUT, endpoint /languages/{language_id} и данными для обновления
        - Вернуть обновленный язык
        """
        # Подготовка данных для теста
        language_id = "123abc"
        update_data = {
            "name_ru": "Английский (обновлен)",
            "name_foreign": "English (updated)"
        }
        
        expected_response = {
            "success": True,
            "status": 200,
            "result": {
                "_id": language_id,
                "name_ru": "Английский (обновлен)",
                "name_foreign": "English (updated)",
                "created_at": "2023-06-15T12:00:00Z",
                "updated_at": "2023-06-16T14:45:00Z"
            },
            "error": None
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод
        result = await api_client.update_language(language_id, update_data)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("PUT", f"/languages/{language_id}", data=update_data)
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_update_language_error(self, api_client):
        """
        Проверяет обработку ошибки при обновлении языка по ID.
        
        Должен:
        - Вызвать _make_request с методом PUT, endpoint /languages/{language_id} и данными для обновления
        - Вернуть словарь с информацией об ошибке
        """
        # Подготовка данных для теста
        language_id = "123abc"
        update_data = {
            "name_ru": "Английский (обновлен)",
            "name_foreign": "English (updated)"
        }
        
        error_response = {
            "success": False,
            "status": 404,
            "result": None,
            "error": "Language not found"
        }
        
        # Создаем мок для метода _make_request, возвращающий словарь с ошибкой
        api_client._make_request = mock.AsyncMock(return_value=error_response)
        
        # Вызываем тестируемый метод
        result = await api_client.update_language(language_id, update_data)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("PUT", f"/languages/{language_id}", data=update_data)
        
        # Проверяем, что в случае ошибки возвращается словарь с ошибкой
        assert result == error_response

    @pytest.mark.asyncio
    async def test_delete_language_success(self, api_client):
        """
        Проверяет успешное удаление языка по ID.
        
        Должен:
        - Вызвать _make_request с методом DELETE и endpoint /languages/{language_id}
        - Вернуть словарь с успешным результатом
        """
        # Подготовка данных для теста
        language_id = "123abc"
        
        expected_response = {
            "success": True,
            "status": 200,
            "result": {
                "message": "Language deleted successfully",
                "deleted": True
            },
            "error": None
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод
        result = await api_client.delete_language(language_id)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("DELETE", f"/languages/{language_id}")
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response
        assert result["success"] is True
        assert "deleted" in result["result"]
        assert result["result"]["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_language_error(self, api_client):
        """
        Проверяет обработку ошибки при удалении языка по ID.
        
        Должен:
        - Вызвать _make_request с методом DELETE и endpoint /languages/{language_id}
        - Вернуть словарь с информацией об ошибке
        """
        # Подготовка данных для теста
        language_id = "123abc"
        
        error_response = {
            "success": False,
            "status": 404,
            "result": None,
            "error": "Language not found"
        }
        
        # Создаем мок для метода _make_request, возвращающий словарь с ошибкой
        api_client._make_request = mock.AsyncMock(return_value=error_response)
        
        # Вызываем тестируемый метод
        result = await api_client.delete_language(language_id)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("DELETE", f"/languages/{language_id}")
        
        # Проверяем, что в случае ошибки возвращается словарь с ошибкой
        assert result == error_response
        assert result["success"] is False