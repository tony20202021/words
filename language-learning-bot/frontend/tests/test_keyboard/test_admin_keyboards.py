import pytest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.bot.keyboards.admin_keyboards import (
    get_admin_keyboard,
    get_languages_keyboard,
    get_edit_language_keyboard,
    get_back_to_languages_keyboard,
    get_back_to_admin_keyboard,
    get_yes_no_keyboard,
    get_upload_columns_keyboard,
    get_word_actions_keyboard
)


class TestAdminKeyboards:
    
    def test_get_admin_keyboard(self):
        """
        Test creating admin menu keyboard.
        Check that:
        1. Function returns InlineKeyboardMarkup
        2. Keyboard contains expected buttons with correct texts and callbacks
        """
        # Act
        keyboard = get_admin_keyboard()
        
        # Assert
        assert isinstance(keyboard, InlineKeyboardMarkup), "Should return InlineKeyboardMarkup"
        
        # Get all buttons
        all_buttons = []
        for row in keyboard.inline_keyboard:
            all_buttons.extend(row)
        
        # Check count
        assert len(all_buttons) == 3, "Should have 3 buttons"
        
        # Check texts
        button_texts = [button.text for button in all_buttons]
        assert any("Управление языками" in text for text in button_texts), "Should have languages management button"
        assert any("Статистика" in text for text in button_texts), "Should have statistics button"
        assert any("Выйти из режима администратора" in text for text in button_texts), "Should have exit button"
        
        # Check callback data
        callback_data = [button.callback_data for button in all_buttons]
        assert "admin_languages" in callback_data
        assert "admin_stats_callback" in callback_data
        assert "back_to_start" in callback_data
    
    def test_get_languages_keyboard(self):
        """
        Test creating languages list keyboard.
        Check that:
        1. Function returns InlineKeyboardMarkup
        2. Keyboard contains buttons for each language plus extra buttons
        """
        # Arrange
        languages = [
            {"_id": "lang1", "name_ru": "Английский", "name_foreign": "English"},
            {"id": "lang2", "name_ru": "Французский", "name_foreign": "Français"}
        ]
        
        # Act
        keyboard = get_languages_keyboard(languages)
        
        # Assert
        assert isinstance(keyboard, InlineKeyboardMarkup), "Should return InlineKeyboardMarkup"
        
        # Get all buttons
        all_buttons = []
        for row in keyboard.inline_keyboard:
            all_buttons.extend(row)
        
        # Check count (2 languages + create + back = 4 buttons)
        assert len(all_buttons) == 4, "Should have 4 buttons"
        
        # Check texts
        button_texts = [button.text for button in all_buttons]
        assert any("Английский (English)" in text for text in button_texts), "Should have button for English"
        assert any("Французский (Français)" in text for text in button_texts), "Should have button for French"
        assert any("Создать новый язык" in text for text in button_texts), "Should have create language button"
        assert any("Вернуться к администрированию" in text for text in button_texts), "Should have back button"
        
        # Check callback data
        callback_data = [button.callback_data for button in all_buttons]
        assert "edit_language_lang1" in callback_data
        assert "edit_language_lang2" in callback_data
        assert "create_language" in callback_data
        assert "back_to_admin" in callback_data
    
    def test_get_edit_language_keyboard(self):
        """
        Test creating language edit keyboard.
        Check that:
        1. Function returns InlineKeyboardMarkup
        2. Keyboard contains all expected edit options
        """
        # Arrange
        language_id = "test_lang"
        
        # Act
        keyboard = get_edit_language_keyboard(language_id)
        
        # Assert
        assert isinstance(keyboard, InlineKeyboardMarkup), "Should return InlineKeyboardMarkup"
        
        # Get all buttons
        all_buttons = []
        for row in keyboard.inline_keyboard:
            all_buttons.extend(row)
        
        # Check count (6 buttons)
        assert len(all_buttons) == 6, "Should have 6 buttons"
        
        # Check callback data
        callback_data = [button.callback_data for button in all_buttons]
        assert f"edit_name_ru_{language_id}" in callback_data
        assert f"edit_name_foreign_{language_id}" in callback_data
        assert f"upload_to_lang_{language_id}" in callback_data
        assert f"search_word_by_number_{language_id}" in callback_data
        assert f"delete_language_{language_id}" in callback_data
        assert "back_to_languages" in callback_data
    
    def test_get_back_to_languages_keyboard(self):
        """
        Test creating back to languages keyboard.
        Check that:
        1. Function returns InlineKeyboardMarkup
        2. Keyboard contains back button with correct callback
        """
        # Act
        keyboard = get_back_to_languages_keyboard()
        
        # Assert
        assert isinstance(keyboard, InlineKeyboardMarkup), "Should return InlineKeyboardMarkup"
        
        # Get all buttons
        all_buttons = []
        for row in keyboard.inline_keyboard:
            all_buttons.extend(row)
        
        # Check count
        assert len(all_buttons) == 1, "Should have 1 button"
        
        # Check text and callback
        assert all_buttons[0].text == "⬅️ Назад к списку языков"
        assert all_buttons[0].callback_data == "back_to_languages"
    
    def test_get_back_to_admin_keyboard(self):
        """
        Test creating back to admin keyboard.
        Check that:
        1. Function returns InlineKeyboardMarkup
        2. Keyboard contains back button with correct callback
        """
        # Act
        keyboard = get_back_to_admin_keyboard()
        
        # Assert
        assert isinstance(keyboard, InlineKeyboardMarkup), "Should return InlineKeyboardMarkup"
        
        # Get all buttons
        all_buttons = []
        for row in keyboard.inline_keyboard:
            all_buttons.extend(row)
        
        # Check count
        assert len(all_buttons) == 1, "Should have 1 button"
        
        # Check text and callback
        assert all_buttons[0].text == "⬅️ Назад к меню администратора"
        assert all_buttons[0].callback_data == "back_to_admin"
    
    def test_get_yes_no_keyboard(self):
        """
        Test creating yes/no confirmation keyboard.
        Check that:
        1. Function returns InlineKeyboardMarkup
        2. Keyboard contains yes and no buttons with correct callbacks
        """
        # Arrange
        action = "delete_language"
        entity_id = "lang123"
        
        # Act
        keyboard = get_yes_no_keyboard(action, entity_id)
        
        # Assert
        assert isinstance(keyboard, InlineKeyboardMarkup), "Should return InlineKeyboardMarkup"
        
        # Get all buttons
        all_buttons = []
        for row in keyboard.inline_keyboard:
            all_buttons.extend(row)
        
        # Check count
        assert len(all_buttons) == 2, "Should have 2 buttons"
        
        # Check texts
        button_texts = [button.text for button in all_buttons]
        assert "✅ Да" in button_texts
        assert "❌ Нет" in button_texts
        
        # Check callback data
        callback_data = [button.callback_data for button in all_buttons]
        assert f"confirm_{action}_{entity_id}" in callback_data
        assert f"cancel_{action}_{entity_id}" in callback_data
    
    def test_get_upload_columns_keyboard(self):
        """
        Test creating upload columns configuration keyboard.
        Check that:
        1. Function returns InlineKeyboardMarkup
        2. Keyboard contains template options and cancel button
        """
        # Arrange
        language_id = "lang123"
        
        # Act
        keyboard = get_upload_columns_keyboard(language_id)
        
        # Assert
        assert isinstance(keyboard, InlineKeyboardMarkup), "Should return InlineKeyboardMarkup"
        
        # Get all buttons
        all_buttons = []
        for row in keyboard.inline_keyboard:
            all_buttons.extend(row)
        
        # Check count
        assert len(all_buttons) == 5, "Should have 5 buttons"
        
        # Check callback data
        callback_data = [button.callback_data for button in all_buttons]
        assert f"column_template_1_{language_id}" in callback_data
        assert f"column_template_2_{language_id}" in callback_data
        assert f"column_template_3_{language_id}" in callback_data
        assert f"custom_columns_{language_id}" in callback_data
        assert f"cancel_upload_{language_id}" in callback_data
    
    def test_get_word_actions_keyboard(self):
        """
        Test creating word actions keyboard.
        Check that:
        1. Function returns InlineKeyboardMarkup
        2. Keyboard contains edit, search, and back buttons
        """
        # Arrange
        word_id = "word123"
        language_id = "lang123"
        
        # Act
        keyboard = get_word_actions_keyboard(word_id, language_id)
        
        # Assert
        assert isinstance(keyboard, InlineKeyboardMarkup), "Should return InlineKeyboardMarkup"
        
        # Get all buttons
        all_buttons = []
        for row in keyboard.inline_keyboard:
            all_buttons.extend(row)
        
        # Check count
        assert len(all_buttons) == 3, "Should have 3 buttons"
        
        # Check texts
        button_texts = [button.text for button in all_buttons]
        assert any("Редактировать" in text for text in button_texts), "Should have edit button"
        assert any("Найти другое слово" in text for text in button_texts), "Should have search button"
        assert any("Назад к языку" in text for text in button_texts), "Should have back button"
        
        # Check callback data
        callback_data = [button.callback_data for button in all_buttons]
        assert f"edit_word_{word_id}" in callback_data
        assert f"search_word_by_number_{language_id}" in callback_data
        assert f"edit_language_{language_id}" in callback_data
        