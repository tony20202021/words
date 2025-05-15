"""
Unit tests for API client progress-related methods.
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


class TestProgressClient:
    """Test cases for APIClient progress methods."""

    @pytest.fixture
    def api_client(self):
        """Fixture to create API client instance."""
        return APIClient(base_url="http://testserver", timeout=5)

    @pytest.mark.asyncio
    async def test_get_user_progress_success(self, api_client):
        """
        Проверяет успешное получение прогресса пользователя с опциональной фильтрацией по языку.
        
        Должен:
        - Вызвать _make_request с endpoint /users/{user_id}/languages/{language_id}/progress
        - Вернуть информацию о прогрессе пользователя
        """
        # Подготовка данных для теста
        user_id = "user123"
        language_id = "123abc"
        
        expected_response = {
            "success": True,
            "status": 200,
            "result": {
                "language_name_ru": "Английский",
                "language_name_foreign": "English",
                "total_words": 1000,
                "words_studied": 150,
                "words_known": 75,
                "progress_percentage": 15.0,
                "next_review_count": 10,
                "last_active": "2023-06-16T12:00:00Z"
            },
            "error": None
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод
        result = await api_client.get_user_progress(user_id, language_id)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with(
            "GET", 
            f"/users/{user_id}/languages/{language_id}/progress"
        )
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_get_user_progress_error(self, api_client):
        """
        Проверяет обработку ошибки при получении прогресса пользователя.
        
        Должен:
        - Вызвать _make_request с endpoint /users/{user_id}/languages/{language_id}/progress
        - Вернуть структуру с информацией об ошибке
        """
        # Подготовка данных для теста
        user_id = "user123"
        language_id = "123abc"
        
        error_response = {
            "success": False,
            "status": 404,
            "result": None,
            "error": "User or language not found"
        }
        
        # Создаем мок для метода _make_request, возвращающий структуру с ошибкой
        api_client._make_request = mock.AsyncMock(return_value=error_response)
        
        # Вызываем тестируемый метод
        result = await api_client.get_user_progress(user_id, language_id)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with(
            "GET", 
            f"/users/{user_id}/languages/{language_id}/progress"
        )
        
        # Проверяем, что в случае ошибки возвращается структура с информацией об ошибке
        assert result == error_response
        assert result["success"] is False
        assert result["error"] == "User or language not found"

    @pytest.mark.asyncio
    async def test_get_study_words_success(self, api_client):
        """
        Проверяет успешное получение списка слов для изучения.
        
        Должен:
        - Вызвать _make_request с endpoint /users/{user_id}/languages/{language_id}/study
        - Передать параметры как query-параметры
        - Вернуть список слов для изучения
        """
        # Подготовка данных для теста
        user_id = "user123"
        language_id = "123abc"
        params = {
            "start_word": 1,
            "skip_marked": True,
            "use_check_date": True
        }
        limit = 100
        
        expected_params = {
            "start_word": 1,
            "skip_marked": "true",  # Изменено с True на "true"
            "use_check_date": "true",  # Изменено с True на "true"
            "limit": 100
        }   

        expected_response = {
            "success": True,
            "status": 200,
            "result": [
                {
                    "_id": "word1",
                    "language_id": language_id,
                    "word_foreign": "hello",
                    "translation": "привет",
                    "transcription": "həˈləʊ",
                    "word_number": 1,
                    "user_word_data": {
                        "score": 1,
                        "next_check_date": "2023-06-16T00:00:00Z",
                        "check_interval": 1
                    }
                },
                {
                    "_id": "word2",
                    "language_id": language_id,
                    "word_foreign": "world",
                    "translation": "мир",
                    "transcription": "wɜːld",
                    "word_number": 2,
                    "user_word_data": None
                }
            ],
            "error": None
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод
        result = await api_client.get_study_words(user_id, language_id, params, limit)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with(
            "GET", 
            f"/users/{user_id}/languages/{language_id}/study", 
            params=expected_params
        )
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_get_study_words_with_default_limit(self, api_client):
        """
        Проверяет получение списка слов для изучения с лимитом по умолчанию.
        
        Должен:
        - Вызвать _make_request с endpoint /users/{user_id}/languages/{language_id}/study
        - Добавить limit=100 (по умолчанию) к параметрам
        - Вернуть список слов для изучения
        """
        # Подготовка данных для теста
        user_id = "user123"
        language_id = "123abc"
        params = {
            "start_word": 1,
            "skip_marked": True,
            "use_check_date": True
        }
        
        expected_params = {
            "start_word": 1,
            "skip_marked": "true",  # Изменено с True на "true"
            "use_check_date": "true",  # Изменено с True на "true"
            "limit": 100
        }

        expected_response = {
            "success": True,
            "status": 200,
            "result": [
                {
                    "_id": "word1",
                    "language_id": language_id,
                    "word_foreign": "hello",
                    "translation": "привет",
                    "transcription": "həˈləʊ",
                    "word_number": 1
                }
            ],
            "error": None
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=expected_response)
        
        # Вызываем тестируемый метод без указания лимита
        result = await api_client.get_study_words(user_id, language_id, params)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with(
            "GET", 
            f"/users/{user_id}/languages/{language_id}/study", 
            params=expected_params
        )
        
        # Проверяем, что результат соответствует ожидаемому
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_get_study_words_error(self, api_client):
        """
        Проверяет обработку ошибки при получении списка слов для изучения.
        
        Должен:
        - Вызвать _make_request с endpoint /users/{user_id}/languages/{language_id}/study
        - Вернуть структуру с информацией об ошибке
        """
        # Подготовка данных для теста
        user_id = "user123"
        language_id = "123abc"
        params = {
            "start_word": 1,
            "skip_marked": True,
            "use_check_date": True
        }
        
        expected_params = {
            "start_word": 1,
            "skip_marked": "true",  # Изменено с True на "true"
            "use_check_date": "true",  # Изменено с True на "true"
            "limit": 100
        }
              
        error_response = {
            "success": False,
            "status": 404,
            "result": None,
            "error": "User or language not found"
        }
        
        # Создаем мок для метода _make_request
        api_client._make_request = mock.AsyncMock(return_value=error_response)
        
        # Вызываем тестируемый метод
        result = await api_client.get_study_words(user_id, language_id, params)
        
        # Проверяем, что _make_request был вызван с правильными параметрами
        api_client._make_request.assert_called_once_with(
            "GET", 
            f"/users/{user_id}/languages/{language_id}/study", 
            params=expected_params
        )
        
        # Проверяем, что результат содержит информацию об ошибке
        assert result == error_response
        assert result["success"] is False
        assert result["error"] == "User or language not found"