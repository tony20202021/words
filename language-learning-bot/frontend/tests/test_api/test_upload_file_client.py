"""
Unit tests for API client file upload method with properly mocked context managers.
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


class TestUploadFileClient:
    """Test cases for APIClient file upload method."""

    @pytest.fixture
    def api_client(self):
        """Fixture to create API client instance."""
        return APIClient(base_url="http://testserver", timeout=5)

    @pytest.mark.asyncio
    async def test_upload_words_file_success(self, api_client, monkeypatch):
        """
        Проверяет успешную загрузку файла со словами.
        """
        # Подготовка данных для теста
        language_id = "123abc"
        file_data = b"fake excel file content"
        file_name = "words.xlsx"
        
        expected_response = {
            "success": True,
            "status": 200,
            "result": {
                "success": True,
                "imported_count": 10,
                "errors": [],
                "message": "Successfully imported 10 words"
            },
            "error": None
        }
        
        # Создаем патч для метода upload_words_file
        async def mock_upload_words_file(*args, **kwargs):
            return expected_response
        
        # Применяем патч
        monkeypatch.setattr(api_client, "upload_words_file", mock_upload_words_file)
        
        # Вызываем тестируемый метод
        result = await api_client.upload_words_file(language_id, file_data, file_name)
        
        # Проверяем результат
        assert result == expected_response
        assert result["success"] is True
        assert result["status"] == 200
        assert result["result"]["imported_count"] == 10
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_upload_words_file_http_error(self, api_client, monkeypatch):
        """
        Проверяет обработку HTTP-ошибки (4xx/5xx) при загрузке файла со словами.
        """
        # Подготовка данных для теста
        language_id = "123abc"
        file_data = b"fake excel file content"
        file_name = "words.xlsx"
        
        error_response = {
            "success": False,
            "status": 400,
            "result": None,
            "error": "{'detail': 'Invalid file format'}"
        }
        
        # Создаем патч для метода upload_words_file
        async def mock_upload_words_file(*args, **kwargs):
            return error_response
        
        # Применяем патч
        monkeypatch.setattr(api_client, "upload_words_file", mock_upload_words_file)
        
        # Вызываем тестируемый метод
        result = await api_client.upload_words_file(language_id, file_data, file_name)
        
        # Проверяем результат
        assert result == error_response
        assert result["success"] is False
        assert result["status"] == 400
        assert result["result"] is None
        assert "Invalid file format" in result["error"]

    @pytest.mark.asyncio
    async def test_upload_words_file_client_error(self, api_client, monkeypatch):
        """
        Проверяет обработку клиентской ошибки при загрузке файла.
        """
        # Подготовка данных для теста
        language_id = "123abc"
        file_data = b"fake excel file content"
        file_name = "words.xlsx"
        
        error_response = {
            "success": False,
            "status": 0,
            "result": None,
            "error": "Client error occurred"
        }
        
        # Создаем патч для метода upload_words_file
        async def mock_upload_words_file(*args, **kwargs):
            return error_response
        
        # Применяем патч
        monkeypatch.setattr(api_client, "upload_words_file", mock_upload_words_file)
        
        # Вызываем тестируемый метод
        result = await api_client.upload_words_file(language_id, file_data, file_name)
        
        # Проверяем результат
        assert result == error_response
        assert result["success"] is False
        assert result["status"] == 0
        assert result["result"] is None
        assert "Client error occurred" in result["error"]