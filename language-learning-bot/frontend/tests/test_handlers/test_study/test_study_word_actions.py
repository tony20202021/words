"""
тесты в этом модуле должны быть простыми
просто вызов тестируемой функции
и минимальная проверка логики, которую она реализует
например проверка, что действительно были вызваны ключевые функции, существенные для ее реализации
все внешние вызовы должны быть заменены на моки

"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext


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
        
        # Создаем моки для зависимостей
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
        
        # Патчим зависимости
        import app.bot.handlers.study.word_actions.word_display_actions as word_display_actions_module

        with patch('app.bot.handlers.study.word_actions.word_display_actions.update_word_score', update_word_score_mock), \
            patch('app.utils.state_models.UserWordState.from_state', user_word_state_from_state_mock), \
            patch('app.bot.handlers.study.word_actions.word_display_actions.show_study_word', AsyncMock()) as show_study_word_mock, \
            patch('app.bot.handlers.study.word_actions.word_display_actions.logger'):
            
            # Вызываем тестируемую функцию
            await word_display_actions_module.process_show_word(callback, state)
            
            # Проверки
            update_word_score_mock.assert_called_once()
            user_word_state_mock.set_flag.assert_called_with('word_shown', True)
            user_word_state_mock.save_to_state.assert_called_once_with(state)
            show_study_word_mock.assert_called_once()
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
        user_word_state_mock.advance_to_next_word = MagicMock(return_value=True)
        user_word_state_mock.save_to_state = AsyncMock()
        user_word_state_from_state_mock = AsyncMock(return_value=user_word_state_mock)
        
        # Моки для других функций
        show_study_word_mock = AsyncMock()
        
        # Патчим зависимости
        import app.bot.handlers.study.word_actions.word_navigation_actions as word_navigation_actions_module
        from app.bot.states.centralized_states import StudyStates

        with patch('app.utils.state_models.UserWordState.from_state', user_word_state_from_state_mock), \
            patch('app.bot.handlers.study.word_actions.word_navigation_actions.show_study_word', show_study_word_mock), \
            patch('app.bot.handlers.study.word_actions.word_navigation_actions.logger'):
            
            # Вызываем тестируемую функцию
            await word_navigation_actions_module.process_next_word(callback, state)
            
            user_word_state_mock.advance_to_next_word.assert_called_once()
            user_word_state_mock.save_to_state.assert_called_once_with(state)
            state.set_state.assert_called_once_with(StudyStates.studying)
            show_study_word_mock.assert_called_once_with(callback, state, user_word_state_mock, need_new_message=True)
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
        
        # Мок для UserWordState
        user_word_state_mock = MagicMock()
        user_word_state_mock.is_valid.return_value = True
        user_word_state_mock.word_data = state_data["current_word"]
        user_word_state_mock.get_flag = MagicMock(return_value=[])
        user_word_state_mock.save_to_state = AsyncMock()
        user_word_state_from_state_mock = AsyncMock(return_value=user_word_state_mock)

        # Мок для show_study_word
        show_study_word_mock = AsyncMock()
        
        # Патчим зависимости
        import app.bot.handlers.study.word_actions.word_utility_actions as word_utility_actions_module
        
        with patch('app.utils.state_models.UserWordState.from_state', user_word_state_from_state_mock), \
            patch('app.bot.handlers.study.word_actions.word_utility_actions.ensure_user_word_data', AsyncMock(return_value=(True, None))), \
            patch('app.bot.handlers.study.word_actions.word_utility_actions.show_study_word', show_study_word_mock), \
            patch('app.bot.handlers.study.word_actions.word_utility_actions.logger'):
            
            # Вызываем тестируемую функцию
            await word_utility_actions_module.process_toggle_word_skip(callback, state)
            
            assert user_word_state_mock.save_to_state.called
            show_study_word_mock.assert_called_once()
            callback.answer.assert_called_once()
            