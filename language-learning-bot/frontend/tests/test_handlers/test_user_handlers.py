"""
Unit tests for user handlers of the Language Learning Bot.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from aiogram import Dispatcher
from aiogram.types import Message, User, CallbackQuery
from aiogram.fsm.context import FSMContext
import app.bot.handlers.user_handlers as user_handlers


class TestUserHandlers:
    """Tests for the user handlers."""
    
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
        
        # Mock API client с корректным форматом ответов
        api_client = AsyncMock()
        api_client.get_user_by_telegram_id = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [],  # Пустой список, будет интерпретирован как отсутствие пользователя
            "error": None
        })
        
        api_client.create_user = AsyncMock(return_value={
            "success": True,
            "status": 201,
            "result": {"id": "user123"},
            "error": None
        })
        
        api_client.get_languages = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [],
            "error": None
        })
        
        api_client.get_user_progress = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": None,
            "error": None
        })
        
        return message, state, api_client
    
    @pytest.fixture
    def setup_callback_mock(self):
        """Set up common mock for callback."""
        callback = MagicMock(spec=CallbackQuery)
        callback.answer = AsyncMock()
        callback.message = MagicMock(spec=Message)
        callback.message.answer = AsyncMock()
        callback.from_user = MagicMock(spec=User)
        callback.from_user.id = 12345
        callback.from_user.username = "test_user"
        callback.from_user.full_name = "Test User"
        
        return callback

    @pytest.mark.asyncio
    async def test_cmd_start(self, setup_mocks):
        """Test the /start command handler."""
        message, state, api_client = setup_mocks
        
        # Импортируем модуль, где определена тестируемая функция
        import app.bot.handlers.user.basic_handlers as basic_handlers_module
        
        # Патчим все зависимости с помощью patch.object
        with patch.object(basic_handlers_module, 'get_api_client_from_bot', return_value=api_client), \
            patch.object(basic_handlers_module, 'logger'):
            
            # Вызываем тестируемую функцию
            await basic_handlers_module.cmd_start(message, state)
            
            # Проверяем, что API клиент был вызван для получения данных пользователя
            api_client.get_user_by_telegram_id.assert_called_once_with(message.from_user.id)
            
            # Проверяем, что был вызван API клиент для получения списка языков
            api_client.get_languages.assert_called_once()
            
            # Проверяем, что бот отправил ответное сообщение
            assert message.answer.called

    @pytest.mark.asyncio
    async def test_cmd_help(self, setup_mocks):
        """Test the /help command handler."""
        message, state, api_client = setup_mocks
        
        # Импортируем модуль, где определена тестируемая функция
        import app.bot.handlers.user.help_handlers as help_handlers_module
        
        # Патчим все зависимости с помощью patch.object
        with patch.object(help_handlers_module, 'get_api_client_from_bot', return_value=api_client), \
            patch.object(help_handlers_module, 'logger'):
            
            # Вызываем тестируемую функцию
            await help_handlers_module.cmd_help(message, state)
            
            # Проверяем, что state.clear был вызван
            assert state.clear.called
            
            # Проверяем, что API клиент был вызван для получения данных пользователя
            api_client.get_user_by_telegram_id.assert_called_once_with(message.from_user.id)
            
            # Проверяем, что бот отправил ответное сообщение
            assert message.answer.called
            # Проверяем, что сообщение содержит нужный текст
            answer_text = message.answer.call_args.args[0]
            assert "Справка по использованию бота" in answer_text

    @pytest.mark.asyncio
    async def test_cmd_settings(self, setup_mocks):
        """Test the /settings command handler."""
        message, state, api_client = setup_mocks
        
        # Устанавливаем данные состояния для теста
        state.get_data.return_value = {
            "start_word": 5,
            "skip_marked": True,
            "use_check_date": False,
            "current_language": {
                "id": "lang123", 
                "name_ru": "Английский", 
                "name_foreign": "English"
            }
        }
        
        # Создаем мок для клавиатуры
        mock_keyboard = MagicMock()
        
        # Импортируем модуль, где определена тестируемая функция
        import app.bot.handlers.user.settings_handlers as settings_handlers_module
        
        # Патчим все зависимости с помощью patch.object
        with patch.object(settings_handlers_module, 'get_api_client_from_bot', return_value=api_client), \
            patch.object(settings_handlers_module, 'logger'), \
            patch.object(settings_handlers_module, 'display_language_settings', AsyncMock()) as display_mock:
            
            # Вызываем тестируемую функцию
            await settings_handlers_module.cmd_settings(message, state)
            
            # Проверяем, что API клиент был вызван для получения данных пользователя
            api_client.get_user_by_telegram_id.assert_called_once_with(message.from_user.id)
            
            # Проверяем, что был вызван display_language_settings
            assert display_mock.called
            assert display_mock.call_args.args[0] == message
            assert display_mock.call_args.args[1] == state

    @pytest.mark.asyncio
    async def test_process_settings_start_word(self, setup_mocks, setup_callback_mock):
        """Test the process_settings_start_word callback handler."""
        _, state, _ = setup_mocks
        callback = setup_callback_mock
        
        # Импортируем модуль, где определена тестируемая функция
        import app.bot.handlers.user.settings_handlers as settings_handlers_module
        
        # Патчим все зависимости с помощью patch.object
        with patch.object(settings_handlers_module, 'logger'), \
            patch.object(settings_handlers_module, 'get_user_language_settings', AsyncMock(return_value={"start_word": 1})):
            
            # Вызываем тестируемую функцию
            await settings_handlers_module.process_settings_start_word(callback, state)
            
            # Проверяем, что состояние было изменено
            state.set_state.assert_called_once_with(settings_handlers_module.SettingsStates.waiting_start_word)
            
            # Проверяем, что бот отправил ответное сообщение
            assert callback.message.answer.called
            # Проверяем, что сообщение содержит информацию о текущем значении
            answer_text = callback.message.answer.call_args.args[0]
            assert "Введите номер слова" in answer_text
            
            # Проверяем, что было обновлено состояние с информацией о последнем callback
            state.update_data.assert_called_once_with(last_callback="settings_start_word")
            
            # Проверяем, что callback.answer был вызван
            assert callback.answer.called

    @pytest.mark.asyncio
    async def test_process_start_word_input_valid(self, setup_mocks):
        """Test the process_start_word_input handler with valid input."""
        message, state, api_client = setup_mocks
        
        # Устанавливаем текст сообщения
        message.text = "10"
        
        # Устанавливаем информацию о пользователе
        message.from_user.full_name = "Test User"
        
        # Устанавливаем существующие данные состояния
        state.get_data.return_value = {
            "skip_marked": True,
            "use_check_date": False,
            "current_language": {
                "id": "lang123",
                "name_ru": "Английский",
                "name_foreign": "English"
            }
        }
        
        # Импортируем модуль, где определена тестируемая функция
        import app.bot.handlers.user.settings_handlers as settings_handlers_module
        
        # Создаем моки для API ответов
        api_client.get_word_count_by_language.return_value = {
            "success": True,
            "status": 200,
            "result": {"count": 2000},
            "error": None
        }
        
        # Патчим все зависимости с помощью patch.object
        with patch.object(settings_handlers_module, 'logger'), \
            patch.object(settings_handlers_module, 'get_api_client_from_bot', return_value=api_client), \
            patch.object(settings_handlers_module, 'get_user_language_settings', AsyncMock(return_value={
                "start_word": 1,
                "skip_marked": True,
                "use_check_date": False
            })), \
            patch.object(settings_handlers_module, 'save_user_language_settings', AsyncMock(return_value=True)), \
            patch.object(settings_handlers_module, 'display_language_settings', AsyncMock()) as display_mock:
            
            # Вызываем тестируемую функцию
            await settings_handlers_module.process_start_word_input(message, state)
            
            # Проверяем, что состояние было обновлено с новым значением start_word
            state.update_data.assert_any_call(start_word=10)
            
            # Проверяем, что состояние было очищено
            assert state.set_state.called
            assert state.set_state.call_args.args[0] is None
            
            # Проверяем, что была вызвана функция display_language_settings для показа обновленных настроек
            assert display_mock.called
            assert display_mock.call_args.args[0] == message
            assert display_mock.call_args.args[1] == state
            assert "успешно обновлены" in display_mock.call_args.kwargs.get("prefix", "")

    @pytest.mark.asyncio
    async def test_process_start_word_input_invalid(self, setup_mocks):
        """Test the process_start_word_input handler with invalid input."""
        message, state, _ = setup_mocks
        
        # Устанавливаем неверный текст сообщения
        message.text = "not_a_number"
        
        # Устанавливаем информацию о пользователе
        message.from_user.full_name = "Test User"
        
        # Импортируем модуль, где определена тестируемая функция
        import app.bot.handlers.user.settings_handlers as settings_handlers_module
        
        # Патчим все зависимости с помощью patch.object
        with patch.object(settings_handlers_module, 'logger'):
            
            # Вызываем тестируемую функцию
            await settings_handlers_module.process_start_word_input(message, state)
            
            # Проверяем, что состояние не было обновлено
            state.update_data.assert_not_called()
            
            # Проверяем, что состояние не было изменено
            state.set_state.assert_not_called()
            
            # Проверяем, что бот отправил сообщение об ошибке
            assert message.answer.called
            answer_text = message.answer.call_args.args[0]
            assert "Некорректный ввод" in answer_text

    @pytest.mark.asyncio
    async def test_process_settings_toggle_skip_marked(self, setup_mocks, setup_callback_mock):
        """Test the process_settings_toggle_skip_marked callback handler."""
        _, state, _ = setup_mocks
        callback = setup_callback_mock
        
        # Устанавливаем существующие данные состояния
        state.get_data.return_value = {
            "start_word": 5,
            "skip_marked": False,
            "use_check_date": True,
            "current_language": {
                "id": "lang123",
                "name_ru": "Английский",
                "name_foreign": "English"
            }
        }
        
        # Импортируем модуль, где определена тестируемая функция
        import app.bot.handlers.user.settings_handlers as settings_handlers_module
        
        # Патчим все зависимости с помощью patch.object
        with patch.object(settings_handlers_module, 'logger'), \
            patch.object(settings_handlers_module, 'get_user_language_settings', AsyncMock(return_value={
                "start_word": 5,
                "skip_marked": False,
                "use_check_date": True
            })), \
            patch.object(settings_handlers_module, 'save_user_language_settings', AsyncMock(return_value=True)), \
            patch.object(settings_handlers_module, 'display_language_settings', AsyncMock()) as display_mock:
            
            # Вызываем тестируемую функцию
            await settings_handlers_module.process_settings_toggle_skip_marked(callback, state)
            
            # Проверяем, что была вызвана функция get_user_language_settings для получения текущих настроек
            assert settings_handlers_module.get_user_language_settings.called
            
            # Проверяем, что была вызвана функция save_user_language_settings с инвертированным значением skip_marked
            settings_arg = settings_handlers_module.save_user_language_settings.call_args.args[2]
            assert settings_arg["skip_marked"] is True
            
            # Проверяем, что состояние было обновлено
            state.update_data.assert_called_once_with(skip_marked=True)
            
            # Проверяем, что была вызвана функция display_language_settings для показа обновленных настроек
            assert display_mock.called
            assert display_mock.call_args.args[0] == callback
            assert display_mock.call_args.args[1] == state
            assert "успешно обновлены" in display_mock.call_args.kwargs.get("prefix", "")
            assert display_mock.call_args.kwargs.get("is_callback", False) is True
            
            # Проверяем, что callback.answer был вызван
            assert callback.answer.called

    @pytest.mark.asyncio
    async def test_process_settings_toggle_check_date(self, setup_mocks, setup_callback_mock):
        """Test the process_settings_toggle_check_date callback handler."""
        _, state, _ = setup_mocks
        callback = setup_callback_mock
        
        # Устанавливаем существующие данные состояния
        state.get_data.return_value = {
            "start_word": 5,
            "skip_marked": True,
            "use_check_date": True,
            "current_language": {
                "id": "lang123",
                "name_ru": "Английский",
                "name_foreign": "English"
            }
        }
        
        # Импортируем модуль, где определена тестируемая функция
        import app.bot.handlers.user.settings_handlers as settings_handlers_module
        
        # Патчим все зависимости с помощью patch.object
        with patch.object(settings_handlers_module, 'logger'), \
            patch.object(settings_handlers_module, 'get_user_language_settings', AsyncMock(return_value={
                "start_word": 5,
                "skip_marked": True,
                "use_check_date": True
            })), \
            patch.object(settings_handlers_module, 'save_user_language_settings', AsyncMock(return_value=True)), \
            patch.object(settings_handlers_module, 'display_language_settings', AsyncMock()) as display_mock:
            
            # Вызываем тестируемую функцию
            await settings_handlers_module.process_settings_toggle_check_date(callback, state)
            
            # Проверяем, что была вызвана функция get_user_language_settings для получения текущих настроек
            assert settings_handlers_module.get_user_language_settings.called
            
            # Проверяем, что была вызвана функция save_user_language_settings с инвертированным значением use_check_date
            settings_arg = settings_handlers_module.save_user_language_settings.call_args.args[2]
            assert settings_arg["use_check_date"] is False
            
            # Проверяем, что состояние было обновлено
            state.update_data.assert_called_once_with(use_check_date=False)
            
            # Проверяем, что была вызвана функция display_language_settings для показа обновленных настроек
            assert display_mock.called
            assert display_mock.call_args.args[0] == callback
            assert display_mock.call_args.args[1] == state
            assert "успешно обновлены" in display_mock.call_args.kwargs.get("prefix", "")
            assert display_mock.call_args.kwargs.get("is_callback", False) is True
            
            # Проверяем, что callback.answer был вызван
            assert callback.answer.called

    def test_register_handlers(self):
        """Test the register_handlers function."""
        # Создаем мок для диспетчера
        dp = MagicMock(spec=Dispatcher)
        dp.include_router = MagicMock()
        
        # Импортируем модуль, где определена тестируемая функция
        import app.bot.handlers.user_handlers as user_handlers_module
        
        # Вызываем тестируемую функцию
        user_handlers_module.register_handlers(dp)
        
        # Проверяем, что include_router был вызван с user_router
        dp.include_router.assert_called_once_with(user_handlers_module.user_router)
            
    @pytest.mark.asyncio
    async def test_cmd_stats(self, setup_mocks):
        """Test the /stats command handler."""
        message, state, api_client = setup_mocks
        
        # Настраиваем моки API ответов для этого теста, используя AsyncMock для асинхронных методов
        api_client.get_user_by_telegram_id = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [{"id": "user123"}],
            "error": None
        })
        
        api_client.get_languages = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": [
                {"id": "lang1", "name_ru": "Английский", "name_foreign": "English"}
            ],
            "error": None
        })
        
        # Этот метод должен быть AsyncMock, так как он вызывается с await
        api_client.get_word_count_by_language = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {"count": 1000},
            "error": None
        })
        
        api_client.get_user_progress = AsyncMock(return_value={
            "success": True,
            "status": 200,
            "result": {
                "language_id": "lang1",
                "language_name_ru": "Английский",
                "language_name_foreign": "English",
                "total_words": 1000,
                "words_studied": 50,
                "words_known": 30,
                "words_skipped": 20,
                "progress_percentage": 3.0,
                "last_study_date": "2023-04-15T12:30:45.123Z"
            },
            "error": None
        })
        
        # Импортируем модуль, где определена тестируемая функция
        import app.bot.handlers.user.stats_handlers as stats_handlers_module
        
        # Патчим все зависимости с помощью patch.object
        with patch.object(stats_handlers_module, 'get_api_client_from_bot', return_value=api_client), \
            patch.object(stats_handlers_module, 'logger'):
            
            # Вызываем тестируемую функцию
            await stats_handlers_module.cmd_stats(message, state)
            
            # Проверяем, что API клиент был вызван с правильными аргументами
            api_client.get_user_by_telegram_id.assert_called_once_with(message.from_user.id)
            api_client.get_languages.assert_called_once()
            api_client.get_word_count_by_language.assert_called_once_with("lang1")
            api_client.get_user_progress.assert_called_once()
            
            # Проверяем, что бот отправил ответное сообщение
            assert message.answer.called
            # Проверяем, что сообщение содержит информацию о статистике
            answer_text = message.answer.call_args.args[0]
            assert "Статистика" in answer_text
            assert "Английский" in answer_text
            