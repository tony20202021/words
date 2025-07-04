"""
Утилиты для настройки обработчиков в Bot Test Framework.
"""

import inspect
import importlib
import re
import os
import sys
from typing import List, Dict, Callable, Any, Optional
from unittest.mock import AsyncMock, MagicMock

from .handlers_utils import (
    print_handler_summary,
    collect_sub_routers,
    import_submodule_handlers,
    print_router_structure,
    print_api_structure,
    print_handlers_structure,
    _import_module,
    _find_command_handlers_from_decorators,
    _find_callback_handlers_from_decorators,
)

def setup_default_handlers(context: Any, handler_modules: Optional[List[str]] = None) -> None:
    """
    Функция для настройки обработчиков по умолчанию из указанных модулей.
    
    Args:
        context: Контекст тестирования BotTestContext
        handler_modules: Список путей к модулям с обработчиками
    """
    print("Настраиваем обработчики из указанных модулей")
    print(f"setup_default_handlers.handler_modules = {handler_modules}")
    
    # Если модули не указаны, пытаемся загрузить из main.py
    if not handler_modules:
        handler_modules = _get_handler_modules_from_main()
        print(f"setup_default_handlers.handler_modules = {handler_modules}")
    
    # Убедимся, что директория проекта в sys.path
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)
        print(f"Добавлен путь к проекту: {project_dir}")
    
    # Словари для хранения обработчиков
    command_handlers = {}
    callback_handlers = {}
    
    # Загружаем модули и собираем обработчики
    for module_path in handler_modules:
        print(f"setup_default_handlers.module_path = {module_path}")
        try:
            # Пробуем импортировать модуль
            module = _import_module(module_path)
            if not module:
                print(f"setup_default_handlers.module = {module}")
                continue
            
            # Также проверяем декораторы в исходном коде
            _find_command_handlers_from_decorators(module, command_handlers)
            _find_callback_handlers_from_decorators(module, callback_handlers)
                    
        except ImportError as e:
            print(f"Ошибка при импорте модуля {module_path}: {e}")
    
    # Устанавливаем обработчики в контекст
    context.command_handlers = command_handlers
    context.callback_handlers = callback_handlers
    
    # Важно: настраиваем API клиент непосредственно в боте
    if context.api_client:
        context.bot.api_client = context.api_client
        if hasattr(context, 'dispatcher') and context.dispatcher:
            context.dispatcher.api_client = context.api_client
    
    # Печатаем красивый вывод о зарегистрированных обработчиках
    print_handler_summary(command_handlers, callback_handlers, context.api_client)


def _get_handler_modules_from_main() -> List[str]:
    """
    Получает список модулей с обработчиками из main.py.
    
    Returns:
        Список строк с путями к модулям
    """
    handler_modules = []
    try:
        # Пытаемся импортировать модуль main.py
        main_module = _import_module("app.main")
        if main_module and hasattr(main_module, "HANDLER_MODULES"):
            # Преобразуем импортированные модули в пути к модулям
            handler_modules = [module.__name__ for module in main_module.HANDLER_MODULES]
            print(f"Найдено {len(handler_modules)} модулей в main.py: {handler_modules}")
    except Exception as e:
        print(f"Ошибка при получении списка модулей из main.py: {e}")
    
    return handler_modules


def _load_admin_submodules() -> List[Any]:
    """
    Загружает подмодули из каталога admin.
    
    Returns:
        Список загруженных модулей
    """
    modules = []
    
    # Путь к каталогу admin
    admin_dir = os.path.join('app', 'bot', 'handlers', 'admin')
    
    if os.path.exists(admin_dir) and os.path.isdir(admin_dir):
        for filename in os.listdir(admin_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                module_name = f'app.bot.handlers.admin.{filename[:-3]}'
                try:
                    module = _import_module(module_name)
                    if module:
                        modules.append(module)
                        print(f"Загружен подмодуль admin: {module_name}")
                except ImportError as e:
                    print(f"Не удалось импортировать модуль {module_name}: {e}")
    
    return modules


async def load_handlers_from_modules(context, module_paths: List[str]) -> None:
    """
    Загружает обработчики из указанных модулей
    
    Args:
        context: Контекст тестирования BotTestContext
        module_paths: Список путей к модулям с обработчиками
    """
    from .handlers_router import load_handlers_from_routers
    
    print("=== НАЧАЛО ЗАГРУЗКИ ОБРАБОТЧИКОВ ===")
    
    # Убедимся, что директория проекта в sys.path
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)
        print(f"Добавлен путь к проекту: {project_dir}")
    
    routers = []
    
    # Загружаем обработчики из роутеров
    await load_handlers_from_routers(context, module_paths, routers)
                
    # Создаем диспетчер для поиска обработчиков, если необходимо
    if context.dispatcher is None:
        context.dispatcher = MagicMock()
        context.dispatcher.sub_routers = routers
    
    # Сохраняем все найденные роутеры для последующего поиска обработчиков
    context.all_routers = routers
    print(f"Сохранено {len(routers)} роутеров для поиска обработчиков")
    
    # Отладочный вывод информации о роутерах и их обработчиках
    # print_router_structure(context)
    print_handlers_structure(context)
    print_api_structure(context)
    print_handler_summary(context.command_handlers, context.callback_handlers, context.api_client)
    
    print("=== КОНЕЦ ЗАГРУЗКИ ОБРАБОТЧИКОВ ===\n")