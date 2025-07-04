"""
Unit tests for study handlers of the Language Learning Bot.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from aiogram import Dispatcher, Router
from aiogram.types import Message, User, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import app.bot.handlers.study_handlers as study_handlers_module
from app.bot.states.centralized_states import HintStates, StudyStates
from app.utils.error_utils import validate_state_data
from datetime import datetime, timedelta


class TestStudyHandlers:
    """Tests for the study handlers."""
    
    @pytest.fixture
    def setup_mocks(self):
        """Set up common mocks for tests."""
        # Mock message
        message = MagicMock(spec=Message)
        message.answer = AsyncMock()
        message.from_user = MagicMock(spec=User)
        message.from_user.id = 12345
        message.from_user.username = "test_user"
        message.from_user.first_name = "Test"
        message.from_user.last_name = "User"
        message.from_user.full_name = "Test User"
        
        # Mock state
        state = MagicMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={})
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()
        state.clear = AsyncMock()
        state.get_state = AsyncMock(return_value="StudyStates:studying")
        
        # Mock API client with new response format
        api_client = AsyncMock()
        api_client.get_user_by_telegram_id = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": None,
            "error": None
        })
        api_client.create_user = AsyncMock(return_value={
            "success": True,
            "status": 201,
            "result": {"id": "user123"},
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
        api_client.get_words_by_language = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [],
            "error": None
        })
        api_client.get_word = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": None,
            "error": None
        })
        api_client.get_user_word_data = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": None,
            "error": None
        })
        api_client.update_user_word_data = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": None,
            "error": None
        })
        api_client.create_user_word_data = AsyncMock(return_value={
            "success": True,
            "status": 201,
            "result": None,
            "error": None
        })
        api_client.get_study_words = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [
                {
                    "id": "word123",
                    "language_id": "lang123",
                    "word_foreign": "house",
                    "translation": "дом",
                    "transcription": "haʊs",
                    "word_number": 1
                }
            ],
            "error": None
        })
        api_client.get_user_progress = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [],
            "error": None
        })
        
        message.bot = MagicMock()
        message.bot.api_client = api_client

        # Mock callback
        callback = MagicMock(spec=CallbackQuery)
        callback.answer = AsyncMock()
        callback.message = message
        callback.from_user = message.from_user
        callback.bot = message.bot
        
        return message, state, api_client, callback
    
    @pytest.mark.asyncio
    async def test_cmd_study_without_language(self, setup_mocks):
        """Test the /study command handler when no language is selected."""
        message, state, api_client, _ = setup_mocks
        
        # Импортируем cmd_study здесь, чтобы избежать проблем с импортами
        from app.bot.handlers.study.study_commands import cmd_study
        
        # Сбрасываем счетчик вызовов перед тестом
        message.answer.reset_mock()
        
        # Patch the required functions, подменяя импорт cmd_language
        with patch('app.bot.handlers.study.study_commands.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.study.study_commands.logger'), \
             patch('app.bot.handlers.language_handlers.cmd_language', AsyncMock()) as mock_cmd_language:
            
            # Call the handler
            await cmd_study(message, state)
            
            # Проверяем, что сообщение об отсутствии языка отправлено
            assert "язык" in message.answer.call_args_list[0][0][0].lower()
            
            # Проверяем, что импорт cmd_language произошел
            # Так как мы не можем легко проверить вызов функции, которая импортируется внутри функции,
            # просто проверим, что функция пытается отправить сообщение с информацией о языке
    
    @pytest.mark.asyncio
    async def test_cmd_study_with_language(self, setup_mocks):
        """Test the cmd_study handler with a selected language."""

        message, state, api_client, _ = setup_mocks
        
        with patch('app.bot.handlers.study.study_commands.process_study', AsyncMock()) as mock_process_study:
                        
            # Call the handler
            from app.bot.handlers.study.study_commands import cmd_study
            await cmd_study(message, state)
            
            mock_process_study.assert_called_once()
            

    @pytest.mark.asyncio
    async def test_show_study_word(self, setup_mocks):
        """Test show_study_word function."""
        message, state, api_client, _ = setup_mocks
        
        # Сбрасываем счетчик вызовов перед тестом
        message.answer.reset_mock()
        
        # Set state data with study words
        word_data = {
            "id": "word123",
            "language_id": "lang123",
            "word_foreign": "house",
            "translation": "дом",
            "transcription": "haʊs",
            "word_number": 1,
            "user_word_data": {
                "is_skipped": False
            }
        }
        
        # Вместо использования get_user_language_settings, напрямую патчим state.get_data
        state.get_data = AsyncMock(return_value={
            "db_user_id": "user123",
            "current_language": {"id": "lang123", "name_ru": "Английский", "name_foreign": "English"},
            "show_hints": True
        })
        
        # Создаем функцию side_effect для message.answer, чтобы сохранить текст сообщения для проверки
        actual_message_text = None
        
        def capture_answer_text(text, **kwargs):
            nonlocal actual_message_text
            actual_message_text = text
            return None
        
        message.answer = AsyncMock(side_effect=capture_answer_text)
        
        # Patch UserWordState.from_state to return a mock with the data we need
        with patch('app.bot.handlers.study.study_words.UserWordState.from_state') as mock_user_word_state:
            # Create mock object with necessary properties
            mock_state_obj = MagicMock()
            mock_state_obj.is_valid.return_value = True
            mock_state_obj.has_more_words.return_value = True
            mock_state_obj.get_current_word.return_value = word_data
            mock_state_obj.get_flag = MagicMock(return_value=[])  # Empty list for active_hints and used_hints
            mock_state_obj.save_to_state = AsyncMock()
            mock_state_obj.user_id = "user123"
            mock_state_obj.word_id = "word123"
            mock_user_word_state.return_value = mock_state_obj
            
            # Mock keyboard
            keyboard_mock = MagicMock()
            
            # Patch the necessary functions
            with patch('app.bot.handlers.study.study_words.logger'), \
                patch('app.utils.settings_utils.get_user_language_settings', 
                    AsyncMock(return_value={
                        "show_hints": True
                    })):
                
                # Call the function
                from app.bot.handlers.study.study_words import show_study_word
                await show_study_word(message, state)
                
                # Check that the bot sent a message
                message.answer.assert_called_once()
                
                # Проверяем ключевые параметры в вызове метода
                call_kwargs = message.answer.call_args.kwargs
                assert "reply_markup" in call_kwargs
                
                # Проверяем содержимое текста сообщения на ключевые фрагменты
                assert actual_message_text is not None, "Текст сообщения не был записан"
                
                # Проверяем, что сообщение содержит важные элементы
                assert "дом" in actual_message_text, "Сообщение не содержит перевод слова 'дом'"
                assert "Английский" in actual_message_text, "Сообщение не содержит название языка 'Английский'"
                assert "house" not in actual_message_text, "Сообщение не должно содержать иностранное слово при первом показе"

    @pytest.mark.asyncio
    async def test_show_study_word_no_words(self, setup_mocks):
        """Test show_study_word function when no words available."""
        message, state, api_client, _ = setup_mocks
        
        # Сбрасываем счетчик вызовов перед тестом
        message.answer.reset_mock()
        
        # Patch UserWordState.from_state to return a mock with no words
        with patch('app.bot.handlers.study.study_words.UserWordState.from_state') as mock_user_word_state:
            # Create mock object with necessary properties
            mock_state_obj = MagicMock()
            mock_state_obj.is_valid.return_value = True
            mock_state_obj.has_more_words.return_value = False
            mock_user_word_state.return_value = mock_state_obj
            
            # Patch the necessary functions
            with patch('app.bot.handlers.study.study_words.logger'):
                
                # Call the function
                from app.bot.handlers.study.study_words import show_study_word
                await show_study_word(message, state)
                
                # Check that the bot sent an end message
                message.answer.assert_called_once()
                
                # Проверяем содержимое сообщения
                args, _ = message.answer.call_args
                assert "изучили все" in args[0].lower()

    @pytest.mark.asyncio
    async def test_process_show_word(self, setup_mocks):
        """Test process_show_word callback handler."""
        _, state, api_client, callback = setup_mocks
        
        with patch('app.bot.handlers.study.word_actions.word_display_actions.UserWordState.from_state') as mock_user_word_state:
            # Создаем мок для UserWordState
            mock_state_obj = MagicMock()
            mock_state_obj.is_valid.return_value = True
            mock_state_obj.set_flag = MagicMock()
            mock_state_obj.get_flag = MagicMock(return_value=[])  # Пустой список для used_hints
            # Заменяем get_active_hints, так как теперь используется get_used_hints
            mock_state_obj.get_used_hints = MagicMock(return_value=[])
            mock_state_obj.user_id = "user123"
            mock_state_obj.word_id = "word123"
            mock_state_obj.word_data = {
                "id": "word123",
                "language_id": "lang123",
                "word_foreign": "house",
                "translation": "дом",
                "transcription": "haʊs",
                "word_number": 1,
                "user_word_data": {}
            }
            mock_state_obj.save_to_state = AsyncMock()
            mock_user_word_state.return_value = mock_state_obj
            
            # Патчим другие зависимости
            with patch('app.bot.handlers.study.word_actions.word_display_actions.update_word_score', 
                    AsyncMock(return_value=(True, {
                        "check_interval": 0,
                        "next_check_date": "2025-05-13",
                        "score": 0,
                        "is_skipped": False
                    }))) as mock_update_score:
                
                # Вызываем обработчик
                from app.bot.handlers.study.word_actions.word_display_actions import process_show_word
                await process_show_word(callback, state)
                
                # Проверяем, что update_word_score был вызван с score=0
                mock_update_score.assert_called_once()
                call_args = mock_update_score.call_args
                assert call_args.kwargs["score"] == 0
                
                # Проверяем, что флаг word_shown был установлен
                mock_state_obj.set_flag.assert_called_with('word_shown', True)
                
                # Проверяем, что состояние было сохранено
                mock_state_obj.save_to_state.assert_called_once_with(state)
                
                # Проверяем, что сообщение было отредактировано
                callback.message.edit_text.assert_called_once()
                edit_args = callback.message.edit_text.call_args
                
                # Проверяем, что callback.answer был вызван
                callback.answer.assert_called_once()
                                
    @pytest.mark.asyncio
    async def test_process_toggle_word_skip(self, setup_mocks):
        """Test process_toggle_word_skip callback handler."""
        _, state, api_client, callback = setup_mocks
        
        # Mock validate_state_data to return True with test data
        with patch('app.bot.handlers.study.word_actions.word_display_actions.validate_state_data') as mock_validate:
            # Set up mock data for validate_state_data
            mock_validate.return_value = (True, {
                "current_word_id": "word123",
                "current_word": {
                    "id": "word123",
                    "language_id": "lang123",
                    "word_foreign": "house",
                    "translation": "дом",
                    "transcription": "haʊs",
                    "word_number": 1,
                    "user_word_data": {
                        "is_skipped": False  # Изначально слово не пропускается
                    }
                },
                "db_user_id": "user123",
                "current_study_index": 0
            })
            
            # Patch UserWordState to avoid actual state updates
            with patch('app.bot.handlers.study.word_actions.word_display_actions.UserWordState.from_state') as mock_user_word_state:
                # Create mock for UserWordState
                mock_state_obj = MagicMock()
                mock_state_obj.is_valid.return_value = True
                mock_state_obj.word_data = {
                    "id": "word123",
                    "language_id": "lang123",
                    "word_foreign": "house",
                    "translation": "дом",
                    "transcription": "haʊs",
                    "word_number": 1,
                    "user_word_data": {
                        "is_skipped": False  # Изначально слово не пропускается
                    }
                }
                mock_state_obj.save_to_state = AsyncMock()
                mock_user_word_state.return_value = mock_state_obj
                
                # Patch update_word_score
                with patch('app.bot.handlers.study.word_actions.word_display_actions.update_word_score', AsyncMock(return_value=(True, {"is_skipped": True}))) as mock_update_score, \
                     patch('app.bot.handlers.study.word_actions.word_display_actions.show_study_word', AsyncMock()) as mock_show_study:
                
                    # Call the handler
                    from app.bot.handlers.study.word_actions.word_utility_actions import process_toggle_word_skip
                    await process_toggle_word_skip(callback, state)
                    
                    # Check that the bot sent a message
                    callback.message.answer.assert_called_once()
                    
    def test_register_handlers(self):
        """Test the register_handlers function."""
        # Create a mock dispatcher
        dp = MagicMock(spec=Dispatcher)
        dp.include_router = MagicMock()
        
        # Call the register_handlers function
        study_handlers_module.register_study_handlers(dp)
        
        # Check that include_router was called with the study_router
        dp.include_router.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_word_know(self, setup_mocks):
        """Test process_word_know callback handler with NEW LOGIC - immediate score update."""
        _, state, api_client, callback = setup_mocks
        
        with patch('app.bot.handlers.study.word_actions.word_evaluation_actions.UserWordState.from_state') as mock_user_word_state:
            # Create mock for UserWordState
            mock_state_obj = MagicMock()
            mock_state_obj.is_valid.return_value = True
            mock_state_obj.set_flag = MagicMock()
            mock_state_obj.save_to_state = AsyncMock()
            mock_user_word_state.return_value = mock_state_obj
            
            # НОВОЕ: Патчим update_word_score для немедленного обновления оценки
            with patch('app.bot.handlers.study.word_actions.word_evaluation_actions.update_word_score', 
                        AsyncMock(return_value=(True, {
                            "score": 1,
                            "check_interval": 2, 
                            "next_check_date": "2025-05-15T00:00:00"
                        }))) as mock_update_score:
                
                # Call the handler
                from app.bot.handlers.study.word_actions.word_evaluation_actions import process_word_know
                await process_word_know(callback, state)
                
                # Check that the bot sent a message with confirmation buttons
                callback.message.answer.assert_called_once()
                call_args = callback.message.answer.call_args
                
                # Проверяем, что оба флага были установлены
                mock_state_obj.set_flag.assert_any_call('pending_next_word', True)
                mock_state_obj.set_flag.assert_any_call('pending_word_know', True)
                
                # Проверяем, что состояние было сохранено
                mock_state_obj.save_to_state.assert_called_once_with(state)
                    
    @pytest.mark.asyncio
    async def test_process_confirm_next_word(self, setup_mocks):
        """Test process_confirm_next_word callback handler with NEW LOGIC - no score update."""
        _, state, api_client, callback = setup_mocks
        
        with patch('app.bot.handlers.study.word_actions.word_navigation_actions.process_next_word', AsyncMock()) as mock_process_next_word, \
            patch('app.bot.handlers.study.word_actions.word_navigation_actions.logger', MagicMock()):
            
            # Call the handler
            from app.bot.handlers.study.word_actions.word_navigation_actions import process_confirm_next_word
            await process_confirm_next_word(callback, state)
            
            mock_process_next_word.assert_called_once()
                
    @pytest.mark.asyncio
    async def test_process_show_word_rollback_scenario(self, setup_mocks):
        """Test process_show_word when called after 'word_know' (rollback scenario)."""
        _, state, api_client, callback = setup_mocks
        
        # Mock validate_state_data для возврата тестовых данных
        with patch('app.bot.handlers.study.word_actions.word_display_actions.validate_state_data') as mock_validate:
            # Настраиваем данные для validate_state_data
            mock_validate.return_value = (True, {
                "current_word_id": "word123",
                "current_word": {
                    "id": "word123",
                    "language_id": "lang123",
                    "word_foreign": "house",
                    "translation": "дом",
                    "transcription": "haʊs",
                    "word_number": 1,
                    "user_word_data": {
                        "score": 1,  # Была установлена в word_know
                        "check_interval": 2,
                        "next_check_date": "2025-05-15T00:00:00",
                        "is_skipped": False  # ДОБАВЛЕНО: поле is_skipped
                    }
                },
                "db_user_id": "user123",
                "current_study_index": 0
            })
            
            # Патчим UserWordState
            with patch('app.bot.handlers.study.word_actions.word_display_actions.UserWordState.from_state') as mock_user_word_state:
                # Создаем мок для UserWordState с флагом pending_word_know
                mock_state_obj = MagicMock()
                mock_state_obj.is_valid.return_value = True
                mock_state_obj.set_flag = MagicMock()
                mock_state_obj.remove_flag = MagicMock()
                mock_state_obj.get_flag = MagicMock(side_effect=lambda name, default=None: 
                    True if name == 'pending_word_know' else ([] if name == 'used_hints' else default))
                mock_state_obj.user_id = "user123"
                mock_state_obj.word_id = "word123"
                mock_state_obj.word_data = mock_validate.return_value[1]["current_word"]
                mock_state_obj.save_to_state = AsyncMock()
                mock_user_word_state.return_value = mock_state_obj
                
                # Патчим зависимости
                with patch('app.bot.handlers.study.word_actions.word_display_actions.update_word_score', 
                          AsyncMock(return_value=(True, {
                              "check_interval": 0,
                              "next_check_date": None,
                              "score": 0,  # Откат к оценке 0
                              "is_skipped": False
                          }))) as mock_update_score:
                    
                    # Настраиваем ответ API для get_language
                    api_client.get_language.return_value = {
                        "success": True, 
                        "result": {
                            "id": "lang123", 
                            "name_ru": "Английский", 
                            "name_foreign": "English"
                        }
                    }
                    
                    # Вызываем обработчик
                    from app.bot.handlers.study.word_actions.word_display_actions import process_show_word
                    await process_show_word(callback, state)
                    
                    # НОВОЕ: Проверяем, что update_word_score был вызван с score=0 (откат)
                    mock_update_score.assert_called_once()
                    call_args = mock_update_score.call_args
                    assert call_args.kwargs["score"] == 0  # Откат к оценке 0
                    
                    # Проверяем, что флаг word_shown был установлен
                    mock_state_obj.set_flag.assert_called_with('word_shown', True)
                    
                    # ИСПРАВЛЕНО: save_to_state может вызываться несколько раз в реальном коде
                    # Проверяем, что состояние было сохранено хотя бы один раз
                    assert mock_state_obj.save_to_state.call_count >= 1
                    
                    # Проверяем, что было отправлено сообщение о возврате к изучению
                    assert callback.message.answer.call_count >= 1

    @pytest.mark.asyncio 
    async def test_word_know_then_show_word_flow(self, setup_mocks):
        """Test complete flow: word_know -> show_word (rollback scenario)."""
        _, state, api_client, callback = setup_mocks
        
        with patch('app.bot.handlers.study.word_actions.word_evaluation_actions.UserWordState.from_state') as mock_user_word_state_1:
            mock_state_obj_1 = MagicMock()
            mock_state_obj_1.is_valid.return_value = True
            mock_state_obj_1.set_flag = MagicMock()
            mock_state_obj_1.save_to_state = AsyncMock()
            mock_user_word_state_1.return_value = mock_state_obj_1
            
            with patch('app.bot.handlers.study.word_actions.word_evaluation_actions.update_word_score', 
                    AsyncMock(return_value=(True, {
                        "score": 1, 
                        "check_interval": 2, 
                        "next_check_date": "2025-05-15T00:00:00",  # ИСПРАВЛЕНО: добавлено поле
                        "is_skipped": False
                    }))) as mock_update_score_1:
                
                # Сбрасываем моки перед первым вызовом
                callback.message.answer.reset_mock()
                
                # Вызываем word_know
                from app.bot.handlers.study.word_actions.word_evaluation_actions import process_word_know
                await process_word_know(callback, state)
                
                # Проверяем, что оценка была обновлена на 1
                mock_update_score_1.assert_called_once()
                assert mock_update_score_1.call_args.kwargs["score"] == 1
                
                # Проверяем, что флаги pending были установлены
                mock_state_obj_1.set_flag.assert_any_call('pending_word_know', True)
                
