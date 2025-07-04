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
            show_debug=show_debug
        )
        
        # Assert
        assert isinstance(keyboard, InlineKeyboardMarkup), "Should return InlineKeyboardMarkup"
        
        # Get all buttons from the keyboard
        all_buttons = []
        for row in keyboard.inline_keyboard:
            all_buttons.extend(row)
        
        # Verify button count
        assert len(all_buttons) == 10, "Should contain 10 buttons"
        
        # Verify each button contains expected text
        button_texts = [button.text for button in all_buttons]
        assert any("Изменить начальное слово" in text for text in button_texts), "Should have start word button"
        
        # Verify buttons have correct callback data
        callback_data = [button.callback_data for button in all_buttons]
        assert "settings_start_word" in callback_data
        assert "settings_toggle_skip_marked" in callback_data
        assert "settings_toggle_check_date" in callback_data
        assert "settings_toggle_show_debug" in callback_data
        