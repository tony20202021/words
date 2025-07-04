"""
Unit test for checking if all bot commands have corresponding handlers.
"""

import pytest
import inspect
import re
import importlib
import sys
from types import ModuleType
import ast
from unittest.mock import MagicMock

class MockContextManager:
    """Мок контекстного менеджера для Hydra initialize"""
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

# Создаем мок объект конфигурации
mock_config = MagicMock()
mock_config.logging.level = "INFO"
mock_config.logging.format = None
mock_config.logging.log_dir = "logs"

# Патчим Hydra перед импортом модулей
with pytest.MonkeyPatch().context() as mp:
    # Правильный патч - возвращаем контекстный менеджер
    mp.setattr('hydra.initialize', lambda **kwargs: MockContextManager())
    mp.setattr('hydra.compose', lambda **kwargs: mock_config)
    
    # Также патчим config_holder, чтобы избежать проблем
    import app.utils.config_holder
    mp.setattr(app.utils.config_holder, 'cfg', mock_config)
    
    # Импортируем списки команд и модулей
    from app.bot.bot import BOT_COMMANDS
    from app.main_frontend import HANDLER_MODULES


def get_command_decorators(module):
    """
    Получает список декораторов команд в модуле путем анализа исходного кода.
    
    Args:
        module: Модуль для анализа
    
    Returns:
        Словарь {функция: [список_команд]}
    """
    # Словарь для хранения {функция: [список_команд]}
    command_decorators = {}
    
    # Ищем все функции в модуле
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        # Получаем исходный код функции
        try:
            func_source = inspect.getsource(obj)
            
            # Ищем декораторы перед определением функции
            # Ищем строки вида @router.message(Command("command_name"))
            # или @admin_router.message(Command("command_name"))
            decorator_pattern = r'@\w+\.message\(Command\((?:"|\')([^"\']+)(?:"|\')\)\)'
            
            # Ищем все совпадения паттерна перед определением функции
            matches = re.findall(decorator_pattern, func_source)
            
            if matches:
                command_decorators[obj] = matches
        except (TypeError, IOError):
            # Пропускаем, если не удается получить исходный код
            pass
    
    return command_decorators


def find_imports_in_source(source_code):
    """
    Анализирует исходный код модуля для поиска импортов, 
    начинающихся с 'app.bot.handlers'.
    
    Args:
        source_code: Исходный код модуля
    
    Returns:
        Список импортированных модулей
    """
    imports = []
    
    try:
        # Парсим исходный код модуля
        tree = ast.parse(source_code)
        
        # Ищем все импорты
        for node in ast.walk(tree):
            # Обработка 'from X import Y'
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith('app.bot.handlers'):
                    imports.append(node.module)
            
            # Обработка 'import X'
            elif isinstance(node, ast.Import):
                for name in node.names:
                    if name.name.startswith('app.bot.handlers'):
                        imports.append(name.name)
    
    except SyntaxError:
        # Пропускаем, если код не может быть распарсен
        pass
    
    return imports


def load_handler_module(module_name):
    """
    Загружает модуль по имени.
    
    Args:
        module_name: Имя модуля для загрузки
    
    Returns:
        Загруженный модуль или None в случае ошибки
    """
    try:
        return importlib.import_module(module_name)
    except ImportError as e:
        print(f"Не удалось импортировать модуль {module_name}: {e}")
        return None


def get_all_handler_modules(base_modules, processed_modules=None):
    """
    Рекурсивно находит все модули обработчиков, включая импортированные модули.
    
    Args:
        base_modules: Список базовых модулей
        processed_modules: Множество уже обработанных модулей (для избежания циклов)
    
    Returns:
        Список всех найденных модулей обработчиков
    """
    if processed_modules is None:
        processed_modules = set()
    
    result = []
    
    for module in base_modules:
        if module in processed_modules:
            continue
        
        processed_modules.add(module)
        result.append(module)
        
        try:
            # Получаем исходный код модуля
            source_code = inspect.getsource(module)
            
            # Находим все импорты модулей
            imported_modules = find_imports_in_source(source_code)
            
            # Загружаем и добавляем найденные модули
            for module_name in imported_modules:
                imported_module = load_handler_module(module_name)
                if imported_module and imported_module not in processed_modules:
                    new_modules = get_all_handler_modules([imported_module], processed_modules)
                    result.extend(new_modules)
        
        except (TypeError, OSError):
            # Пропускаем, если не удается получить исходный код
            pass
    
    return result


def test_all_commands_have_handlers():
    """Проверка, что все команды имеют обработчики."""
    # Получаем список команд
    commands = [cmd["command"] for cmd in BOT_COMMANDS]
    
    # Проверяем, что список команд не пустой
    assert len(commands) > 0, "Список команд пуст"
    
    # Список для хранения найденных команд
    command_handlers = []
    
    # Получаем все модули обработчиков
    all_modules = get_all_handler_modules(HANDLER_MODULES)
    
    # Проверяем наличие обработчиков в каждом модуле
    for module in all_modules:
        # Получаем список декораторов команд в модуле
        command_decorators = get_command_decorators(module)
        
        # Собираем все команды из декораторов
        for func, cmds in command_decorators.items():
            command_handlers.extend(cmds)
    
    # Выводим отладочную информацию
    print(f"Найдено {len(all_modules)} модулей обработчиков")
    print(f"Найдено {len(command_handlers)} обработчиков команд: {', '.join(command_handlers)}")
    
    # Проверяем, что все ожидаемые команды найдены
    for cmd in commands:
        print(cmd)
        assert cmd in command_handlers, f"Команда /{cmd} не найдена среди декораторов"