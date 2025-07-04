"""
тесты в этом модуле должны быть простыми
просто вызов тестируемой функции
и минимальная проверка логики, которую она реализует
например проверка, что действительно были вызваны ключевые функции, существенные для ее реализации
все внешние вызовы должны быть заменены на моки

"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from aiogram import Dispatcher
from aiogram.types import Message, User, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.dispatcher.event.bases import SkipHandler
from app.bot.states.centralized_states import HintStates, StudyStates

# Импортируем функции обработчиков из правильных подмодулей
from app.bot.handlers.study.hint.create_handlers import process_hint_create, process_hint_text
from app.bot.handlers.study.hint.edit_handlers import process_hint_edit, process_hint_edit_text
from app.bot.handlers.study.hint.common import cmd_cancel_hint
from app.bot.handlers.study.hint.toggle_handlers import process_hint_toggle
import app.bot.handlers.study.study_hint_handlers as study_hint_handlers


class TestStudyHintHandlers:
    """Tests for the study hint handlers."""

    @pytest.fixture
    def setup_mocks(self):
        """Set up common mocks for tests."""
        # Создаем state_data с реальными значениями для всех используемых полей
        state_data = {
            "current_word_id": "word123",
            "db_user_id": "user123",
            "current_word": {
                "id": "word123",
                "word_foreign": "house",
                "translation": "дом",
                "transcription": "haʊs",
                "language_id": "lang123",
                "user_word_data": {
                    "hint_phoneticsound": "х-ауз",
                    "hint_phoneticassociation": "существующая подсказка",
                    "check_interval": 1,
                    "next_check_date": "2025-05-15"
                }
            },
            "current_language": {
                "id": "lang123",
                "name_ru": "Английский",
                "name_foreign": "English"
            }
        }
        
        # Mock message
        message = MagicMock(spec=Message)
        message.answer = AsyncMock()
        message.edit_text = AsyncMock()
        message.from_user = MagicMock(spec=User)
        message.from_user.id = 12345
        message.from_user.username = "test_user"
        message.from_user.first_name = "Test"
        message.from_user.last_name = "User"
        message.from_user.full_name = "Test User"
        
        # Mock state
        state = MagicMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value=state_data)
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()
        state.get_state = AsyncMock(return_value=None)
        state.clear = AsyncMock()
        
        # Mock API client
        api_client = AsyncMock()
        api_client.get_user_by_telegram_id = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [],
            "error": None
        })
        api_client.create_user = AsyncMock(return_value={
            "success": True,
            "status": 201,
            "result": {"id": "user123"},
            "error": None
        })
        api_client.get_word = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {
                "id": "word123",
                "word_foreign": "house",
                "translation": "дом",
                "transcription": "haʊs",
                "language_id": "lang123",
                "user_word_data": {
                    "hint_phoneticassociation": "существующая подсказка",
                    "check_interval": 1,
                    "next_check_date": "2025-05-15"
                }
            },
            "error": None
        })
        api_client.get_language = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {
                "id": "lang123",
                "name_ru": "Английский",
                "name_foreign": "English"
            },
            "error": None
        })
        api_client.get_user_word_data = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {
                "hint_phoneticsound": "х-ауз",
                "score": 0,
                "check_interval": 1,
                "next_check_date": "2025-05-15"
            },
            "error": None
        })
        api_client.update_user_word_data = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {
                "hint_phoneticsound": "х-ауз",
                "score": 0,
                "check_interval": 1,
                "next_check_date": "2025-05-15"
            },
            "error": None
        })
        api_client.create_user_word_data = AsyncMock(return_value={
            "success": True,
            "status": 201,
            "result": {
                "hint_phoneticsound": "х-ауз",
                "score": 0,
                "check_interval": 1,
                "next_check_date": "2025-05-15"
            },
            "error": None
        })
        
        # Mock callback
        callback = MagicMock(spec=CallbackQuery)
        callback.answer = AsyncMock()
        callback.message = message
        callback.message.edit_text = AsyncMock()
        callback.from_user = message.from_user
        callback.data = "hint_view_phonetic_word123"
        callback.bot = message.bot = MagicMock()
        callback.bot.api_client = api_client
        
        # Mock voice message 
        voice_message = MagicMock(spec=Message)
        voice_message.answer = AsyncMock()
        voice_message.from_user = message.from_user
        voice_message.text = None
        voice_message.voice = MagicMock()
        voice_message.voice.file_id = "voice_file_id"
        voice_message.voice.duration = 5
        voice_message.bot = MagicMock()
        voice_message.bot.get_file = AsyncMock()
        voice_message.bot.api_client = api_client
        
        return message, state, api_client, callback, voice_message, state_data

    @pytest.mark.asyncio
    async def test_process_hint_toggle(self, setup_mocks):
        """Test the process_hint_toggle handler."""
        _, state, api_client, callback, _, state_data = setup_mocks
        
        # Настраиваем моки
        callback.message.edit_text.reset_mock()
        callback.answer.reset_mock()
        
        # Устанавливаем callback.data для toggle_hint
        callback.data = "hint_toggle_association_word123"
        
        # Устанавливаем state_data
        state.get_data.return_value = {
            "word_data": {
                "id": "word123",
                "word_foreign": "house",
                "translation": "дом",
                "transcription": "haʊs",
                "language_id": "lang123",
                "user_word_data": {
                    "hint_phoneticassociation": "существующая подсказка"
                }
            },
            "db_user_id": "user123"
        }
        
        # Импортируем модуль, в котором находится тестируемая функция
        import app.bot.handlers.study.hint.toggle_handlers as toggle_handlers_module
        
        # Создаем моки для необходимых функций
        validate_state_data_mock = AsyncMock(return_value=(True, state.get_data.return_value))
        get_hint_key_mock = MagicMock(return_value="hint_phoneticassociation")
        get_hint_name_mock = MagicMock(return_value="Ассоциация")
        get_hint_icon_mock = MagicMock(return_value="🔤")
        get_hint_text_mock = AsyncMock(return_value="существующая подсказка")
        update_word_score_mock = AsyncMock(return_value=(True, {"score": 0}))
        
        # Создаем мок для UserWordState
        user_word_state_mock = MagicMock()
        user_word_state_mock.is_valid.return_value = True
        user_word_state_mock.get_flag.return_value = []  # Изначально нет использованных подсказок
        user_word_state_mock.set_flag = MagicMock()
        user_word_state_mock.save_to_state = AsyncMock()
        
        # Используем patch для патчирования всех зависимостей
        with patch('app.bot.handlers.study.hint.toggle_handlers.validate_state_data', validate_state_data_mock), \
            patch('app.bot.handlers.study.hint.toggle_handlers.get_hint_key', get_hint_key_mock), \
            patch('app.bot.handlers.study.hint.toggle_handlers.get_hint_name', get_hint_name_mock), \
            patch('app.bot.handlers.study.hint.toggle_handlers.get_hint_icon', get_hint_icon_mock), \
            patch('app.bot.handlers.study.hint.toggle_handlers.get_hint_text', get_hint_text_mock), \
            patch('app.bot.handlers.study.hint.toggle_handlers.update_word_score', update_word_score_mock), \
            patch('app.utils.state_models.UserWordState.from_state', AsyncMock(return_value=user_word_state_mock)), \
            patch('app.bot.handlers.study.hint.toggle_handlers.CallbackParser.parse_hint_action', MagicMock(return_value=("toggle", "association", "word123"))), \
            patch('app.bot.handlers.study.hint.toggle_handlers.show_study_word', AsyncMock()), \
            patch('app.bot.handlers.study.hint.toggle_handlers.logger'):
            
            # Настраиваем API ответ для get_language
            api_client.get_language.return_value = {
                "success": True,
                "status": 200,
                "result": {
                    "id": "lang123",
                    "name_ru": "Английский",
                    "name_foreign": "English"
                },
                "error": None
            }
            
            # Вызываем тестируемую функцию
            await process_hint_toggle(callback, state)
            
            # Проверяем, что validate_state_data был вызван с правильными параметрами
            validate_state_data_mock.assert_called()
            
            # Проверяем, что get_hint_key и get_hint_name были вызваны с правильным типом подсказки
            get_hint_key_mock.assert_called_once_with("association")
            get_hint_name_mock.assert_called_once_with("association")
            
            # Проверяем, что get_hint_text был вызван с правильными параметрами
            get_hint_text_mock.assert_called_once()
            
            # Проверяем, что установлена оценка 0 (используется подсказка)
            update_word_score_mock.assert_called_once()
            
            # Проверяем, что подсказка добавлена в список использованных
            user_word_state_mock.set_flag.assert_any_call('used_hints', ['association'])
            
            # Проверяем, что состояние было сохранено
            user_word_state_mock.save_to_state.assert_called_once_with(state)
            
