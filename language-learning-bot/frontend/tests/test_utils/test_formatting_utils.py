"""
Tests for formatting_utils module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.utils.formatting_utils import (
    format_date,
    format_date_standard,
    format_settings_text,
    format_study_word_message,
    format_used_hints
)

class TestFormatDate:
    
    def test_format_date_success(self):
        # Setup
        date_str = "2023-05-15"
        
        # Патчим locale.setlocale для имитации установки локали
        with patch('locale.setlocale'):
            # Execute
            result = format_date(date_str)
            
            # Verify
            assert "15" in result  # День должен быть в результате
            assert "2023" in result  # Год должен быть в результате
            
    def test_format_date_none(self):
        # Проверка на пустое значение
        assert format_date(None) == 'N/A'
        assert format_date('N/A') == 'N/A'


class TestFormatDateStandard:
    
    def test_format_date_standard_same_as_format_date(self):
        # Setup
        date_str = "2023-05-15"
        
        # Патчим locale.setlocale для имитации установки локали
        with patch('locale.setlocale'):
            # Execute и Verify
            assert format_date_standard(date_str) == format_date(date_str)


class TestFormatSettingsText:
    
    def test_format_settings_text_success(self):
        # Setup
        start_word = 5
        skip_marked = True
        use_check_date = False
        show_hints = True
        show_debug = False
        prefix = "Настройки:\n"
        suffix = "\nКонец настроек"
        
        # Execute
        result = format_settings_text(
            start_word, skip_marked, use_check_date, show_hints, show_debug, 
            prefix=prefix, suffix=suffix
        )
        
        # Verify - проверяем наличие ключевых элементов
        assert prefix in result
        assert suffix in result
        assert f"Начальное слово: <b>{start_word}</b>" in result
        assert "Пропускать ❌" in result  # skip_marked = True
        assert "Не учитывать ❌" in result  # use_check_date = False
        assert "Придумывать ✅" in result  # show_hints = True
        assert "Скрывать ❌" in result  # show_debug = False


class TestFormatStudyWordMessage:
    
    def test_format_study_word_message_without_showing_word(self):
        # Setup
        language_name_ru = "Английский"
        language_name_foreign = "English"
        word_number = 10
        translation = "Книга"
        is_skipped = False
        score = 0
        check_interval = 0
        next_check_date = None
        show_word = False
        word_foreign = "Book"
        transcription = "bʊk"
        
        # Execute
        result = format_study_word_message(
            language_name_ru, language_name_foreign, word_number, translation,
            is_skipped, score, check_interval, next_check_date,
            show_word, word_foreign, transcription
        )
        
        # Verify
        assert language_name_ru in result
        assert language_name_foreign in result
        assert str(word_number) in result
        assert translation in result
        assert word_foreign not in result  # Слово не должно показываться
        assert transcription not in result  # Транскрипция не должна показываться
    
    def test_format_study_word_message_with_showing_word(self):
        # Setup
        language_name_ru = "Английский"
        language_name_foreign = "English"
        word_number = 10
        translation = "Книга"
        is_skipped = False
        score = 0
        check_interval = 0
        next_check_date = None
        show_word = True
        word_foreign = "Book"
        transcription = "bʊk"
        
        # Execute
        result = format_study_word_message(
            language_name_ru, language_name_foreign, word_number, translation,
            is_skipped, score, check_interval, next_check_date,
            show_word, word_foreign, transcription
        )
        
        # Verify
        assert language_name_ru in result
        assert language_name_foreign in result
        assert str(word_number) in result
        assert translation in result
        assert word_foreign in result  # Слово должно показываться
        assert transcription in result  # Транскрипция должна показываться


class TestFormatUsedHints:
    
    @pytest.mark.asyncio
    async def test_format_used_hints_success(self):
        # Setup
        bot = AsyncMock()
        user_id = "user123"
        word_id = "word123"
        current_word = {
            "_id": "word123",
            "word_foreign": "Book",
            "translation": "Книга"
        }
        used_hints = ["meaning", "phoneticsound"]
        
        # Патчим функцию get_hint_text и hint_constants
        with patch('app.utils.formatting_utils.get_hint_text', side_effect=[
            "Подсказка для значения",
            "Подсказка для фонетики"
        ]), \
        patch('app.utils.formatting_utils.get_hint_key', side_effect=[
            "hint_meaning", "hint_phoneticsound"
        ]), \
        patch('app.utils.formatting_utils.get_hint_name', side_effect=[
            "Ассоциация для значения на русском", "Фонетическое звучание"
        ]), \
        patch('app.utils.formatting_utils.get_hint_icon', side_effect=[
            "🧠", "🎵"
        ]):
            
            # Execute
            result = await format_used_hints(
                bot, user_id, word_id, current_word, used_hints, include_header=True
            )
            
            # Verify
            assert "Использованные подсказки" in result
            assert "Подсказка для значения" in result
            assert "Подсказка для фонетики" in result
            assert "🧠" in result  # Иконка для meaning
            assert "🎵" in result  # Иконка для phoneticsound