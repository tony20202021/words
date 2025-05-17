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
from app.bot.handlers.study.study_states import HintStates, StudyStates

# Импортируем функции обработчиков из правильных подмодулей
from app.bot.handlers.study.hint.create_handlers import process_hint_create, process_hint_text
from app.bot.handlers.study.hint.edit_handlers import process_hint_edit, process_hint_edit_text
from app.bot.handlers.study.hint.common import cmd_cancel_hint
from app.bot.handlers.study.hint.toggle_handlers import process_hint_toggle
import app.bot.handlers.study.study_hint_handlers as study_hint_handlers


class TestStudyWordActions:

    @pytest.mark.asyncio
    async def test_process_show_word(self):
        """Test process_show_word function."""
        # Настраиваем моки
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = MagicMock()
        callback.from_user.id = 12345
        callback.from_user.username = "test_user"
        callback.from_user.full_name = "Test User"
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()  # Добавляем edit_text
        callback.message.answer = AsyncMock()
        callback.answer = AsyncMock()
        
        # Мок для API клиента
        api_client = MagicMock()
        api_client.get_language = AsyncMock(return_value={
            "success": True,
            "result": {
                "id": "lang123", 
                "name_ru": "Английский", 
                "name_foreign": "English"
            }
        })
        callback.bot = MagicMock()
        callback.bot.api_client = api_client
        
        state = MagicMock(spec=FSMContext)
        
        # Готовим данные для validate_state_data
        state_data = {
            "current_word": {
                "id": "word123",
                "word_foreign": "house",
                "translation": "дом",
                "transcription": "haʊs",
                "language_id": "lang123",
                "user_word_data": {}
            },
            "current_word_id": "word123",
            "db_user_id": "user123"
        }
        
        # Создаем моки для зависимостей
        validate_state_data_mock = AsyncMock(return_value=(True, state_data))
        update_word_score_mock = AsyncMock(return_value=(True, {
            "score": 0,
            "check_interval": 0,
            "next_check_date": "2025-05-20",
            "is_skipped": False
        }))
        user_word_state_mock = MagicMock()
        user_word_state_mock.is_valid.return_value = True
        user_word_state_mock.user_id = "user123"  # Добавляем user_id
        user_word_state_mock.word_id = "word123"  # Добавляем word_id
        user_word_state_mock.set_flag = MagicMock()
        user_word_state_mock.get_flag = MagicMock(return_value=[])  # Возвращаем пустой список для used_hints
        user_word_state_mock.save_to_state = AsyncMock()
        user_word_state_from_state_mock = AsyncMock(return_value=user_word_state_mock)
        
        format_used_hints_mock = AsyncMock(return_value="")  # Мок для format_used_hints
        get_show_hints_setting_mock = AsyncMock(return_value=True)  # Мок для get_show_hints_setting
        create_word_keyboard_mock = MagicMock(return_value="KEYBOARD")  # Мок для create_word_keyboard
        
        # Патчим зависимости
        import app.bot.handlers.study.study_word_actions as word_actions_module

        with patch('app.bot.handlers.study.study_word_actions.validate_state_data', validate_state_data_mock), \
            patch('app.bot.handlers.study.study_word_actions.update_word_score', update_word_score_mock), \
            patch('app.utils.state_models.UserWordState.from_state', user_word_state_from_state_mock), \
            patch('app.bot.handlers.study.study_word_actions.get_api_client_from_bot', MagicMock(return_value=api_client)), \
            patch('app.utils.formatting_utils.format_used_hints', format_used_hints_mock), \
            patch('app.utils.settings_utils.get_show_hints_setting', get_show_hints_setting_mock), \
            patch('app.bot.keyboards.study_keyboards.create_word_keyboard', create_word_keyboard_mock), \
            patch('app.bot.handlers.study.study_word_actions.logger'):
            
            # Вызываем тестируемую функцию
            await word_actions_module.process_show_word(callback, state)
            
            # Проверки
            # 1. Проверяем вызов validate_state_data
            validate_state_data_mock.assert_called_once()
            
            # 2. Проверяем вызов update_word_score с правильными параметрами
            update_word_score_mock.assert_called_once()
            
            # 3. Проверяем, что был вызван api_client.get_language
            api_client.get_language.assert_called_once_with("lang123")
            
            # 4. Проверяем, что установлен флаг word_shown
            user_word_state_mock.set_flag.assert_called_with('word_shown', True)
            
            # 5. Проверяем сохранение состояния
            user_word_state_mock.save_to_state.assert_called_once_with(state)
            
            # 6. Проверяем, что сообщение было отредактировано или отправлено
            assert callback.message.edit_text.called or callback.message.answer.called
            
            # 7. Проверяем вызов callback.answer
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_next_word(self):
        """Test process_next_word function."""
        # Настраиваем моки
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = MagicMock()
        callback.from_user.id = 12345
        callback.from_user.username = "test_user"
        callback.from_user.full_name = "Test User"
        callback.message = MagicMock()
        callback.message.answer = AsyncMock()
        callback.answer = AsyncMock()
        
        state = MagicMock(spec=FSMContext)
        
        # Создаем пользовательский state
        user_word_state_mock = MagicMock()
        user_word_state_mock.is_valid.return_value = True
        user_word_state_mock.set_flag = MagicMock()
        user_word_state_mock.advance_to_next_word = MagicMock()
        user_word_state_mock.save_to_state = AsyncMock()
        user_word_state_from_state_mock = AsyncMock(return_value=user_word_state_mock)
        
        # Моки для других функций
        show_study_word_mock = AsyncMock()
        
        # Патчим зависимости
        import app.bot.handlers.study.study_word_actions as word_actions_module

        with patch('app.utils.state_models.UserWordState.from_state', user_word_state_from_state_mock), \
            patch('app.bot.handlers.study.study_word_actions.show_study_word', show_study_word_mock), \
            patch('app.bot.handlers.study.study_word_actions.logger'):
            
            # Вызываем тестируемую функцию
            await word_actions_module.process_next_word(callback, state)
            
            # Проверки
            # 1. Проверяем установку флага word_shown в False
            user_word_state_mock.set_flag.assert_called_once_with('word_shown', False)
            
            # 2. Проверяем вызов advance_to_next_word
            user_word_state_mock.advance_to_next_word.assert_called_once()
            
            # 3. Проверяем сохранение состояния
            user_word_state_mock.save_to_state.assert_called_once_with(state)
            
            # 4. Проверяем отправку промежуточного сообщения
            callback.message.answer.assert_called_once_with("🔄 Переходим к следующему слову...")
            
            # 5. Проверяем вызов show_study_word
            show_study_word_mock.assert_called_once_with(callback.message, state)
            
            # 6. Проверяем вызов callback.answer
            callback.answer.assert_called_once()
                    
    @pytest.mark.asyncio
    async def test_process_toggle_word_skip(self):
        """Test process_toggle_word_skip function."""
        # Настраиваем моки
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = MagicMock()
        callback.from_user.id = 12345
        callback.from_user.username = "test_user"
        callback.from_user.full_name = "Test User"
        callback.message = MagicMock()
        callback.message.answer = AsyncMock()
        callback.answer = AsyncMock()
        
        # Мок для API клиента - обратите внимание на добавление get_user_language_settings
        api_client = MagicMock()
        api_client.get_language = AsyncMock(return_value={
            "success": True,
            "result": {
                "id": "lang123", 
                "name_ru": "Английский", 
                "name_foreign": "English"
            }
        })
        # Важно: добавить мок для метода get_user_language_settings в api_client
        api_client.get_user_language_settings = AsyncMock(return_value={
            "success": True,
            "result": {
                "show_debug": False,
                "show_hints": True,
                "start_word": 1,
                "skip_marked": False,
                "use_check_date": True
            },
            "error": None
        })
        callback.bot = MagicMock()
        callback.bot.api_client = api_client
        
        state = MagicMock(spec=FSMContext)
        
        # Готовим данные для validate_state_data
        state_data = {
            "current_word": {
                "id": "word123",
                "word_foreign": "house",
                "translation": "дом",
                "transcription": "haʊs",
                "language_id": "lang123",
                "user_word_data": {
                    "is_skipped": False  # Изначально не пропускается
                }
            },
            "current_word_id": "word123",
            "db_user_id": "user123",
            "current_language": {
                "id": "lang123",
                "name_ru": "Английский",
                "name_foreign": "English"
            }
        }
        
        # Настраиваем state.get_data
        state.get_data = AsyncMock(return_value=state_data)
        
        # Создаем моки для зависимостей
        validate_state_data_mock = AsyncMock(return_value=(True, state_data))
        update_word_score_mock = AsyncMock(return_value=(True, {
            "score": 0,
            "check_interval": 0,
            "next_check_date": "2025-05-20",
            "is_skipped": True  # Стало пропускаемым
        }))
        
        # Мок для UserWordState
        user_word_state_mock = MagicMock()
        user_word_state_mock.is_valid.return_value = True
        user_word_state_mock.word_data = state_data["current_word"]
        user_word_state_mock.get_flag = MagicMock(return_value=[])
        user_word_state_mock.save_to_state = AsyncMock()
        user_word_state_from_state_mock = AsyncMock(return_value=user_word_state_mock)
        
        # Мок для show_study_word
        show_study_word_mock = AsyncMock()
        
        # Создаем простой мок для get_user_language_settings, который просто возвращает словарь
        # без всякой внутренней логики
        async def mock_get_user_language_settings(msg_obj, state_obj):
            return {"show_debug": False, "show_hints": True}
        
        # Патчим зависимости
        import app.bot.handlers.study.study_word_actions as word_actions_module
        
        with patch('app.bot.handlers.study.study_word_actions.validate_state_data', validate_state_data_mock), \
            patch('app.bot.handlers.study.study_word_actions.update_word_score', update_word_score_mock), \
            patch('app.utils.state_models.UserWordState.from_state', user_word_state_from_state_mock), \
            patch('app.bot.handlers.study.study_word_actions.show_study_word', show_study_word_mock), \
            patch('app.bot.handlers.study.study_word_actions.get_api_client_from_bot', MagicMock(return_value=api_client)), \
            patch('app.utils.settings_utils.get_user_language_settings', mock_get_user_language_settings), \
            patch('app.utils.settings_utils.get_show_hints_setting', AsyncMock(return_value=True)), \
            patch('app.bot.handlers.study.study_word_actions.logger'):
            
            # Вызываем тестируемую функцию
            await word_actions_module.process_toggle_word_skip(callback, state)
            
            # Проверки
            # 1. Проверяем вызов validate_state_data
            validate_state_data_mock.assert_called_once()
            
            # 2. Проверяем вызов update_word_score
            update_word_score_mock.assert_called_once()
            
            # 3. Проверяем, что отправлено сообщение пользователю
            callback.message.answer.assert_called_once()
            message_text = callback.message.answer.call_args[0][0]
            assert "Статус изменен" in message_text
            assert "пропускаться" in message_text
            assert "house" in message_text
            
            # 4. Проверяем обновление state
            assert user_word_state_mock.save_to_state.called
            
            # 5. Проверяем вызов show_study_word
            show_study_word_mock.assert_called_once_with(callback.message, state)
            
            # 6. Проверяем вызов callback.answer
            callback.answer.assert_called_once()
            