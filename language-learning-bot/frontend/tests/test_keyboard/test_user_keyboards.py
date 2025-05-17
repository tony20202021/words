import pytest
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.user_keyboards import create_settings_keyboard


class TestUserKeyboards:
    
    def test_create_settings_keyboard(self):
        """
        Test creating settings keyboard with default values.
        Verify that:
        1. Function returns InlineKeyboardMarkup
        2. Keyboard contains 5 buttons
        3. Button texts contain expected strings
        """
        # Arrange
        skip_marked = False
        use_check_date = True
        show_hints = True
        show_debug = False
        
        # Act
        keyboard = create_settings_keyboard(
            skip_marked=skip_marked,
            use_check_date=use_check_date,
            show_hints=show_hints,
            show_debug=show_debug
        )
        
        # Assert
        assert isinstance(keyboard, InlineKeyboardMarkup), "Should return InlineKeyboardMarkup"
        
        # Get all buttons from the keyboard
        all_buttons = []
        for row in keyboard.inline_keyboard:
            all_buttons.extend(row)
        
        # Verify button count
        assert len(all_buttons) == 5, "Should contain 5 buttons"
        
        # Verify each button contains expected text
        button_texts = [button.text for button in all_buttons]
        assert any("Изменить начальное слово" in text for text in button_texts), "Should have start word button"
        assert any("Помеченные слова: сменить на \"Пропускать\"" in text for text in button_texts), "Should have skip marked button with correct text"
        assert any("Период проверки: сменить на \"Не учитывать\"" in text for text in button_texts), "Should have check date button with correct text"
        assert any("Подсказки: сменить на \"Пропускать\"" in text for text in button_texts), "Should have hints button with correct text"
        assert any("Отладочная информация: сменить на \"Показывать\"" in text for text in button_texts), "Should have debug button with correct text"
        
        # Verify buttons have correct callback data
        callback_data = [button.callback_data for button in all_buttons]
        assert "settings_start_word" in callback_data
        assert "settings_toggle_skip_marked" in callback_data
        assert "settings_toggle_check_date" in callback_data
        assert "settings_toggle_show_hints" in callback_data
        assert "settings_toggle_show_debug" in callback_data
        