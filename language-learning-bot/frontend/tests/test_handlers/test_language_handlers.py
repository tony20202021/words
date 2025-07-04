"""
Unit tests for language handlers of the Language Learning Bot.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from aiogram import Dispatcher
from aiogram.types import Message, User, CallbackQuery
from aiogram.fsm.context import FSMContext
import app.bot.handlers.language_handlers as language_handlers


class TestLanguageHandlers:
    """Tests for the language handlers."""
    
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
        message.bot = MagicMock()
        
        # Mock state
        state = MagicMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={})
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()
        state.clear = AsyncMock()
        
        # Mock API client
        api_client = AsyncMock()
        api_client.get_word_count_by_language = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {"count": 100},
            "error": None
        })
        
        # Добавляем мок для get_user_progress
        api_client.get_user_progress = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {
                "words_studied": 10,
                "words_known": 5,
                "words_skipped": 2,
                "total_words": 100,
                "progress_percentage": 5.0
            },
            "error": None
        })
        
        # Mock callback
        callback = MagicMock(spec=CallbackQuery)
        callback.answer = AsyncMock()
        callback.message = message
        callback.from_user = message.from_user
        callback.data = "lang_select_1"
        callback.bot = message.bot
        
        return message, state, api_client, callback
    
    @pytest.mark.asyncio
    async def test_process_language_with_languages(self, setup_mocks):
        """Test the /language command handler when languages are available."""
        message, state, api_client, _ = setup_mocks
        
        # Создаем мок для функции get_available_languages, который вернет список языков в новом формате
        api_client.get_languages = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [
                {"id": 1, "name_ru": "Английский", "name_foreign": "English"},
                {"id": 2, "name_ru": "Испанский", "name_foreign": "Español"},
                {"id": 3, "name_ru": "Китайский", "name_foreign": "中文"}
            ],
            "error": None
        })
        
        # Мокируем get_user_by_telegram_id для получения db_user_id
        api_client.get_user_by_telegram_id = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [{"id": "user123"}],
            "error": None
        })
        
        # Патчим функцию get_available_languages, чтобы она не пыталась вызвать реальную функцию
        # Мы непосредственно мокируем работу с API клиентом
        with patch('app.bot.handlers.language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.language_handlers.logger'), \
             patch('app.bot.handlers.language_handlers.InlineKeyboardBuilder'):
            # Call the handler
            await language_handlers.process_language(message, state)
            
            # Check API calls
            api_client.get_languages.assert_called_once()
            api_client.get_user_by_telegram_id.assert_called_once()
            
            # Check that the bot sent a response message
            assert message.answer.call_count == 4
    
    @pytest.mark.asyncio
    async def test_process_language_without_languages(self, setup_mocks):
        """Test the /language command handler when no languages are available."""
        message, state, api_client, _ = setup_mocks
        
        # Мокируем get_languages для возврата пустого списка
        api_client.get_languages = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [],
            "error": None
        })
        
        # Патчим функцию get_available_languages
        with patch('app.bot.handlers.language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.language_handlers.logger'):
            # Call the handler
            await language_handlers.process_language(message, state)
            
            # Check API calls
            api_client.get_languages.assert_called_once()
            
            # Check that the bot sent an error message
            message.answer.assert_called_once_with(
                "В системе пока нет доступных языков. "
                "Обратитесь к администратору бота."
            )
    
    @pytest.mark.asyncio
    async def test_process_language_selection_success(self, setup_mocks):
        """Test the process_language_selection callback handler with valid language."""
        _, state, api_client, callback = setup_mocks
        
        # Мокируем get_language
        api_client.get_language = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {
                "id": 1, 
                "name_ru": "Английский",
                "name_foreign": "English"
            },
            "error": None
        })
        
        # Мокируем get_user_by_telegram_id
        api_client.get_user_by_telegram_id = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [{"id": "user123"}],
            "error": None
        })
        
        # Мокируем get_user_progress
        api_client.get_user_progress = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {
                "words_studied": 10,
                "words_known": 5,
                "words_skipped": 2,
                "total_words": 100,
                "progress_percentage": 5.0
            },
            "error": None
        })
        
        # Патчим функции API и get_user_language_settings
        with patch('app.bot.handlers.language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.language_handlers.logger'), \
             patch('app.bot.handlers.language_handlers.get_user_language_settings', 
                   AsyncMock(return_value={
                      "start_word": 1,
                      "skip_marked": False,
                      "use_check_date": True,
                      "show_hints": True
                   })):
             
            # Сбросим счетчик вызовов update_data перед тестом
            state.update_data.reset_mock()
            
            # Call the handler
            await language_handlers.process_language_selection(callback, state)
            
            # Проверяем вызов API методов через патчированную функцию get_language_by_id
            # Проверяем вызов API методов
            api_client.get_user_by_telegram_id.assert_called_once()
            api_client.get_user_progress.assert_called_once()
            
            # Проверяем, что update_data был вызван для сохранения языка и настроек
            assert state.update_data.call_count <= 3
            
            # Проверяем, что бот отправил сообщение об успехе
            assert callback.message.answer.call_count == 2
            
            # Проверяем, что callback.answer был вызван
            callback.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_language_selection_error(self, setup_mocks):
        """Test the process_language_selection callback handler with invalid language ID."""
        _, state, api_client, callback = setup_mocks
        
        # Set callback data for non-existent language
        callback.data = "lang_select_999"
        
        # Мокируем get_language для возврата ошибки (язык не найден)
        api_client.get_language = AsyncMock(return_value={
            "success": True,
            "status": 404,
            "result": None,
            "error": None
        })
        
        # Патчим функции API 
        with patch('app.bot.handlers.language_handlers.get_api_client_from_bot', return_value=api_client), \
             patch('app.bot.handlers.language_handlers.logger'):

            # Call the handler
            await language_handlers.process_language_selection(callback, state)
            
            # Проверяем, что отправлено сообщение об ошибке
            assert callback.answer.call_count == 2
    
    def test_register_handlers(self):
        """Test the register_handlers function."""
        # Create a mock dispatcher
        dp = MagicMock(spec=Dispatcher)
        dp.include_router = MagicMock()
        
        # Call the register_handlers function
        language_handlers.register_handlers(dp)
        
        # Check that include_router was called with the language_router
        dp.include_router.assert_called_once_with(language_handlers.language_router)

    @pytest.mark.asyncio
    async def test_cmd_language_keyboard_creation(self, setup_mocks):
        """Test that cmd_language creates proper keyboard with language buttons."""
        message, state, api_client, _ = setup_mocks
        
        # Настраиваем возвращаемое значение для get_languages
        api_client.get_languages = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [
                {"id": "lang1", "name_ru": "Английский", "name_foreign": "English"},
                {"id": "lang2", "name_ru": "Испанский", "name_foreign": "Español"}
            ],
            "error": None
        })
        
        # Мокируем get_user_by_telegram_id
        api_client.get_user_by_telegram_id = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [{"id": "user123"}],
            "error": None
        })
        
        # Создаем мок для InlineKeyboardBuilder
        mock_keyboard_builder = MagicMock()
        mock_keyboard_builder.button = MagicMock()
        mock_keyboard_builder.adjust = MagicMock()
        mock_keyboard_builder.as_markup = MagicMock(return_value="mock_markup")
        
        # Импортируем модуль, где определена тестируемая функция
        import app.bot.handlers.language_handlers as language_handlers_module
        
        # Патчим все зависимости с помощью patch.object
        with patch.object(language_handlers_module, 'get_api_client_from_bot', return_value=api_client), \
            patch.object(language_handlers_module, 'logger'), \
            patch.object(language_handlers_module, 'InlineKeyboardBuilder', return_value=mock_keyboard_builder):
            
            # Вызываем тестируемую функцию
            await language_handlers_module.cmd_language(message, state)
            
            # Проверяем, что был создан InlineKeyboardBuilder
            assert mock_keyboard_builder.button.call_count == 2
            
            # Проверяем, что кнопки были созданы для обоих языков
            mock_keyboard_builder.button.assert_any_call(
                text=mock_keyboard_builder.button.call_args_list[0].kwargs['text'],
                callback_data=f"lang_select_lang1"
            )
            mock_keyboard_builder.button.assert_any_call(
                text=mock_keyboard_builder.button.call_args_list[1].kwargs['text'],
                callback_data=f"lang_select_lang2"
            )
            
            # Проверяем, что был вызван adjust для настройки расположения кнопок
            mock_keyboard_builder.adjust.assert_called_once_with(1)
            
            # Проверяем, что был вызван as_markup для получения разметки
            mock_keyboard_builder.as_markup.assert_called_once()
            
            # Проверяем, что сообщение было отправлено с клавиатурой
            assert message.answer.call_count == 3

    @pytest.mark.asyncio
    async def test_process_language_selection_user_progress(self, setup_mocks):
        """Test that process_language_selection correctly handles user progress."""
        _, state, api_client, callback = setup_mocks
        
        # Настраиваем callback.data
        callback.data = "lang_select_lang1"
        
        # Мокируем get_language для возврата данных о языке
        api_client.get_language = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {
                "id": "lang1", 
                "name_ru": "Английский",
                "name_foreign": "English"
            },
            "error": None
        })
        
        # Мокируем get_user_by_telegram_id для возврата данных о пользователе
        api_client.get_user_by_telegram_id = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [{"id": "user123"}],
            "error": None
        })
        
        # Мокируем get_user_progress для возврата данных о прогрессе
        api_client.get_user_progress = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {
                "words_studied": 100,
                "words_known": 80,
                "words_skipped": 10,
                "total_words": 1000,
                "progress_percentage": 8.0
            },
            "error": None
        })
        
        # Импортируем модуль, где определена тестируемая функция
        import app.bot.handlers.language_handlers as language_handlers_module
        
        # Патчим все зависимости с помощью patch.object
        with patch.object(language_handlers_module, 'get_api_client_from_bot', return_value=api_client), \
            patch.object(language_handlers_module, 'logger'), \
            patch.object(language_handlers_module, 'get_user_language_settings', 
                        AsyncMock(return_value={
                            "start_word": 1,
                            "skip_marked": False,
                            "use_check_date": True,
                            "show_hints": True
                        })), \
            patch.object(language_handlers_module, 'format_settings_text', 
                        return_value="Formatted settings text"):
            
            # Вызываем тестируемую функцию
            await language_handlers_module.process_language_selection(callback, state)
            
            # Проверяем, что данные пользователя и прогресс были получены
            api_client.get_user_by_telegram_id.assert_called_once()
            api_client.get_user_progress.assert_called_once()
            
            # Проверяем, что были получены настройки пользователя
            language_handlers_module.get_user_language_settings.assert_called_once()
            
            # Проверяем, что состояние было обновлено с информацией о настройках
            assert state.update_data.call_count == 3
            
            # Проверяем, что было отправлено сообщение с информацией о языке и прогрессе
            assert callback.message.answer.call_count == 2
            
            sent_message = callback.message.answer.call_args.args[0]
            assert "Вы выбрали язык: <b>Английский (English)</b>" in sent_message
            assert "Изучено слов: 100" in sent_message
            assert "Известно слов: 80" in sent_message
            assert "Пропущено слов: 10" in sent_message
            assert "Всего слов: 1000" in sent_message
            assert "Прогресс: 8.0%" in sent_message
            
            # Проверяем, что callback.answer был вызван для скрытия уведомления
            callback.answer.assert_called_once()