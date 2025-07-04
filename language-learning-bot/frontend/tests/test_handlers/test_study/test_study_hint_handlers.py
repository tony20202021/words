"""
Unit tests for study_hint_handlers.py module of the Language Learning Bot.

тесты в этом модуле должны быть простыми
просто вызов тестируемой функции
и минимальная проверка логики, которую она реализует
например проверка, что действительно были вызваны ключевые функции, существенные для ее реализации
все внешние вызовы должны быть заменены на моки

"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from aiogram.types import Message, User, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.bot.states.centralized_states import HintStates, StudyStates

# Импортируем функции обработчиков из правильных подмодулей
from app.bot.handlers.study.hint.create_handlers import process_hint_create
from app.bot.handlers.study.hint.edit_handlers import process_hint_edit
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
    
    def test_hint_router_exists(self):
        """Test that the hint_router exists."""
        # Just check that the router exists
        assert hasattr(study_hint_handlers, 'hint_router')
        
        # Check that all expected sub-routers are included
        assert hasattr(study_hint_handlers, 'create_router')
        assert hasattr(study_hint_handlers, 'edit_router')
        assert hasattr(study_hint_handlers, 'toggle_router')
        assert hasattr(study_hint_handlers, 'common_router')
        assert hasattr(study_hint_handlers, 'unknown_router')

    @pytest.mark.asyncio
    async def test_process_hint_text(self, setup_mocks):
        """Test the process_hint_text handler for creating a hint."""
        message, state, api_client, _, _, state_data = setup_mocks
        
        # Сбрасываем моки
        state.set_state.reset_mock()
        message.answer.reset_mock()
        
        # Устанавливаем текст сообщения
        message.text = "домик на холме"
        # Добавляем атрибут voice со значением None
        message.voice = None
        
        # Устанавливаем state_data для hint creation
        hint_state_data = {
            "hint_key": "hint_phoneticassociation",
            "hint_name": "Ассоциация",
            "hint_word_id": "word123",
            "db_user_id": "user123",
            "current_word": state_data["current_word"]
        }
        state.get_data.return_value = hint_state_data
        
        with patch('app.bot.handlers.study.hint.common.UserWordState.from_state') as mock_user_state, \
            patch('app.bot.handlers.study.hint.common.HintState.from_state') as mock_hint_state, \
            patch('app.bot.handlers.study.hint.common.ensure_user_word_data', 
                AsyncMock(return_value=(True, {"hint_phoneticassociation": "домик на холме"}))), \
            patch('app.bot.handlers.study.hint.common.process_hint_input', 
                AsyncMock(return_value="домик на холме")) as mock_voice_utils, \
            patch('app.bot.handlers.study.hint.common.logger'):
            
            # Настройка mock_user_state
            user_state_obj = MagicMock()
            user_state_obj.is_valid.return_value = True
            user_state_obj.user_id = "user123"
            user_state_obj.word_id = "word123" 
            user_state_obj.word_data = state_data["current_word"]
            user_state_obj.get_flag = MagicMock(return_value=[])
            user_state_obj.set_flag = MagicMock()
            user_state_obj.save_to_state = AsyncMock()
            mock_user_state.return_value = user_state_obj
            
            # Настройка mock_hint_state
            hint_state_obj = MagicMock()
            hint_state_obj.is_valid.return_value = True
            hint_state_obj.hint_key = "hint_phoneticassociation"
            hint_state_obj.hint_name = "Ассоциация"
            hint_state_obj.hint_word_id = "word123"
            hint_state_obj.get_hint_type = MagicMock(return_value="association")
            mock_hint_state.return_value = hint_state_obj
            
            # Вызываем тестируемую функцию
            from app.bot.handlers.study.hint.common import process_hint_text
            await process_hint_text(message, state)
            
            # ОСНОВНЫЕ ПРОВЕРКИ:
            mock_voice_utils.assert_called_once_with(message, "Ассоциация")
            mock_user_state.assert_called_once_with(state)
            mock_hint_state.assert_called_once_with(state)
            user_state_obj.is_valid.assert_called()
            hint_state_obj.is_valid.assert_called()
                                                    
    @pytest.mark.asyncio
    async def test_process_hint_edit(self, setup_mocks):
        """Test the process_hint_edit handler."""
        _, state, api_client, callback, _, state_data = setup_mocks
        
        state_data = {
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
        
        # Устанавливаем callback.data
        callback.data = "hint_edit_association_word123"
        
        # Создаем моки с возможностью отслеживания вызовов
        get_hint_key_mock = MagicMock(return_value="hint_phoneticassociation")
        get_hint_name_mock = MagicMock(return_value="Ассоциация")
        get_hint_text_mock = AsyncMock(return_value="существующая подсказка")
        
        # Для функций, которые вызываются с await, используем AsyncMock
        validate_state_data_mock = AsyncMock(return_value=(True, state_data))
        
        # Создаем мок для HintState
        hint_instance = MagicMock()
        hint_instance.save_to_state = AsyncMock()
        MockHintState = MagicMock(return_value=hint_instance)

        # Используем patch.object для всех импортированных функций и классов
        with patch('app.bot.handlers.study.hint.edit_handlers.get_hint_key', get_hint_key_mock), \
            patch('app.bot.handlers.study.hint.edit_handlers.get_hint_name', get_hint_name_mock), \
            patch('app.bot.handlers.study.hint.edit_handlers.get_hint_text', get_hint_text_mock), \
            patch('app.bot.handlers.study.hint.edit_handlers.CallbackParser.parse_hint_action', MagicMock(return_value=("edit", "association", "word123"))), \
            patch('app.bot.handlers.study.hint.edit_handlers.HintState', MockHintState), \
            patch('app.bot.handlers.study.hint.edit_handlers.validate_state_data', validate_state_data_mock), \
            patch('app.bot.handlers.study.hint.edit_handlers.logger'):
            
            # Вызываем тестируемую функцию
            await process_hint_edit(callback, state)
            
            # Проверяем, что validate_state_data был вызван с правильными аргументами
            validate_state_data_mock.assert_called_once()
            
            # Проверяем, что get_hint_key и get_hint_name были вызваны с правильными аргументами
            get_hint_key_mock.assert_called_once_with("association")
            get_hint_name_mock.assert_called_once_with("association")
            
            # Проверяем, что HintState был создан с правильными параметрами
            MockHintState.assert_called_once_with(
                hint_key="hint_phoneticassociation",
                hint_name="Ассоциация",
                hint_word_id="word123",
                current_hint_text="существующая подсказка"
            )
            
            # Проверяем, что save_to_state был вызван
            assert hint_instance.save_to_state.called
            
            # Проверяем, что state.set_state был вызван с правильным состоянием
            assert state.set_state.called
            assert state.set_state.call_args.args[0] == HintStates.editing
            
            # Проверяем, что message.answer был вызван
            assert callback.message.answer.called
            
            # Проверяем, что callback.answer был вызван
            assert callback.answer.called

    @pytest.mark.asyncio
    async def test_cmd_cancel_hint(self, setup_mocks):
        """Test the cmd_cancel_hint handler."""
        message, state, _, _, _, _ = setup_mocks
        
        # Устанавливаем состояние
        state.get_state = AsyncMock(return_value="HintStates:creating")
        
        # Устанавливаем данные состояния
        state_data = {
            "current_study_index": 0,
            "current_word": {
                "id": "word123",
                "word_foreign": "house",
                "translation": "дом",
                "transcription": "haʊs",
                "language_id": "lang123",
                "user_word_data": {
                    "check_interval": 1,
                    "next_check_date": "2025-05-15"
                }
            }
        }
        state.get_data.return_value = state_data
        
        user_word_state_mock = MagicMock()
        user_word_state_mock.is_valid = MagicMock(return_value = True)
        user_word_state_mock.get_flag.return_value = []
        user_word_state_mock.set_flag = AsyncMock()
        user_word_state_mock.save_to_state = AsyncMock()
        
        user_word_state_from_state_mock = AsyncMock(return_value=user_word_state_mock)
        
        
        show_study_word_mock = AsyncMock()
        
        with \
            patch('app.utils.state_models.UserWordState.from_state', user_word_state_from_state_mock), \
            patch('app.bot.handlers.study.hint.common.show_study_word', show_study_word_mock), \
            patch('app.bot.handlers.study.hint.common.logger'):
            
            # Вызываем обработчик
            from app.bot.handlers.study.hint.common import cmd_cancel_hint
            await cmd_cancel_hint(message, state)
        
        assert state.get_state.called
        assert state.set_state.called
        user_word_state_from_state_mock.assert_called_once()
        user_word_state_mock.get_flag.assert_called_once()
        assert show_study_word_mock.called
        assert message.answer.called
                    
    @pytest.mark.asyncio
    async def test_process_hint_create(self, setup_mocks):
        """Test the process_hint_create handler."""
        _, state, _, callback, _, _ = setup_mocks
        
        # Сбрасываем моки
        callback.message.answer.reset_mock()
        state.set_state.reset_mock()
        
        # Устанавливаем callback.data
        callback.data = "hint_create_association_word123"
        
        # Устанавливаем state_data
        state_data = {
            "current_word_id": "word123",
            "db_user_id": "user123",
            "word_data": {
                "id": "word123",
                "word_foreign": "house",
                "translation": "дом",
                "transcription": "haʊs",
                "language_id": "lang123",
                "user_word_data": {
                    "check_interval": 1,
                    "next_check_date": "2025-05-15"
                }
            }
        }
        state.get_data.return_value = state_data
        
        # Импортируем модуль, в котором находится тестируемая функция
        import app.bot.handlers.study.hint.create_handlers as create_handlers_module
        
        # Создаем моки для всех зависимостей
        validate_state_data_mock = AsyncMock(return_value=(True, state_data))
        get_hint_key_mock = MagicMock(return_value="hint_phoneticassociation")
        get_hint_name_mock = MagicMock(return_value="Ассоциация")
        
        # Создаем мок для HintState
        hint_state_mock = MagicMock()
        hint_state_mock.save_to_state = AsyncMock()
        HintState_mock = MagicMock(return_value=hint_state_mock)
        
        # Используем patch.object для патчирования всех зависимостей
        with patch.object(create_handlers_module, 'validate_state_data', validate_state_data_mock), \
            patch.object(create_handlers_module, 'get_hint_key', get_hint_key_mock), \
            patch.object(create_handlers_module, 'get_hint_name', get_hint_name_mock), \
            patch.object(create_handlers_module, 'HintState', HintState_mock), \
            patch.object(create_handlers_module, 'logger'):
            
            # Вызываем тестируемую функцию
            await process_hint_create(callback, state)
            
            # Проверяем, что validate_state_data был вызван с правильными аргументами
            validate_state_data_mock.assert_called()
            
            # Проверяем, что get_hint_key и get_hint_name были вызваны с правильными аргументами
            get_hint_key_mock.assert_called_once_with("association")
            get_hint_name_mock.assert_called_once_with("association")
            
            # Проверяем, что HintState был создан с правильными параметрами
            HintState_mock.assert_called_once_with(
                hint_key="hint_phoneticassociation",
                hint_name="Ассоциация",
                hint_word_id="word123"
            )
            
            # Проверяем, что state.set_state был вызван с правильным состоянием
            assert state.set_state.called
            assert state.set_state.call_args.args[0] == HintStates.creating
            
            # Проверяем, что message.answer был вызван
            assert callback.message.answer.called
            
            # Проверяем, что callback.answer был вызван
            assert callback.answer.called
