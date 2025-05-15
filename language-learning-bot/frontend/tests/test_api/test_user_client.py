"""
Unit tests for API client user-related methods.
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


class TestUserClient:
    """Test cases for APIClient user methods."""

    @pytest.fixture
    def api_client(self):
        """Fixture to create API client instance."""
        return APIClient(base_url="http://testserver", timeout=5)

    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id_success(self, api_client):
        """
        Проверяет успешное получение пользователя по ID в Telegram.
        
        Должен:
        - Вызвать _make_request с endpoint /users и параметром telegram_id
        - Вернуть первого найденного пользователя
        """
        # Подготовка данных для теста
        telegram_id = 123456789
        
        expected_user = [{
            "_id": "user123",
            "telegram_id": telegram_id,
            "username": "john_doe",
            "first_name": "John",
            "last_name": "Doe",
            "is_admin": False,
            "created_at": "2023-06-15T12:00:00Z",
            "updated_at": "2023-06-15T12:00:00Z"
        }]
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_user)
        
        # Вызываем тестируемый метод
        result = await api_client.get_user_by_telegram_id(telegram_id)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with(
            "GET", 
            "/users", 
            params={"telegram_id": telegram_id}
        )
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_user

    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id_not_found(self, api_client):
        """
        Проверяет случай, когда пользователь с указанным telegram_id не найден.
        
        Должен:
        - Вызвать _make_request с endpoint /users и параметром telegram_id
        - Вернуть None, если пользователь не найден (пустой список)
        """
        # Подготовка данных для теста
        telegram_id = 123456789
        
        # Создаем мок для метода _make_request, возвращающий пустой список
        api_client._make_request = mock.AsyncMock(return_value=None)
        
        # Вызываем тестируемый метод
        result = await api_client.get_user_by_telegram_id(telegram_id)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with(
            "GET", 
            "/users", 
            params={"telegram_id": telegram_id}
        )
        
        # Проверяем, что результат None, так как пользователь не найден
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id_error(self, api_client):
        """
        Проверяет обработку ошибки при получении пользователя по ID в Telegram.
        
        Должен:
        - Вызвать _make_request с endpoint /users и параметром telegram_id
        - Вернуть None в случае ошибки
        """
        # Подготовка данных для теста
        telegram_id = 123456789
        
        # Создаем мок для метода _make_request, возвращающий None (ошибка)
        api_client._make_request = mock.AsyncMock(return_value=None)
        
        # Вызываем тестируемый метод
        result = await api_client.get_user_by_telegram_id(telegram_id)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with(
            "GET", 
            "/users", 
            params={"telegram_id": telegram_id}
        )
        
        # Проверяем, что в случае ошибки возвращается None
        assert result is None

    @pytest.mark.asyncio
    async def test_create_user_success(self, api_client):
        """
        Проверяет успешное создание нового пользователя.
        
        Должен:
        - Вызвать _make_request с методом POST, endpoint /users и данными пользователя
        - Вернуть созданного пользователя
        """
        # Подготовка данных для теста
        user_data = {
            "telegram_id": 123456789,
            "username": "john_doe",
            "first_name": "John",
            "last_name": "Doe",
            "is_admin": False
        }
        
        expected_response = {
            "_id": "user123",
            "telegram_id": 123456789,
            "username": "john_doe",
            "first_name": "John",
            "last_name": "Doe",
            "is_admin": False,
            "created_at": "2023-06-16T10:30:00Z",
            "updated_at": "2023-06-16T10:30:00Z"
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод
        result = await api_client.create_user(user_data)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("POST", "/users", data=user_data)
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_create_user_error(self, api_client):
        """
        Проверяет обработку ошибки при создании нового пользователя.
        
        Должен:
        - Вызвать _make_request с методом POST, endpoint /users и данными пользователя
        - Вернуть None в случае ошибки
        """
        # Подготовка данных для теста
        user_data = {
            "telegram_id": 123456789,
            "username": "john_doe",
            "first_name": "John",
            "last_name": "Doe",
            "is_admin": False
        }
        
        # Создаем мок для метода _make_request, возвращающий None (ошибка)
        api_client._make_request = mock.AsyncMock(return_value=None)
        
        # Вызываем тестируемый метод
        result = await api_client.create_user(user_data)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("POST", "/users", data=user_data)
        
        # Проверяем, что в случае ошибки возвращается None
        assert result is None

    @pytest.mark.asyncio
    async def test_update_user_success(self, api_client):
        """
        Проверяет успешное обновление пользователя по ID.
        
        Должен:
        - Вызвать _make_request с методом PUT, endpoint /users/{user_id} и данными для обновления
        - Вернуть обновленного пользователя
        """
        # Подготовка данных для теста
        user_id = "user123"
        update_data = {
            "first_name": "John (обновлен)",
            "is_admin": True
        }
        
        expected_response = {
            "_id": user_id,
            "telegram_id": 123456789,
            "username": "john_doe",
            "first_name": "John (обновлен)",
            "last_name": "Doe",
            "is_admin": True,
            "created_at": "2023-06-15T12:00:00Z",
            "updated_at": "2023-06-16T14:45:00Z"
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод
        result = await api_client.update_user(user_id, update_data)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("PUT", f"/users/{user_id}", data=update_data)
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_update_user_error(self, api_client):
        """
        Проверяет обработку ошибки при обновлении пользователя по ID.
        
        Должен:
        - Вызвать _make_request с методом PUT, endpoint /users/{user_id} и данными для обновления
        - Вернуть None в случае ошибки
        """
        # Подготовка данных для теста
        user_id = "user123"
        update_data = {
            "first_name": "John (обновлен)",
            "is_admin": True
        }
        
        # Создаем мок для метода _make_request, возвращающий None (ошибка)
        api_client._make_request = mock.AsyncMock(return_value=None)
        
        # Вызываем тестируемый метод
        result = await api_client.update_user(user_id, update_data)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with("PUT", f"/users/{user_id}", data=update_data)
        
        # Проверяем, что в случае ошибки возвращается None
        assert result is None