"""
Tests for hint_constants module.
"""

import pytest
from unittest.mock import MagicMock

from app.utils.hint_constants import (
    get_hint_key,
    get_hint_name,
    get_hint_icon,
    get_all_hint_types,
    format_hint_button,
    has_hint,
    HINT_TYPE_MAP,
    HINT_ICONS,
    HINT_ORDER
)

class TestGetHintKey:
    
    def test_get_hint_key_existing(self):
        # Setup
        hint_type = "meaning"
        
        # Execute
        result = get_hint_key(hint_type)
        
        # Verify
        assert result == "hint_meaning"  # В соответствии с HINT_TYPE_MAP
        assert result == HINT_TYPE_MAP[hint_type][0]  # Проверка через константу
    
    def test_get_hint_key_nonexistent(self):
        # Setup
        hint_type = "nonexistent_type"
        
        # Execute
        result = get_hint_key(hint_type)
        
        # Verify
        assert result is None


class TestGetHintName:
    
    def test_get_hint_name_existing(self):
        # Setup
        hint_type = "phoneticassociation"
        
        # Execute
        result = get_hint_name(hint_type)
        
        # Verify
        assert "Ассоциация для фонетики" in result  # В соответствии с HINT_TYPE_MAP
        assert result == HINT_TYPE_MAP[hint_type][1]  # Проверка через константу
    
    def test_get_hint_name_nonexistent(self):
        # Setup
        hint_type = "nonexistent_type"
        
        # Execute
        result = get_hint_name(hint_type)
        
        # Verify
        assert result is None


class TestGetHintIcon:
    
    def test_get_hint_icon_existing(self):
        # Setup
        hint_type = "writing"
        
        # Execute
        result = get_hint_icon(hint_type)
        
        # Verify
        assert result == "✍️"  # В соответствии с HINT_ICONS
        assert result == HINT_ICONS[hint_type]  # Проверка через константу
    
    def test_get_hint_icon_nonexistent(self):
        # Setup
        hint_type = "nonexistent_type"
        
        # Execute
        result = get_hint_icon(hint_type)
        
        # Verify
        assert result == "ℹ️"  # Дефолтная иконка


class TestGetAllHintTypes:
    
    def test_get_all_hint_types(self):
        # Execute
        result = get_all_hint_types()
        
        # Verify
        assert result == HINT_ORDER  # Порядок типов подсказок
        assert "meaning" in result
        assert "phoneticassociation" in result
        assert "phoneticsound" in result
        assert "writing" in result


class TestFormatHintButton:
    
    def test_format_hint_button_no_hint(self):
        # Setup
        hint_type = "meaning"
        has_hint = False
        is_active = False
        
        # Execute
        result = format_hint_button(hint_type, has_hint, is_active)
        
        # Verify
        assert get_hint_icon(hint_type) in result  # Иконка присутствует
    
    def test_format_hint_button_with_hint_active(self):
        # Setup
        hint_type = "phoneticsound"
        has_hint = True
        is_active = True
        
        # Execute
        result = format_hint_button(hint_type, has_hint, is_active)
        
        # Verify
        assert get_hint_icon(hint_type) in result  # Иконка присутствует
    
    def test_format_hint_button_with_hint_inactive(self):
        # Setup
        hint_type = "writing"
        has_hint = True
        is_active = False
        
        # Execute
        result = format_hint_button(hint_type, has_hint, is_active)
        
        # Verify
        assert get_hint_icon(hint_type) in result  # Иконка присутствует


class TestHasHint:
    
    def test_has_hint_in_word_data(self):
        # Setup
        hint_type = "meaning"
        hint_key = get_hint_key(hint_type)
        word_data = {
            "word_foreign": "book",
            "translation": "книга",
            hint_key: "подсказка для значения"
        }
        
        # Execute
        result = has_hint(word_data, hint_type)
        
        # Verify
        assert result is True
    
    def test_has_hint_in_user_word_data(self):
        # Setup
        hint_type = "phoneticassociation"
        hint_key = get_hint_key(hint_type)
        word_data = {
            "word_foreign": "book",
            "translation": "книга",
            "user_word_data": {
                hint_key: "подсказка для фонетики"
            }
        }
        
        # Execute
        result = has_hint(word_data, hint_type)
        
        # Verify
        assert result is True
    
    def test_has_hint_not_present(self):
        # Setup
        hint_type = "writing"
        word_data = {
            "word_foreign": "book",
            "translation": "книга",
            # Нет подсказки для данного типа
        }
        
        # Execute
        result = has_hint(word_data, hint_type)
        
        # Verify
        assert result is False
    
    def test_has_hint_empty_value(self):
        # Setup
        hint_type = "writing"
        hint_key = get_hint_key(hint_type)
        word_data = {
            "word_foreign": "book",
            "translation": "книга",
            hint_key: ""  # Пустая подсказка
        }
        
        # Execute
        result = has_hint(word_data, hint_type)
        
        # Verify
        assert result is False  # Пустая подсказка считается отсутствующей
    
    def test_has_hint_invalid_type(self):
        # Setup
        hint_type = "nonexistent_type"  # Несуществующий тип подсказки
        word_data = {
            "word_foreign": "book",
            "translation": "книга"
        }
        
        # Execute
        result = has_hint(word_data, hint_type)
        
        # Verify
        assert result is False  # Несуществующий тип подсказки

