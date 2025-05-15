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
from aiogram import Dispatcher
from aiogram.types import Message, User, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.dispatcher.event.bases import SkipHandler
from app.bot.handlers.study.study_states import HintStates, StudyStates

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
                    "hint_syllables": "х-ауз",
                    "hint_association": "существующая подсказка",
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
                    "hint_association": "существующая подсказка",
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
                "hint_syllables": "х-ауз",
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
                "hint_syllables": "х-ауз",
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
                "hint_syllables": "х-ауз",
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
        assert hasattr(study_hint_handlers, 'view_router')
        assert hasattr(study_hint_handlers, 'edit_router')
        assert hasattr(study_hint_handlers, 'toggle_router')
        assert hasattr(study_hint_handlers, 'cancel_router')

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
            "hint_key": "hint_association",
            "hint_name": "Ассоциация",
            "hint_word_id": "word123",
            "db_user_id": "user123",
            "current_word": state_data["current_word"]
        }
        state.get_data.return_value = hint_state_data
        
        # Создаем мок для show_study_word
        show_study_word_mock = AsyncMock()
        
        # Патчим функции с правильными путями импорта
        with patch('app.bot.handlers.study.hint.create_handlers.show_study_word', show_study_word_mock), \
            patch('app.utils.state_models.UserWordState.from_state') as mock_user_state, \
            patch('app.utils.state_models.HintState.from_state') as mock_hint_state, \
            patch('app.utils.word_data_utils.ensure_user_word_data', 
                AsyncMock(return_value=(True, {"hint_association": "домик на холме"}))):
            
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
            hint_state_obj.hint_key = "hint_association"
            hint_state_obj.hint_name = "Ассоциация"
            hint_state_obj.hint_word_id = "word123"
            hint_state_obj.get_hint_type = MagicMock(return_value="association")
            mock_hint_state.return_value = hint_state_obj
            
            # Вызываем тестируемую функцию
            await process_hint_text(message, state)
            
            # Проверяем что сообщение об успехе было отправлено
            assert message.answer.called
            assert any("успешно" in str(call).lower() for call in message.answer.call_args_list)
            
            # Проверяем что state был установлен в режим изучения
            assert state.set_state.called
            assert any(call.args[0] == StudyStates.studying for call in state.set_state.call_args_list)
            
            # Проверяем что show_study_word был вызван
            assert show_study_word_mock.called
                
    @pytest.mark.asyncio
    async def test_process_hint_edit(self, setup_mocks):
        """Test the process_hint_edit handler."""
        _, state, api_client, callback, _, state_data = setup_mocks
        
        # Настраиваем моки
        callback.message.answer.reset_mock()
        state.set_state.reset_mock()
        
        # Устанавливаем callback.data
        callback.data = "hint_edit_association_word123"
        
        # Импортируем модуль, в котором используются функции
        import app.bot.handlers.study.hint.edit_handlers as edit_handlers_module
        
        # Создаем моки с возможностью отслеживания вызовов
        get_hint_key_mock = MagicMock(return_value="hint_association")
        get_hint_name_mock = MagicMock(return_value="Ассоциация")
        get_hint_text_mock = AsyncMock(return_value="существующая подсказка")
        
        # Для функций, которые вызываются с await, используем AsyncMock
        validate_state_data_mock = AsyncMock(return_value=(True, state_data))
        
        # Создаем мок для HintState
        hint_instance = MagicMock()
        hint_instance.save_to_state = AsyncMock()
        MockHintState = MagicMock(return_value=hint_instance)
        
        # Используем patch.object для всех импортированных функций и классов
        with patch.object(edit_handlers_module, 'get_hint_key', get_hint_key_mock), \
            patch.object(edit_handlers_module, 'get_hint_name', get_hint_name_mock), \
            patch.object(edit_handlers_module, 'get_hint_text', get_hint_text_mock), \
            patch.object(edit_handlers_module, 'HintState', MockHintState), \
            patch.object(edit_handlers_module, 'validate_state_data', validate_state_data_mock), \
            patch.object(edit_handlers_module, 'get_api_client_from_bot', return_value=api_client):
            
            # Вызываем тестируемую функцию
            await process_hint_edit(callback, state)
            
            # Проверяем, что validate_state_data был вызван с правильными аргументами
            validate_state_data_mock.assert_called_once_with(
                state, 
                ["current_word", "db_user_id"], 
                callback,
                "Ошибка: недостаточно данных для редактирования подсказки"
            )
            
            # Проверяем, что get_hint_key и get_hint_name были вызваны с правильными аргументами
            get_hint_key_mock.assert_called_once_with("association")
            get_hint_name_mock.assert_called_once_with("association")
            
            # Проверяем, что HintState был создан с правильными параметрами
            MockHintState.assert_called_once_with(
                hint_key="hint_association",
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
    async def test_process_hint_view(self, setup_mocks):
        """Test the process_hint_view handler when hint exists."""
        _, state, api_client, callback, _, state_data = setup_mocks
        
        # Настраиваем edit_text как AsyncMock
        callback.message.edit_text = AsyncMock()
        
        # Устанавливаем callback.data
        callback.data = "hint_view_phonetic_word123"
        
        # Импортируем модуль, в котором используются функции
        import app.bot.handlers.study.hint.view_handlers as view_handlers_module
        
        # Создаем моки для всех зависимостей, которые действительно импортируются
        get_hint_text_mock = AsyncMock(return_value="х-ауз")
        update_word_score_mock = AsyncMock(return_value=(True, {}))
        get_show_hints_setting_mock = AsyncMock(return_value=True)
        format_study_word_message_mock = MagicMock(return_value="Слово: дом")
        create_word_keyboard_mock = MagicMock(return_value=MagicMock())
        validate_state_data_mock = AsyncMock(return_value=(True, state_data))
        get_all_hint_types_mock = MagicMock(return_value=["meaning", "association", "phonetic"])
        
        # Создаем мок для UserWordState
        user_state_obj = MagicMock()
        user_state_obj.is_valid.return_value = True
        user_state_obj.get_flag = MagicMock(return_value=[])
        user_state_obj.set_flag = MagicMock()
        user_state_obj.save_to_state = AsyncMock()
        MockUserWordState = AsyncMock(return_value=user_state_obj)
        
        # Используем patch.object для всех импортируемых функций
        with patch.object(view_handlers_module, 'get_hint_text', get_hint_text_mock), \
            patch.object(view_handlers_module, 'update_word_score', update_word_score_mock), \
            patch.object(view_handlers_module, 'get_show_hints_setting', get_show_hints_setting_mock), \
            patch.object(view_handlers_module, 'format_study_word_message', format_study_word_message_mock), \
            patch.object(view_handlers_module, 'create_word_keyboard', create_word_keyboard_mock), \
            patch.object(view_handlers_module, 'validate_state_data', validate_state_data_mock), \
            patch.object(view_handlers_module, 'get_api_client_from_bot', return_value=api_client), \
            patch.object(view_handlers_module, 'get_hint_key', return_value="hint_syllables"), \
            patch.object(view_handlers_module, 'get_hint_name', return_value="Фонетика"), \
            patch.object(view_handlers_module, 'get_hint_icon', return_value="🔤"), \
            patch.object(view_handlers_module, 'get_all_hint_types', get_all_hint_types_mock), \
            patch('app.utils.state_models.UserWordState.from_state', AsyncMock(return_value=user_state_obj)):
            
            # Вызываем функцию
            await process_hint_view(callback, state)
            
            # Проверяем, что get_all_hint_types был вызван
            assert get_all_hint_types_mock.called
            
            # Проверяем, что get_hint_text был вызван
            assert get_hint_text_mock.called
            
            # Проверяем, что update_word_score был вызван
            assert update_word_score_mock.called
            
            # Проверяем, что message.edit_text был вызван
            assert callback.message.edit_text.called
            
            # Проверяем, что callback.answer был вызван (чтобы убрать уведомление)
            assert callback.answer.called
            
            # Проверяем, что пользовательский state был сохранен
            assert user_state_obj.save_to_state.called

    @pytest.mark.asyncio
    async def test_cmd_cancel_hint(self, setup_mocks):
        """Test the cmd_cancel_hint handler."""
        message, state, _, _, _, _ = setup_mocks
        
        # Сбрасываем моки
        message.answer.reset_mock()
        state.set_state.reset_mock()
        
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
        
        # Создаем мок для show_study_word
        show_study_word_mock = AsyncMock()
        
        # Импортируем модуль, в котором вызывается функция
        import app.bot.handlers.study.hint.common as common_module
        
        # Используем patch.object для патчирования show_study_word в модуле common
        with patch.object(common_module, 'show_study_word', show_study_word_mock), \
            pytest.raises(SkipHandler):  # Ожидаем исключение SkipHandler
            
            # Вызываем обработчик
            await cmd_cancel_hint(message, state)
        
        # Проверяем, что state.set_state был вызван с правильным значением
        assert state.set_state.called
        assert any(call.args[0] == StudyStates.studying for call in state.set_state.call_args_list)
        
        # Проверяем, что message.answer был вызван с правильным сообщением
        assert message.answer.called
        assert any("отменено" in str(call).lower() for call in message.answer.call_args_list)
        
        # Проверяем, что show_study_word был вызван
        assert show_study_word_mock.called
            
    @pytest.mark.asyncio
    async def test_process_hint_create(self, setup_mocks):
        """Test the process_hint_create handler."""
        _, state, api_client, callback, _, _ = setup_mocks
        
        # Сбрасываем моки
        callback.message.answer.reset_mock()
        state.set_state.reset_mock()
        
        # Устанавливаем callback.data
        callback.data = "hint_create_association_word123"
        
        # Устанавливаем state_data
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
        get_hint_key_mock = MagicMock(return_value="hint_association")
        get_hint_name_mock = MagicMock(return_value="Ассоциация")
        get_all_hint_types_mock = MagicMock(return_value=["meaning", "association", "phonetic"])
        get_api_client_from_bot_mock = MagicMock(return_value=api_client)
        
        # Создаем мок для HintState
        hint_state_mock = MagicMock()
        hint_state_mock.save_to_state = AsyncMock()
        HintState_mock = MagicMock(return_value=hint_state_mock)
        
        # Используем patch.object для патчирования всех зависимостей
        with patch.object(create_handlers_module, 'validate_state_data', validate_state_data_mock), \
            patch.object(create_handlers_module, 'get_hint_key', get_hint_key_mock), \
            patch.object(create_handlers_module, 'get_hint_name', get_hint_name_mock), \
            patch.object(create_handlers_module, 'get_all_hint_types', get_all_hint_types_mock), \
            patch.object(create_handlers_module, 'get_api_client_from_bot', get_api_client_from_bot_mock), \
            patch.object(create_handlers_module, 'HintState', HintState_mock), \
            patch.object(create_handlers_module, 'logger'):
            
            # Вызываем тестируемую функцию
            await process_hint_create(callback, state)
            
            # Проверяем, что validate_state_data был вызван с правильными аргументами
            validate_state_data_mock.assert_called_once_with(
                state, 
                ["current_word", "db_user_id"],
                callback,
                "Ошибка: недостаточно данных для создания подсказки"
            )
            
            # Проверяем, что get_hint_key и get_hint_name были вызваны с правильными аргументами
            get_hint_key_mock.assert_called_once_with("association")
            get_hint_name_mock.assert_called_once_with("association")
            
            # Проверяем, что HintState был создан с правильными параметрами
            HintState_mock.assert_called_once_with(
                hint_key="hint_association",
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
            