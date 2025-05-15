"""
Bot Test Framework - класс для определения сценария тестирования бота.
"""

from typing import Dict, List, Union, Callable, Any, Optional, Tuple
from .bot_actions import BotAction, CommandAction, MessageAction, CallbackAction, AssertionAction
from .bot_actions_keyboard import AssertKeyboardContains, AssertKeyboardNotContains, AssertKeyboardButtonCount
from .handlers_setup import setup_default_handlers
from .api_mock_setup import (
    setup_api_mock_for_common_scenarios,
    setup_api_mock_for_study_testing,
    setup_api_mock_for_error_testing
)


class BotTestScenario:
    """
    Класс для определения сценария тестирования бота
    """
    def __init__(self, name: str, handler_modules: List[str], user_id: int = 12345):
        self.name = name
        self.handler_modules = handler_modules
        self.user_id = user_id
        self.actions: List[BotAction] = []
        self.setup_api_mock = None
        self.setup_handlers = None
        self.use_auto_setup = True  # Флаг для автоматической настройки обработчиков
        
    def add_command(self, command: str, args: str = "", step_name: str = None) -> "BotTestScenario":
        """
        Добавляет команду в сценарий
        
        Args:
            command: Команда без слеша (например, "start", "help")
            args: Аргументы команды (опционально)
            step_name: Название шага для отчетов и отладки
        
        Returns:
            self для цепочки вызовов
        """
        self.actions.append(CommandAction(command, args))
        return self

    def add_message(self, text: str, step_name: str = None) -> "BotTestScenario":
        """
        Добавляет сообщение пользователя в сценарий
        
        Args:
            text: Текст сообщения
            step_name: Название шага для отчетов и отладки
        
        Returns:
            self для цепочки вызовов
        """
        self.actions.append(MessageAction(text))
        return self

    def add_callback(self, callback_data: str, step_name: str = None) -> "BotTestScenario":
        """
        Добавляет действие нажатия на кнопку в сценарий
        
        Args:
            callback_data: Данные callback
            step_name: Название шага для отчетов и отладки
        
        Returns:
            self для цепочки вызовов
        """
        self.actions.append(CallbackAction(callback_data))
        return self

    def assert_message_contains(self, text: str, position: int = -1, step_name: str = None) -> "BotTestScenario":
        """
        Добавляет проверку наличия текста в сообщении бота
        
        Args:
            text: Искомый текст
            position: Индекс сообщения (по умолчанию -1 - последнее сообщение)
            step_name: Название шага для отчетов и отладки
        
        Returns:
            self для цепочки вызовов
        """
        def assertion_func(context):
            # В BotTestContext сообщения хранятся в sent_messages
            if not context.sent_messages:
                print(f"not context.sent_messages")
                result = False
            
            try:
                if abs(position) <= len(context.sent_messages):
                    # sent_messages хранит кортежи (text, kwargs)
                    message_text = context.sent_messages[position][0]
                    result = (text in message_text)
                    if not result:
                        print(f"message_text = {message_text}")
                else:
                    # Если позиция выходит за пределы списка сообщений, проверяем последнее
                    result =(text in context.sent_messages[-1][0])
                    if not result:
                        print(f"context.sent_messages[-1][0] = {context.sent_messages[-1][0]}")
            except Exception as e:
                print(f"Ошибка при проверке сообщения: {e}")
                print(f"Позиция: {position}")
                print(f"Количество сообщений: {len(context.sent_messages)}")
                result = False

            return result
        
        step_info = f" [Шаг: {step_name}]" if step_name else ""
        error_message = f"Сообщение не содержит текст: '{text}'"
        self.actions.append(AssertionAction(assertion_func, error_message, step_info))
        return self

    def assert_state_contains(self, key: str, value: Any = None, step_name: str = None) -> "BotTestScenario":
        """
        Добавляет проверку наличия ключа и значения в состоянии FSM
        
        Args:
            key: Ключ в состоянии
            value: Ожидаемое значение
            step_name: Название шага для отчетов и отладки
        
        Returns:
            self для цепочки вызовов
        """
        def assertion_func(context):
            # проверяем состояние в истории
            if not context.state_history:
                return False
            
            # Получаем последнее состояние
            last_state = context.state_history[-1]
            if key not in last_state:
                return False
            
            # Для словарей проверяем только указанные ключи
            if isinstance(value, dict) and isinstance(last_state[key], dict):
                # Проверяем что все ключи и значения из value присутствуют в last_state[key]
                for sub_key, sub_value in value.items():
                    if sub_key not in last_state[key] or last_state[key][sub_key] != sub_value:
                        return False
                return True
            
            # Для остальных типов проверяем прямое равенство
            if  (value is None) or (value == 'None'):
                result = last_state[key] is None
            else:
                result = (last_state[key] == value)

            if not result:
                print(f"last_state = {last_state}")

            return result
        
        step_info = f" [Шаг: {step_name}]" if step_name else ""
        error_message = f"Состояние не содержит '{key}={value}'"
        self.actions.append(AssertionAction(assertion_func, error_message, step_info))
        return self

    def assert_keyboard_contains(self, button_text: str = None, callback_data: str = None, 
                               should_exist: bool = True, step_name: str = None) -> "BotTestScenario":
        """
        Добавляет проверку наличия кнопки в клавиатуре последнего сообщения
        
        Args:
            button_text: Текст кнопки
            callback_data: Данные callback для кнопки
            should_exist: True, если кнопка должна существовать, False - если не должна
            step_name: Название шага для отчетов и отладки
        
        Returns:
            self для цепочки вызовов
        """
        self.actions.append(AssertKeyboardContains(button_text, callback_data, should_exist, step_name))
        return self

    def assert_keyboard_not_contains(self, button_text: str = None, callback_data: str = None, 
                                   step_name: str = None) -> "BotTestScenario":
        """
        Добавляет проверку отсутствия кнопки в клавиатуре последнего сообщения
        
        Args:
            button_text: Текст кнопки
            callback_data: Данные callback для кнопки
            step_name: Название шага для отчетов и отладки
        
        Returns:
            self для цепочки вызовов
        """
        self.actions.append(AssertKeyboardNotContains(button_text, callback_data, step_name))
        return self

    def assert_keyboard_button_count(self, expected_count: int, step_name: str = None) -> "BotTestScenario":
        """
        Добавляет проверку количества кнопок в клавиатуре последнего сообщения
        
        Args:
            expected_count: Ожидаемое количество кнопок
            step_name: Название шага для отчетов и отладки
        
        Returns:
            self для цепочки вызовов
        """
        self.actions.append(AssertKeyboardButtonCount(expected_count, step_name))
        return self

    def with_api_mock(self, setup_func: Callable[["AsyncMock"], None]) -> "BotTestScenario":
        """
        Настраивает мок для API клиента
        """
        self.setup_api_mock = setup_func
        return self
    
    def with_common_api_mock(self) -> "BotTestScenario":
        """
        Настраивает стандартный мок для API клиента с типовыми сценариями
        """
        self.setup_api_mock = setup_api_mock_for_common_scenarios
        return self
    
    def with_study_api_mock(self) -> "BotTestScenario":
        """
        Настраивает мок для API клиента для тестирования функциональности изучения слов
        """
        self.setup_api_mock = setup_api_mock_for_study_testing
        return self
    
    def with_error_api_mock(self) -> "BotTestScenario":
        """
        Настраивает мок для API клиента для тестирования обработки ошибок
        """
        self.setup_api_mock = setup_api_mock_for_error_testing
        return self
    
    def with_handlers(self, setup_func: Callable[["BotTestContext"], None]) -> "BotTestScenario":
        """
        Задает функцию для настройки обработчиков
        """
        self.setup_handlers = setup_func
        return self
    
    def with_auto_setup(self, enabled: bool = True) -> "BotTestScenario":
        """
        Включает или выключает автоматическую настройку обработчиков
        """
        self.use_auto_setup = enabled
        return self

    async def execute(self) -> None:
        """
        Выполняет сценарий тестирования
        """
        # Импортируем BotTestContext здесь, чтобы избежать циклических импортов
        from .bot_test_context import BotTestContext
        
        # Создаем контекст тестирования
        context = BotTestContext(user_id=self.user_id)
        
        try:
            # Создаем и настраиваем мок для API клиента
            if self.setup_api_mock:
                from unittest.mock import AsyncMock
                api_client = AsyncMock()
                self.setup_api_mock(api_client)
                context.configure_api_client(api_client)
            
            # Загружаем обработчики
            from .handlers_setup import load_handlers_from_modules
            # print(self.handler_modules)
            await load_handlers_from_modules(context, self.handler_modules)
            
            # Автоматическая настройка обработчиков, если включена
            if self.use_auto_setup:
                setup_default_handlers(context, self.handler_modules)
            
            # Если есть пользовательская настройка обработчиков, вызываем ее
            if hasattr(self, 'setup_handlers') and self.setup_handlers:
                print("Вызываем пользовательскую настройку обработчиков")
                self.setup_handlers(context)
            
            # Выполняем все действия в сценарии
            for action in self.actions:
                await action.execute(context)
        finally:
            # Освобождаем ресурсы
            context.cleanup()