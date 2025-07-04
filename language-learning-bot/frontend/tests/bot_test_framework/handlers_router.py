"""
Функции для работы с роутерами и обработчиками в Bot Test Framework.
"""

import inspect
import traceback
from typing import List
from unittest.mock import MagicMock
from aiogram import Router

from .handlers_utils import (
    _import_module,
    collect_sub_routers,
    import_submodule_handlers,
    extract_command_handlers_from_router,
    extract_callback_handlers_from_router
)


async def load_handlers_from_routers(context, module_paths: List[str], routers: List) -> None:
    """
    Загружает обработчики из роутеров в указанных модулях.
    
    Args:
        context: Контекст тестирования
        module_paths: Список путей к модулям с обработчиками
        routers: Список для сохранения найденных роутеров
    """
    for module_path in module_paths:
        try:
            # Загружаем модуль
            print(f"Загрузка модуля: {module_path}")
            module = _import_module(module_path)
            
            if not module:
                continue
            
            # Ищем роутеры в модуле (напрямую в модуле, а не только в register_handlers)
            for name, obj in inspect.getmembers(module):
                # Ищем роутеры в модуле
                if isinstance(obj, Router) and hasattr(obj, 'sub_routers') and (obj not in routers):
                    routers.append(obj)
                    print(f"\tНайден Router в модуле {module}: {name} = {obj}")
                    
                    # Рекурсивно добавим все подроутеры
                    collect_sub_routers(obj, routers)
                            
            # Инициализируем словари обработчиков, если они еще не существуют
            if not hasattr(context, 'command_handlers'):
                context.command_handlers = {}
            if not hasattr(context, 'callback_handlers'):
                context.callback_handlers = {}
                    
            # Ищем функцию register_handlers
            register_func = None
            for name, obj in inspect.getmembers(module):
                if name == "register_handlers" and callable(obj):
                    register_func = obj
                    print(f"Найдена функция register_handlers: {register_func}")
                    break
            
            # Если нашли register_handlers, мокируем диспетчер и вызываем функцию
            if register_func:
                # Создаем мок-диспетчер с возможностью сбора роутеров
                mock_dispatcher = MagicMock()
                collected_routers = []
                
                # Определяем функцию-коллбэк для include_router, чтобы сохранять роутеры
                def mock_include_router(router):
                    print(f"Мок диспетчера: include_router вызван с роутером {router}")
                    if router not in collected_routers:
                        collected_routers.append(router)
                        # Добавляем этот роутер в общий список, если его там еще нет
                        if router not in routers:
                            routers.append(router)
                            print(f"Добавлен роутер из register_handlers: {router}")
                        
                        # Рекурсивно добавим все подроутеры
                        collect_sub_routers(router, routers)
                    return mock_dispatcher  # Возвращаем сам диспетчер для цепочки вызовов
                
                # Настраиваем мок
                mock_dispatcher.include_router = MagicMock(side_effect=mock_include_router)
                
                try:
                    # Проверяем сигнатуру функции register_handlers
                    sig = inspect.signature(register_func)
                    if len(sig.parameters) > 0:
                        # Вызываем функцию register_handlers с моком диспетчера
                        register_func(mock_dispatcher)
                    else:
                        # Если функция не принимает аргументов, просто вызываем её
                        register_func()
                    
                except Exception as e:
                    print(f"Ошибка при вызове register_handlers: {e}")
                    traceback.print_exc()
            
        except ImportError as e:
            print(f"Не удалось импортировать модуль {module_path}: {e}")
            
    # Заполняем command_handlers и callback_handlers на основе найденных роутеров
    print(f"Извлечение обработчиков из {len(routers)} найденных роутеров")
    
    for router in routers:
        # Извлекаем обработчики команд
        command_handlers = extract_command_handlers_from_router(router)
        if command_handlers:
            context.command_handlers.update(command_handlers)
            
        # Извлекаем обработчики callback
        callback_handlers = extract_callback_handlers_from_router(router)
        if callback_handlers:
            context.callback_handlers.update(callback_handlers)
            
    # Выводим статистику найденных обработчиков
    print(f"Найдено обработчиков команд: {len(context.command_handlers)}")
    print(f"Найдено обработчиков callback: {len(context.callback_handlers)}")
                
