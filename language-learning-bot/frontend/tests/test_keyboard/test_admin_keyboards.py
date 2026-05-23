import pytest
from unittest.mock import patch, Mock
from aiogram.types import InlineKeyboardMarkup

from app.bot.keyboards.admin_keyboards import (
    get_admin_keyboard,
    get_languages_keyboard,
    get_edit_language_keyboard,
    get_word_actions_keyboard,
    get_users_keyboard,
    get_user_detail_keyboard
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
        
        # ИСПРАВЛЕНО: Теперь должно быть 4 кнопки (добавлено управление пользователями)
        assert len(all_buttons) == 6, "Should have 6 buttons"
        
        # Check texts
        button_texts = [button.text for button in all_buttons]
        assert any("Управление языками" in text for text in button_texts), "Should have languages management button"
        assert any("Управление пользователями" in text for text in button_texts), "Should have users management button"
        assert any("Статистика" in text for text in button_texts), "Should have statistics button"
        assert any("Выйти из режима администратора" in text for text in button_texts), "Should have exit button"
        
        # Check callback data
        callback_data = [button.callback_data for button in all_buttons]
        assert "admin_languages" in callback_data
        assert "admin_users" in callback_data
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
        assert len(all_buttons) == 7, "Should have 7 buttons"
        
        # Check callback data
        callback_data = [button.callback_data for button in all_buttons]
        assert f"edit_name_ru_{language_id}" in callback_data
        assert f"edit_name_foreign_{language_id}" in callback_data
        assert f"upload_to_lang_{language_id}" in callback_data
        assert f"search_word_by_number_{language_id}" in callback_data
        assert f"delete_language_{language_id}" in callback_data
        assert "back_to_languages" in callback_data
    
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
        assert len(all_buttons) == 4, "Should have 4 buttons"
        
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

    def test_get_users_keyboard(self):
        """
        Test creating users list keyboard.
        Check that:
        1. Function returns InlineKeyboardMarkup
        2. Keyboard contains buttons for each user plus navigation
        """
        # Arrange
        users = [
            {"_id": "user1", "first_name": "John", "username": "john_doe", "is_admin": False},
            {"id": "user2", "first_name": "Jane", "username": "jane_doe", "is_admin": True},
            {"_id": "user3", "first_name": "Bob", "is_admin": False}  # No username
        ]
        
        # Act
        keyboard = get_users_keyboard(users, page=0, per_page=10)
        
        # Assert
        assert isinstance(keyboard, InlineKeyboardMarkup), "Should return InlineKeyboardMarkup"
        
        # Get all buttons 
        all_buttons = []
        for row in keyboard.inline_keyboard:
            all_buttons.extend(row)
        
        # Check count (3 users + back button = 4 buttons, no pagination needed for 3 users)
        assert len(all_buttons) == 4, "Should have 4 buttons"
        
        # Check texts
        button_texts = [button.text for button in all_buttons]
        assert any("John (@john_doe)" in text for text in button_texts), "Should have button for John"
        assert any("Jane (@jane_doe) 👑" in text for text in button_texts), "Should have button for Jane with admin crown"
        assert any("Bob" in text for text in button_texts), "Should have button for Bob"
        assert any("Назад в админку" in text for text in button_texts), "Should have back button"
        
        # Check callback data
        callback_data = [button.callback_data for button in all_buttons]
        assert "view_user_user1" in callback_data
        assert "view_user_user2" in callback_data
        assert "view_user_user3" in callback_data
        assert "back_to_admin" in callback_data

    def test_get_users_keyboard_with_pagination(self):
        """
        Test creating users keyboard with pagination.
        """
        # Arrange - создаем много пользователей для проверки пагинации
        users = []
        for i in range(25):  # 25 пользователей для проверки пагинации
            users.append({
                "_id": f"user{i}",
                "first_name": f"User{i}",
                "username": f"user{i}",
                "is_admin": i % 5 == 0  # Каждый 5-й - админ
            })
        
        # Act - первая страница
        keyboard_page_0 = get_users_keyboard(users, page=0, per_page=10)
        
        # Assert
        all_buttons_page_0 = []
        for row in keyboard_page_0.inline_keyboard:
            all_buttons_page_0.extend(row)
        
        # На первой странице: 10 пользователей + кнопка "След." + информация о странице + кнопка "Назад" = 13 кнопок
        assert len(all_buttons_page_0) == 13, "Page 0 should have 13 buttons"
        
        # Проверяем наличие кнопки "След."
        button_texts = [button.text for button in all_buttons_page_0]
        assert any("След." in text for text in button_texts), "Should have next page button"
        assert any("Стр. 1/3" in text for text in button_texts), "Should have page info"

    def test_get_user_detail_keyboard(self):
        """
        Test creating user detail keyboard.
        Check that:
        1. Function returns InlineKeyboardMarkup
        2. Keyboard contains expected action buttons
        """
        # Arrange
        user_id = "user123"
        
        # Act
        keyboard = get_user_detail_keyboard(user_id)
        
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
        assert any("Подробная статистика" in text for text in button_texts), "Should have stats button"
        assert any("Назад к списку" in text for text in button_texts), "Should have back button"
        
        # Check callback data
        callback_data = [button.callback_data for button in all_buttons]
        assert f"user_stats_{user_id}" in callback_data
        assert "admin_users" in callback_data
        