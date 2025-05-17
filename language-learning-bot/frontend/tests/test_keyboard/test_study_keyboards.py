import pytest
from unittest.mock import patch, MagicMock

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.bot.keyboards.study_keyboards import create_word_keyboard


class TestStudyKeyboards:
    
    @patch('app.bot.keyboards.study_keyboards.setup_logger')
    @patch('app.bot.keyboards.study_keyboards.has_hint')
    @patch('app.bot.keyboards.study_keyboards.format_hint_button')
    @patch('app.bot.keyboards.study_keyboards.get_all_hint_types')
    def test_create_word_keyboard_not_shown(self, mock_hint_types, mock_format_button, 
                                         mock_has_hint, mock_logger):
        """
        Test creating word keyboard with default values when word is not shown.
        Check that:
        1. Function returns InlineKeyboardMarkup
        2. Keyboard contains expected buttons
        3. No hint buttons shown when show_hints=False
        """
        # Arrange
        mock_logger.return_value = MagicMock()
        mock_hint_types.return_value = ["syllables", "association"]
        mock_has_hint.return_value = False
        mock_format_button.return_value = "Mock Hint Button"
        
        word = {
            "_id": "word123",
            "word_foreign": "test",
            "translation": "тест",
            "transcription": "test",
            "user_word_data": {
                "is_skipped": False
            }
        }
        
        # Act
        keyboard = create_word_keyboard(
            word=word,
            word_shown=False,
            show_hints=False,  # No hint buttons
            used_hints=[]
        )
        
        # Assert
        assert isinstance(keyboard, InlineKeyboardMarkup), "Should return InlineKeyboardMarkup"
        
        # Get all buttons from the keyboard
        all_buttons = []
        for row in keyboard.inline_keyboard:
            all_buttons.extend(row)
        
        # Verify we have 3 buttons (know word, don't know, skip flag)
        assert len(all_buttons) == 3, "Should have 3 buttons without hints"
        
        # Verify button texts
        button_texts = [button.text for button in all_buttons]
        assert any("Я знаю это слово" in text for text in button_texts), "Should have 'know word' button"
        assert any("Не знаю" in text for text in button_texts), "Should have 'don't know' button"
        assert any("Флаг: сменить на" in text for text in button_texts), "Should have skip flag button"
        
        # Verify callback data
        callback_data = [button.callback_data for button in all_buttons]
        assert "word_know" in callback_data
        assert "show_word" in callback_data
        assert "toggle_word_skip" in callback_data
        
        # Verify no hint buttons were added
        mock_has_hint.assert_not_called()
        mock_format_button.assert_not_called()
    
    @patch('app.bot.keyboards.study_keyboards.setup_logger')
    @patch('app.bot.keyboards.study_keyboards.has_hint')
    @patch('app.bot.keyboards.study_keyboards.format_hint_button')
    @patch('app.bot.keyboards.study_keyboards.get_all_hint_types')
    def test_create_word_keyboard_shown(self, mock_hint_types, mock_format_button, 
                                     mock_has_hint, mock_logger):
        """
        Test creating word keyboard when word is shown.
        Check that:
        1. Function returns InlineKeyboardMarkup with "next word" button
        2. No "know word" or "don't know" buttons
        """
        # Arrange
        mock_logger.return_value = MagicMock()
        mock_hint_types.return_value = ["syllables", "association"]
        mock_has_hint.return_value = False
        mock_format_button.return_value = "Mock Hint Button"
        
        word = {
            "_id": "word123",
            "word_foreign": "test",
            "translation": "тест",
            "transcription": "test",
            "user_word_data": {
                "is_skipped": False
            }
        }
        
        # Act
        keyboard = create_word_keyboard(
            word=word,
            word_shown=True,  # Word is shown
            show_hints=False,
            used_hints=[]
        )
        
        # Assert
        assert isinstance(keyboard, InlineKeyboardMarkup), "Should return InlineKeyboardMarkup"
        
        # Get all buttons from the keyboard
        all_buttons = []
        for row in keyboard.inline_keyboard:
            all_buttons.extend(row)
        
        # Verify we have 2 buttons (next word, skip flag)
        assert len(all_buttons) == 2, "Should have 2 buttons when word is shown"
        
        # Verify button texts
        button_texts = [button.text for button in all_buttons]
        assert any("Следующее слово" in text for text in button_texts), "Should have 'next word' button"
        assert any("Флаг: сменить на" in text for text in button_texts), "Should have skip flag button"
        
        # Verify no "know word" or "don't know" buttons
        assert not any("Я знаю это слово" in text for text in button_texts), "Should not have 'know word' button"
        assert not any("Не знаю" in text for text in button_texts), "Should not have 'don't know' button"
    
    @patch('app.bot.keyboards.study_keyboards.setup_logger')
    @patch('app.bot.keyboards.study_keyboards.has_hint')
    @patch('app.bot.keyboards.study_keyboards.format_hint_button')
    @patch('app.bot.keyboards.study_keyboards.get_all_hint_types')
    def test_create_word_keyboard_with_hints(self, mock_hint_types, mock_format_button, 
                                          mock_has_hint, mock_logger):
        """
        Test creating word keyboard with hints shown.
        Check that:
        1. Function returns InlineKeyboardMarkup with hint buttons
        2. Hint buttons have correct callback data
        """
        # Arrange
        mock_logger.return_value = MagicMock()
        mock_hint_types.return_value = ["syllables", "association"]
        mock_has_hint.return_value = True  # Hints exist
        mock_format_button.return_value = "Mock Hint Button"
        
        word = {
            "_id": "word123",
            "word_foreign": "test",
            "translation": "тест",
            "transcription": "test",
            "user_word_data": {
                "is_skipped": False
            }
        }
        
        # Act
        keyboard = create_word_keyboard(
            word=word,
            word_shown=False,
            show_hints=True,  # Show hint buttons
            used_hints=[]
        )
        
        # Assert
        assert isinstance(keyboard, InlineKeyboardMarkup), "Should return InlineKeyboardMarkup"
        
        # Get all buttons from the keyboard
        all_buttons = []
        for row in keyboard.inline_keyboard:
            all_buttons.extend(row)
        
        # Check we have more buttons now (know word, don't know, 2 hints, skip flag)
        assert len(all_buttons) == 5, "Should have 5 buttons with hints"
        
        # Verify callback data for hint buttons
        callback_data = [button.callback_data for button in all_buttons]
        
        # Check for hint toggle callbacks
        hint_callbacks = [cb for cb in callback_data if "hint_toggle_" in cb]
        assert len(hint_callbacks) == 2, "Should have 2 hint toggle buttons"
        
        # Verify each hint type got a button with the correct action
        for hint_type in mock_hint_types.return_value:
            expected_callback = f"hint_toggle_{hint_type}_word123"
            assert any(expected_callback in cb for cb in callback_data), f"Should have button for {hint_type}"
            