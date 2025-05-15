"""
Tests for word_data_utils module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.utils.word_data_utils import (
    ensure_user_word_data,
    update_word_score,
    get_hint_text
)


class TestEnsureUserWordData:
    
    @pytest.mark.asyncio
    async def test_update_existing_data(self):
        # Setup
        bot = MagicMock()
        api_client = AsyncMock()
        api_client.get_user_word_data.return_value = {
            "success": True,
            "result": {
                "word_id": "word123",
                "score": 0
            }
        }
        api_client.update_user_word_data.return_value = {
            "success": True,
            "result": {
                "word_id": "word123",
                "score": 1
            }
        }
        
        bot.return_value = api_client
        
        with patch('app.utils.word_data_utils.get_api_client_from_bot', return_value=api_client):
            # Execute
            success, result = await ensure_user_word_data(
                bot,
                "user123",
                "word123",
                {"score": 1}
            )
            
            # Verify
            assert success is True
            assert result["score"] == 1
            api_client.get_user_word_data.assert_called_once_with("user123", "word123")
            api_client.update_user_word_data.assert_called_once_with("user123", "word123", {"score": 1})
    
    @pytest.mark.asyncio
    async def test_create_new_data_with_word(self):
        # Setup
        bot = MagicMock()
        api_client = AsyncMock()
        api_client.get_user_word_data.return_value = {
            "success": False,
            "error": "Not found"
        }
        api_client.create_user_word_data.return_value = {
            "success": True,
            "result": {
                "word_id": "word123",
                "language_id": "lang123",
                "score": 1
            }
        }
        
        bot.return_value = api_client
        
        with patch('app.utils.word_data_utils.get_api_client_from_bot', return_value=api_client):
            # Execute
            success, result = await ensure_user_word_data(
                bot,
                "user123",
                "word123",
                {"score": 1},
                {"language_id": "lang123"}
            )
            
            # Verify
            assert success is True
            assert result["score"] == 1
            assert result["language_id"] == "lang123"
            api_client.get_user_word_data.assert_called_once_with("user123", "word123")
            api_client.create_user_word_data.assert_called_once_with("user123", {
                "word_id": "word123",
                "language_id": "lang123",
                "score": 1
            })
    
    @pytest.mark.asyncio
    async def test_create_fails_without_language_id(self):
        # Setup
        bot = MagicMock()
        api_client = AsyncMock()
        api_client.get_user_word_data.return_value = {
            "success": False,
            "error": "Not found"
        }
        
        bot.return_value = api_client
        message_obj = AsyncMock()
        
        with patch('app.utils.word_data_utils.get_api_client_from_bot', return_value=api_client):
            # Execute
            success, result = await ensure_user_word_data(
                bot,
                "user123",
                "word123",
                {"score": 1},
                None,
                message_obj
            )
            
            # Verify
            assert success is False
            assert result is None
            api_client.get_user_word_data.assert_called_once_with("user123", "word123")
            message_obj.answer.assert_called_once()


class TestUpdateWordScore:
    
    @pytest.mark.asyncio
    async def test_update_with_score_zero(self):
        # Setup
        bot = MagicMock()
        api_client = AsyncMock()
        api_client.get_user_word_data.return_value = {
            "success": True,
            "result": {
                "word_id": "word123",
                "score": 1,
                "check_interval": 2
            }
        }
        api_client.update_user_word_data.return_value = {
            "success": True,
            "result": {
                "word_id": "word123",
                "score": 0,
                "check_interval": 0,
                "next_check_date": None
            }
        }
        
        bot.return_value = api_client
        
        with patch('app.utils.word_data_utils.get_api_client_from_bot', return_value=api_client):
            with patch('app.utils.word_data_utils.ensure_user_word_data') as mock_ensure:
                mock_ensure.return_value = (True, {
                    "word_id": "word123",
                    "score": 0,
                    "check_interval": 0,
                    "next_check_date": None
                })
                
                # Execute
                success, result = await update_word_score(
                    bot,
                    "user123",
                    "word123",
                    score=0,
                    word={"language_id": "lang123"}
                )
                
                # Verify
                assert success is True
                assert result["score"] == 0
                assert result["check_interval"] == 0
                assert result["next_check_date"] is None
                
                # Check update_data passed to ensure_user_word_data
                update_data = mock_ensure.call_args[0][3]
                assert update_data["score"] == 0
                assert update_data["is_skipped"] is False
                assert update_data["check_interval"] == 0
                assert update_data["next_check_date"] is None
    
    @pytest.mark.asyncio
    async def test_update_with_score_one_new_interval(self):
        # Setup
        bot = MagicMock()
        api_client = AsyncMock()
        api_client.get_user_word_data.return_value = {
            "success": True,
            "result": {
                "word_id": "word123",
                "score": 0,
                "check_interval": 0
            }
        }
        
        bot.return_value = api_client
        
        with patch('app.utils.word_data_utils.get_api_client_from_bot', return_value=api_client):
            with patch('app.utils.word_data_utils.ensure_user_word_data') as mock_ensure:
                mock_ensure.return_value = (True, {
                    "word_id": "word123",
                    "score": 1,
                    "check_interval": 1,
                    "next_check_date": (datetime.now() + timedelta(days=1)).isoformat()
                })
                
                # Execute
                success, result = await update_word_score(
                    bot,
                    "user123",
                    "word123",
                    score=1,
                    word={"language_id": "lang123"}
                )
                
                # Verify
                assert success is True
                assert result["score"] == 1
                assert result["check_interval"] == 1
                
                # Check update_data passed to ensure_user_word_data
                update_data = mock_ensure.call_args[0][3]
                assert update_data["score"] == 1
                assert update_data["is_skipped"] is False
                assert update_data["check_interval"] == 1
                assert "next_check_date" in update_data


class TestGetHintText:
    
    @pytest.mark.asyncio
    async def test_get_hint_from_word_data(self):
        # Setup
        bot = MagicMock()
        api_client = AsyncMock()
        
        bot.return_value = api_client
        
        word_data = {
            "hint_syllables": "Тестовая фонетическая подсказка"
        }
        
        with patch('app.utils.word_data_utils.get_api_client_from_bot', return_value=api_client):
            # Execute
            result = await get_hint_text(
                bot,
                "user123",
                "word123",
                "hint_syllables",
                word_data
            )
            
            # Verify
            assert result == "Тестовая фонетическая подсказка"
            # API should not be called since hint found in word_data
            api_client.get_user_word_data.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_hint_from_user_word_data(self):
        # Setup
        bot = MagicMock()
        api_client = AsyncMock()
        
        bot.return_value = api_client
        
        word_data = {
            "user_word_data": {
                "hint_syllables": "Тестовая фонетическая подсказка"
            }
        }
        
        with patch('app.utils.word_data_utils.get_api_client_from_bot', return_value=api_client):
            # Execute
            result = await get_hint_text(
                bot,
                "user123",
                "word123",
                "hint_syllables",
                word_data
            )
            
            # Verify
            assert result == "Тестовая фонетическая подсказка"
            # API should not be called since hint found in user_word_data
            api_client.get_user_word_data.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_hint_from_api(self):
        # Setup
        bot = MagicMock()
        api_client = AsyncMock()
        api_client.get_user_word_data.return_value = {
            "success": True,
            "result": {
                "hint_syllables": "Тестовая фонетическая подсказка"
            }
        }
        
        bot.return_value = api_client
        
        word_data = {}  # Empty word data
        
        with patch('app.utils.word_data_utils.get_api_client_from_bot', return_value=api_client):
            # Execute
            result = await get_hint_text(
                bot,
                "user123",
                "word123",
                "hint_syllables",
                word_data
            )
            
            # Verify
            assert result == "Тестовая фонетическая подсказка"
            # API should be called since hint not found in word_data
            api_client.get_user_word_data.assert_called_once_with("user123", "word123")
    
    @pytest.mark.asyncio
    async def test_get_hint_not_found(self):
        # Setup
        bot = MagicMock()
        api_client = AsyncMock()
        api_client.get_user_word_data.return_value = {
            "success": True,
            "result": {}  # No hint in API result
        }
        
        bot.return_value = api_client
        
        word_data = {}  # Empty word data
        
        with patch('app.utils.word_data_utils.get_api_client_from_bot', return_value=api_client):
            # Execute
            result = await get_hint_text(
                bot,
                "user123",
                "word123",
                "hint_syllables",
                word_data
            )
            
            # Verify
            assert result is None
            # API should be called since hint not found in word_data
            api_client.get_user_word_data.assert_called_once_with("user123", "word123")