"""
Bot Test Framework - система для тестирования telegram-бота путем моделирования
последовательности команд и взаимодействий пользователя.
"""

# Импорт базовых классов действий
from .bot_actions import (
    BotAction, 
    CommandAction, 
    MessageAction, 
    CallbackAction, 
    AssertionAction
)

# Импорт классов действий для клавиатур
from .bot_actions_keyboard import (
    AssertKeyboardContains,
    AssertKeyboardNotContains,
    AssertKeyboardButtonCount
)

# Импорт основных компонентов фреймворка
from .bot_test_context import BotTestContext
from .bot_test_scenario import BotTestScenario
from .bot_test_framework import create_test_scenario, bot_test, get_default_handler_modules

# Импорт функций работы с обработчиками
from .handlers_setup import (
    setup_default_handlers,
    load_handlers_from_modules
)

# Импорт функций для настройки API клиента
from .api_mock_setup import (
    setup_api_mock_for_common_scenarios,
    setup_api_mock_for_study_testing,
    setup_api_mock_for_error_testing
)

# Импорт функций для работы со сценариями
from .scenario_executor import (
    execute_scenario_steps,
    load_scenario_from_dict,
    load_yaml_scenario
)

__all__ = [
    # Базовые классы действий
    'BotAction',
    'CommandAction',
    'MessageAction',
    'CallbackAction',
    'AssertionAction',
    
    # Классы действий для клавиатур
    'AssertKeyboardContains',
    'AssertKeyboardNotContains',
    'AssertKeyboardButtonCount',
    
    # Основные компоненты фреймворка
    'BotTestContext',
    'BotTestScenario',
    'create_test_scenario',
    'bot_test',
    'get_default_handler_modules',
    
    # Функции для работы с обработчиками
    'setup_default_handlers',
    'load_handlers_from_modules',
    
    # Функции для настройки API клиента
    'setup_api_mock_for_common_scenarios',
    'setup_api_mock_for_study_testing',
    'setup_api_mock_for_error_testing',
    
    # Функции для работы со сценариями
    'execute_scenario_steps',
    'load_scenario_from_dict',
    'load_yaml_scenario',
]