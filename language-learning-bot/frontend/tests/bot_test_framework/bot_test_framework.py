"""
Bot Test Framework - система для тестирования telegram-бота путем моделирования
последовательности команд и взаимодействий пользователя.
"""

import sys
import os
import importlib
import ast
import inspect
from typing import List, Optional, Any, Set

from .bot_actions import BotAction, CommandAction, MessageAction, CallbackAction, AssertionAction
from .bot_test_context import BotTestContext
from .bot_test_scenario import BotTestScenario


def get_default_handler_modules() -> List[str]:
    """
    Получает список модулей с обработчиками из main.py.
    Рекурсивно находит все импортированные модули, начинающиеся с 'app.bot.handlers'.
    
    Returns:
        Список строк с путями к модулям (пустой список, если модули не найдены)
    """
    import ast
    import inspect
    import importlib
    import os
    import sys
    from typing import List, Set, Any
    
    handler_modules = []
    modules_to_process = []
    processed_modules = set()
    
    def find_imports_in_source(source_code: str) -> List[str]:
        """
        Анализирует исходный код модуля для поиска импортов, начинающихся с 'app.bot.handlers'.
        
        Args:
            source_code: Исходный код модуля
            
        Returns:
            Список путей к импортированным модулям
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
    
    def process_module(module_path: str) -> None:
        """
        Обрабатывает модуль, добавляя его и все его импорты в список.
        
        Args:
            module_path: Путь к модулю
        """
        if module_path in processed_modules:
            return
        
        processed_modules.add(module_path)
        
        if module_path not in handler_modules:
            handler_modules.append(module_path)
        
        try:
            # Пытаемся импортировать модуль
            module = importlib.import_module(module_path)
            
            # Получаем исходный код модуля
            try:
                source_code = inspect.getsource(module)
                
                # Находим все импорты модулей
                imported_modules = find_imports_in_source(source_code)
                
                # Добавляем найденные модули для обработки
                for imported_module in imported_modules:
                    if imported_module not in processed_modules:
                        modules_to_process.append(imported_module)
            
            except (TypeError, OSError) as e:
                print(f"Не удалось получить исходный код для {module_path}: {e}")
                pass
            
        except ImportError as e:
            print(f"Не удалось импортировать модуль {module_path}: {e}")
            pass
    
    def get_module_path(module: Any) -> str:
        """
        Получает путь к модулю из объекта модуля или строки.
        
        Args:
            module: Объект модуля или строка с путем к модулю
            
        Returns:
            Строка с путем к модулю
        """
        if isinstance(module, str):
            return module
        elif hasattr(module, '__name__'):
            return module.__name__
        else:
            return str(module)
    
    try:
        # Убедимся, что директория проекта в sys.path
        project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if project_dir not in sys.path:
            sys.path.insert(0, project_dir)
            print(f"Добавлен путь к проекту: {project_dir}")
            
        # Пытаемся импортировать модуль main.py
        try:
            main_module = importlib.import_module("app.main_frontend")
            if main_module and hasattr(main_module, "HANDLER_MODULES"):
                # Преобразуем импортированные модули в пути к модулям
                for module in main_module.HANDLER_MODULES:
                    module_path = get_module_path(module)
                    modules_to_process.append(module_path)
                print(f"Получено {len(modules_to_process)} начальных модулей из main_frontend.py: {main_module.HANDLER_MODULES}")
            else:
                print("Модуль main_frontend.py не содержит HANDLER_MODULES")
                
        except ImportError:
            # Пробуем импортировать старое имя модуля
            try:
                main_module = importlib.import_module("app.main")
                if main_module and hasattr(main_module, "HANDLER_MODULES"):
                    # Преобразуем импортированные модули в пути к модулям
                    for module in main_module.HANDLER_MODULES:
                        module_path = get_module_path(module)
                        modules_to_process.append(module_path)
                    print(f"Получено {len(modules_to_process)} начальных модулей из main.py: {main_module.HANDLER_MODULES}")
                else:
                    print("Модуль main.py не содержит HANDLER_MODULES")
            except ImportError:
                print("Не удалось импортировать ни main_frontend.py, ни main.py")
                
    except Exception as e:
        print(f"Ошибка при получении списка модулей: {e}")
    
    # Если список модулей пуст, возможно main.py не имеет атрибута HANDLER_MODULES
    # Попробуем найти базовые модули handlers с типичными именами
    if not modules_to_process:
        print("Пробуем найти стандартные модули обработчиков")
        base_modules = []
        for module_path in base_modules:
            try:
                # Проверяем, можно ли импортировать модуль
                importlib.import_module(module_path)
                modules_to_process.append(module_path)
                print(f"Найден стандартный модуль: {module_path}")
            except ImportError:
                # Пропускаем модули, которые не удается импортировать
                pass
    
    # Обрабатываем найденные модули
    while modules_to_process:
        module_path = modules_to_process.pop(0)
        process_module(module_path)
    
    if handler_modules:
        print(f"Найдено {len(handler_modules)} модулей с обработчиками: {handler_modules}")
    else:
        print("Не найдено модулей с обработчиками!")
    
    return handler_modules


def create_test_scenario(name: str, handler_modules: Optional[List[str]] = None, user_id: int = 12345):
    """
    Создает экземпляр тестового сценария с автоматическим определением handler_modules.
    
    Args:
        name: Название сценария
        handler_modules: Список модулей с обработчиками (если None, определяется автоматически)
        user_id: ID пользователя для теста
        
    Returns:
        Экземпляр BotTestScenario
    """
    # Если handler_modules не указан, используем значение по умолчанию
    if handler_modules is None:
        handler_modules = get_default_handler_modules()
        
        if not handler_modules:
            print("ПРЕДУПРЕЖДЕНИЕ: Не найдены модули с обработчиками. Тесты могут работать некорректно.")
        else:
            print(f"Используются автоматически определенные модули: {handler_modules}")
        
    return BotTestScenario(name, handler_modules, user_id)

# Определяем bot_test как синоним create_test_scenario для обратной совместимости
bot_test = create_test_scenario