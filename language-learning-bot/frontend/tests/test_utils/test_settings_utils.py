"""
Tests for settings_utils module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.utils.settings_utils import (
    get_user_language_settings,
    save_user_language_settings,
    display_language_settings,
    get_show_hints_setting,
    get_show_debug_setting
)

class TestGetUserLanguageSettings:
    
    @pytest.mark.asyncio
    async def test_get_user_language_settings_success(self):
        # Setup
        message = AsyncMock()
        state = AsyncMock()
        
        # Настраиваем mock данные состояния
        state_data = {
            "db_user_id": "user123",
            "current_language": {"id": "lang123", "name_ru": "Английский"}
        }
        state.get_data.return_value = state_data
        
        # Настраиваем mock API клиент
        api_client = AsyncMock()
        api_client.get_user_language_settings.return_value = {
            "success": True,
            "result": {
                "start_word": 5,
                "skip_marked": True,
                "use_check_date": False,
                "show_hints": True
            }
        }
        
        # Патчим функцию получения API клиента
        with patch('app.utils.settings_utils.get_api_client_from_bot', return_value=api_client):
            # Execute
            settings = await get_user_language_settings(message, state)
            
            # Verify
            assert settings["start_word"] == 5
            assert settings["skip_marked"] is True
            assert settings["use_check_date"] is False
            assert settings["show_hints"] is True
            
            # Проверяем, что API клиент был вызван с правильными параметрами
            api_client.get_user_language_settings.assert_called_once_with("user123", "lang123")


class TestSaveUserLanguageSettings:
    
    @pytest.mark.asyncio
    async def test_save_user_language_settings_success(self):
        # Setup
        message = AsyncMock()
        state = AsyncMock()
        
        # Настраиваем mock данные состояния
        state_data = {
            "db_user_id": "user123",
            "current_language": {"id": "lang123", "name_ru": "Английский"}
        }
        state.get_data.return_value = state_data
        
        # Настраиваем настройки для сохранения
        settings_to_save = {
            "start_word": 10,
            "skip_marked": False,
            "use_check_date": True,
            "show_hints": True
        }
        
        # Настраиваем mock API клиент
        api_client = AsyncMock()
        api_client.update_user_language_settings.return_value = {
            "success": True,
            "result": settings_to_save
        }
        
        # Патчим функцию получения API клиента
        with patch('app.utils.settings_utils.get_api_client_from_bot', return_value=api_client):
            # Execute
            success = await save_user_language_settings(message, state, settings_to_save)
            
            # Verify
            assert success is True
            
            # Проверяем, что API клиент был вызван с правильными параметрами
            api_client.update_user_language_settings.assert_called_once_with(
                "user123", "lang123", settings_to_save
            )
            
            # Проверяем, что состояние было обновлено
            state.update_data.assert_called_once_with(**settings_to_save)


class TestDisplayLanguageSettings:
    
    @pytest.mark.asyncio
    async def test_display_language_settings_success(self):
        # Setup
        message = AsyncMock()
        state = AsyncMock()
        
        # Настраиваем mock get_user_language_settings
        settings = {
            "start_word": 5,
            "skip_marked": True,
            "use_check_date": False,
            "show_hints": True,
            "show_debug": False
        }
        
        # Данные состояния для языка
        state_data = {
            "current_language": {
                "id": "lang123",
                "name_ru": "Английский",
                "name_foreign": "English"
            }
        }
        state.get_data.return_value = state_data
        
        # Патчим импорт клавиатуры
        keyboard_mock = MagicMock()
        
        # Патчим необходимые функции
        with patch('app.utils.settings_utils.get_user_language_settings', return_value=settings), \
             patch('app.bot.keyboards.user_keyboards.create_settings_keyboard', return_value=keyboard_mock):
            
            # Execute
            await display_language_settings(message, state)
            
            # Verify
            # Проверяем, что сообщение было отправлено
            message.answer.assert_called_once()
            
            # Проверяем, что клавиатура была передана
            args, kwargs = message.answer.call_args
            assert kwargs["reply_markup"] == keyboard_mock
            assert "parse_mode" in kwargs


class TestGetShowHintsSetting:
    
    @pytest.mark.asyncio
    async def test_get_show_hints_setting_from_settings(self):
        # Setup
        message = AsyncMock()
        state = AsyncMock()
        
        # Патчим get_user_language_settings для возврата настроек
        settings = {"show_hints": True}
        
        # Патчим функцию получения настроек
        with patch('app.utils.settings_utils.get_user_language_settings', return_value=settings):
            # Execute
            result = await get_show_hints_setting(message, state)
            
            # Verify
            assert result is True


class TestGetShowDebugSetting:
    
    @pytest.mark.asyncio
    async def test_get_show_debug_setting_from_settings(self):
        # Setup
        message = AsyncMock()
        state = AsyncMock()
        
        # Патчим get_user_language_settings для возврата настроек
        settings = {"show_debug": True}
        
        # Патчим функцию получения настроек
        with patch('app.utils.settings_utils.get_user_language_settings', return_value=settings):
            # Execute
            result = await get_show_debug_setting(message, state)
            
            # Verify
            assert result is True
            