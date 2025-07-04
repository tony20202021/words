"""
Вспомогательные функции для настройки и анализа обработчиков в Bot Test Framework.
"""

import inspect
import importlib
import re
import traceback
from typing import Dict, Callable, Any, List
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command


def print_handler_summary(command_handlers, callback_handlers, api_client):
    """
    Выводит красивое сообщение о зарегистрированных обработчиках
    
    Args:
        command_handlers: Словарь обработчиков команд
        callback_handlers: Словарь обработчиков callback
        api_client: Ссылка на API клиент
    """
    command_count = len(command_handlers)
    callback_count = len(callback_handlers)
    
    print("\n" + "="*70)
    print(f"🤖 Зарегистрировано {command_count} обработчиков команд:")
    
    if command_count > 0:
        for i, (cmd, handler) in enumerate(sorted(command_handlers.items())):
            print(f"   {i+1}. /{cmd} → {handler.__name__}")
    else:
        print("   Нет зарегистрированных обработчиков команд")
    
    print("\n📱 Зарегистрировано {0} обработчиков callback:".format(callback_count))
    
    if callback_count > 0:
        for i, (callback_data, handler) in enumerate(sorted(callback_handlers.items())):
            if callback_data.startswith("startswith:"):
                prefix = callback_data.split(":", 1)[1]
                print(f"   {i+1}. {prefix}* → {handler.__name__} (префикс)")
            else:
                print(f"   {i+1}. {callback_data} → {handler.__name__}")
    else:
        print("   Нет зарегистрированных обработчиков callback")
    
    print("\n🌐 API клиент: " + ("✅ Установлен" if api_client else "❌ Не установлен"))
    print("="*70 + "\n")

def print_router_structure(context):
    """
    Расширенный отладочный вывод информации о диспетчере и роутерах
    с детальным анализом обработчиков и их фильтров
    """
    print("\n=== ПОДРОБНАЯ СТРУКТУРА РОУТЕРОВ ===")
    
    if not hasattr(context, 'all_routers') or not context.all_routers:
        print("Нет доступных роутеров для анализа!")
        return
    
    # Вывод структуры каждого роутера
    for i, router in enumerate(context.all_routers):
        router_name = getattr(router, 'name', f"Router#{i+1}")
        print(f"\n📌 Роутер #{i+1}: {router_name} ({router})")
        
        # Вывод обработчиков сообщений
        if hasattr(router, 'message') and hasattr(router.message, 'handlers'):
            handlers_count = len(router.message.handlers)
            print(f"  📨 Обработчики сообщений ({handlers_count}):")
            
            for j, handler in enumerate(router.message.handlers):
                handler_name = handler.callback.__name__ if hasattr(handler, 'callback') else "unknown"
                print(f"    💬 Обработчик #{j+1}: {handler_name}")
                
                # Вывод фильтров
                if hasattr(handler, 'filters') and handler.filters:
                    # print(f"      🔍 Фильтры ({len(handler.filters)}):")
                    for k, filter_obj in enumerate(handler.filters):
                        filter_type = filter_obj.__class__.__name__
                        # print(f"        • Фильтр #{k+1}: {filter_type}")
                        
                        # Специальная обработка для фильтра команд
                        if hasattr(filter_obj, 'commands'):
                            print(f"          🛠️ Команды: {', '.join(filter_obj.commands)}")
                
                        if hasattr(filter_obj, 'states'):
                            print(f"          🛠️ Состояния:")
                            for state in filter_obj.states:
                                print(f" - Group: {state.group.__name__}, name: {state.name}. State: {state.state}")

                        if hasattr(filter_obj, 'callback') and filter_obj.callback:
                            if isinstance(filter_obj.callback, Command):
                                print(f"\tкомандный фильтр: {filter_obj.callback.commands}")
                            elif isinstance(filter_obj.callback, State):
                                state = filter_obj.callback
                                state_name = state.state
                                print(f"\tобработчик для состояния {state_name}")

                # Вывод флагов (новый формат aiogram)
                if hasattr(handler, 'flags') and handler.flags:
                    print(f"      🏁 Флаги:")
                    for flag_name, flag_values in handler.flags.items():
                        print(f"        • {flag_name}: {flag_values}")
        
        # Вывод обработчиков callback-запросов
        if hasattr(router, 'callback_query') and hasattr(router.callback_query, 'handlers'):
            handlers_count = len(router.callback_query.handlers)
            print(f"\n  🔄 Обработчики callback-запросов ({handlers_count}):")
            
            for j, handler in enumerate(router.callback_query.handlers):
                handler_name = handler.callback.__name__ if hasattr(handler, 'callback') else "unknown"
                print(f"    ⚡ Обработчик #{j+1}: {handler_name}")
                
                # Вывод фильтров
                if hasattr(handler, 'filters') and handler.filters:
                    print(f"      🔍 Фильтры ({len(handler.filters)}):")
                    for k, filter_obj in enumerate(handler.filters):
                        filter_type = filter_obj.__class__.__name__
                        print(f"        • Фильтр #{k+1}: {filter_type}")
                        
                        # Вывод магического фильтра (F.data)
                        if hasattr(filter_obj, 'magic'):
                            print(f"          🔮 Magic: {filter_obj.magic}")
    
    # Итоговая статистика
    print(f"  📚 Всего роутеров: {len(context.all_routers)}")
    print("=== КОНЕЦ СТРУКТУРЫ РОУТЕРОВ ===\n")
    
def print_handlers_structure(context):
    # Выводим список найденных обработчиков команд

    print("\n📊 СТАТИСТИКА ОБРАБОТЧИКОВ:")

    command_count = len(context.command_handlers) if hasattr(context, 'command_handlers') else 0
    print(f"\n  🤖 Обработчики команд ({command_count}):")
    
    if command_count > 0:
        for i, (cmd, handler) in enumerate(sorted(context.command_handlers.items())):
            print(f"    {i+1}. /{cmd} → {handler.__name__}")
    else:
        print("    Нет зарегистрированных обработчиков команд")
    
    # Выводим список найденных обработчиков callback
    callback_count = len(context.callback_handlers) if hasattr(context, 'callback_handlers') else 0
    print(f"\n  📱 Обработчики callback ({callback_count}):")
    
    if callback_count > 0:
        for i, (callback_data, handler) in enumerate(sorted(context.callback_handlers.items())):
            if callback_data.startswith("startswith:"):
                prefix = callback_data.split(":", 1)[1]
                print(f"    {i+1}. {prefix}* → {handler.__name__} (префикс)")
            else:
                print(f"    {i+1}. {callback_data} → {handler.__name__}")
    else:
        print("    Нет зарегистрированных обработчиков callback")
    
    print("=== КОНЕЦ СТРУКТУРЫ обработчиков ===\n")

def print_api_structure(context):
    # Вывод API клиента
    api_status = "✅ Установлен" if context.api_client else "❌ Не установлен"
    print(f"\n  🌐 API клиент: {api_status}")
    

def collect_sub_routers(router, routers_list):
    """
    Рекурсивно собирает все подроутеры из роутера и добавляет их в список
    
    Args:
        router: Объект Router
        routers_list: Список для сохранения роутеров
    """
    if hasattr(router, 'sub_routers'):
        for sub_router in router.sub_routers:
            if sub_router not in routers_list:
                routers_list.append(sub_router)
                # print(f"Добавлен подроутер: {sub_router}")
                collect_sub_routers(sub_router, routers_list)
                
    # Дополнительная проверка через dir и getattr (для aiogram 3.x)
    for attr_name in dir(router):
        if attr_name == 'sub_routers':
            continue  # Уже обработали выше
        
        try:
            attr = getattr(router, attr_name)
            if isinstance(attr, router.__class__) and attr not in routers_list:
                routers_list.append(attr)
                # print(f"Добавлен подроутер через атрибут {attr_name}: {attr}")
                collect_sub_routers(attr, routers_list)
        except Exception:
            pass


def import_submodule_handlers(base_module_path, submodule_dir, routers_list):
    """
    Импортирует обработчики из подмодулей (например, study или admin)
    
    Args:
        base_module_path: Базовый путь модуля (например, 'app.bot.handlers')
        submodule_dir: Имя подкаталога с подмодулями ('study', 'admin')
        routers_list: Список для сохранения найденных роутеров
    """
    if not base_module_path.endswith(submodule_dir):
        try:
            # Формируем путь к каталогу с подмодулями
            submodule_path = f"{base_module_path}.{submodule_dir}"
            print(f"Пробуем импортировать подмодули из {submodule_path}")
            
            # Импортируем основной модуль подкаталога
            submodule = _import_module(submodule_path)
            
            # Ищем роутеры в модуле
            if submodule:
                for name, obj in inspect.getmembers(submodule):
                    if hasattr(obj, 'sub_routers') and obj not in routers_list:
                        routers_list.append(obj)
                        print(f"Найден Router в подмодуле {submodule_dir}: {name} = {obj}")
                        # Рекурсивно добавим все подроутеры
                        collect_sub_routers(obj, routers_list)
            
                # Проверяем, есть ли HANDLER_MODULES или другие списки модулей
                handler_modules = []
                if hasattr(submodule, 'HANDLER_MODULES'):
                    handler_modules = submodule.HANDLER_MODULES
                
                # Если не нашли HANDLER_MODULES, пробуем импортировать подмодули напрямую
                if not handler_modules:
                    # Импортируем все .py файлы из подкаталога
                    import os
                    import pkgutil
                    
                    try:
                        # Получаем путь к пакету
                        package_dir = os.path.dirname(submodule.__file__)
                        
                        # Импортируем все модули из пакета
                        for _, submodule_name, is_pkg in pkgutil.iter_modules([package_dir]):
                            if not is_pkg and not submodule_name.startswith('__'):
                                try:
                                    submodule_full_path = f"{submodule_path}.{submodule_name}"
                                    print(f"Импортируем подмодуль: {submodule_full_path}")
                                    
                                    # Импортируем подмодуль
                                    sub_module = _import_module(submodule_full_path)
                                    
                                    # Ищем роутеры в подмодуле
                                    if sub_module:
                                        for name, obj in inspect.getmembers(sub_module):
                                            if hasattr(obj, 'sub_routers') and obj not in routers_list:
                                                routers_list.append(obj)
                                                print(f"Найден Router в подмодуле {submodule_name}: {name} = {obj}")
                                                # Рекурсивно добавим все подроутеры
                                                collect_sub_routers(obj, routers_list)
                                except ImportError as e:
                                    print(f"Ошибка при импорте подмодуля {submodule_name}: {e}")
                    except (AttributeError, ImportError, ValueError) as e:
                        print(f"Ошибка при импорте подмодулей из {submodule_path}: {e}")
            
        except ImportError as e:
            print(f"Подмодуль {submodule_dir} не найден в {base_module_path}: {e}")


def _import_module(module_path: str):
    """
    Безопасный импорт модуля с обработкой ошибок.
    
    Args:
        module_path: Путь к модулю
        
    Returns:
        Импортированный модуль или None в случае ошибки
    """
    try:
        return importlib.import_module(module_path)
    except ImportError as e:
        print(f"Не удалось импортировать модуль {module_path}: {e}")
        return None


def _find_command_handlers_from_decorators(module, command_handlers: Dict[str, Callable]):
    """
    Ищет обработчики команд в декораторах модуля.
    
    Args:
        module: Модуль для анализа
        command_handlers: Словарь для заполнения {команда: обработчик}
    """
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
                for cmd in matches:
                    command_handlers[cmd] = obj
                    print(f"Найден обработчик команды (из декоратора): {name} для команды /{cmd}")
        except (TypeError, IOError):
            # Пропускаем, если не удается получить исходный код
            pass


def _find_callback_handlers_from_decorators(module, callback_handlers: Dict[str, Callable]):
    """
    Ищет обработчики callback в декораторах модуля.
    
    Args:
        module: Модуль для анализа
        callback_handlers: Словарь для заполнения {callback_data: обработчик}
    """
    # Ищем все функции в модуле
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        # Получаем исходный код функции
        try:
            func_source = inspect.getsource(obj)
            
            # 1. Ищем декораторы типа @router.callback_query(F.data == "settings_toggle_skip_marked")
            callback_pattern = r'@\w+\.callback_query\(.*?[F|f]\.data\s*==\s*(?:"|\')([^"\']+)(?:"|\')\)'
            
            # Ищем все совпадения паттерна перед определением функции
            matches = re.findall(callback_pattern, func_source)
            
            if matches:
                for callback_data in matches:
                    callback_handlers[callback_data] = obj
                    print(f"Найден обработчик callback (из декоратора ==): {name} для callback {callback_data}")
            
            # 1.5 Ищем декораторы типа 
            # @evaluation_router.callback_query(F.data == CallbackData.WORD_KNOW) # 2 слова разделенные точкой, заканчивается скобкой
            # @evaluation_router.callback_query(F.data == CallbackData.WORD_KNOW, StudyStates.studying) # 2 слова разделенные точкой, заканчивается запятой, дальше неважно
            callback_pattern = r'@\w+\.callback_query\([^)]*F\.data\s*==\s*([^,\)]*\.[^,\)]+)(?:\s*,\s*([^)]+))?\)'
            
            # Ищем все совпадения паттерна перед определением функции
            matches = re.findall(callback_pattern, func_source)
            
            if matches:
                for (callback_data, _) in matches:
                    callback_handlers[callback_data] = obj
                    print(f"Найден обработчик callback (из декоратора == *.*): {name} для callback {callback_data}")
            
            # 2. Ищем декораторы типа @router.callback_query(F.data.startswith("lang_select_"))
            startswith_pattern = r'@\w+\.callback_query\(.*?[F|f]\.data\.startswith\((?:"|\')([^"\']+)(?:"|\')\)'
            
            # Ищем все совпадения паттерна startswith
            matches = re.findall(startswith_pattern, func_source)
            
            if matches:
                for prefix in matches:
                    # Для обработчиков с startswith регистрируем специальное имя с префиксом
                    callback_handlers[f"startswith:{prefix}"] = obj
                    print(f"Найден обработчик callback (из декоратора startswith): {name} для префикса {prefix}")
            
            # 3. Ищем декораторы с несколькими вариантами F.data.startswith(("prefix1", "prefix2"))
            multi_startswith_pattern = r'@\w+\.callback_query\(.*?[F|f]\.data\.startswith\(\(([^)]+)\)\)\)'
            
            # Ищем все совпадения паттерна с несколькими префиксами
            matches = re.findall(multi_startswith_pattern, func_source)
            
            if matches:
                for prefixes_str in matches:
                    # Разбираем строку с префиксами (может содержать кавычки и запятые)
                    try:
                        # Используем регулярное выражение для извлечения строк в кавычках
                        prefix_matches = re.findall(r'(?:"|\')([^"\']+)(?:"|\')', prefixes_str)
                        for prefix in prefix_matches:
                            callback_handlers[f"startswith:{prefix}"] = obj
                            print(f"Найден обработчик callback (из декоратора multi-startswith): {name} для префикса {prefix}")
                    except Exception as e:
                        print(f"Ошибка при разборе мульти-префиксов: {e}")
            
        except (TypeError, IOError) as e:
            # Пропускаем, если не удается получить исходный код
            print(f"Ошибка при получении исходного кода для {name}: {e}")


def extract_command_handlers_from_router(router):
    """
    Извлекает обработчики команд из роутера.
    
    Args:
        router: Объект Router
        
    Returns:
        Словарь {команда: обработчик}
    """
    command_handlers = {}
    
    # Проверяем наличие обработчиков сообщений
    if hasattr(router, 'message') and hasattr(router.message, 'handlers'):
        for handler_obj in router.message.handlers:
            # Проверяем наличие фильтров
            if hasattr(handler_obj, 'filters') and handler_obj.filters:
                for filter_obj in handler_obj.filters:
                    # Проверяем на фильтр команд
                    if hasattr(filter_obj, 'commands') and filter_obj.commands:
                        # Если нашли команды, регистрируем обработчик для каждой команды
                        for command in filter_obj.commands:
                            command_handlers[command] = handler_obj.callback
                            print(f"Найден обработчик для команды /{command}: {handler_obj.callback.__name__}")
            
                    if hasattr(filter_obj, 'states') and filter_obj.states:
                        for state in filter_obj.states:
                            command_handlers[str(state)] = handler_obj.callback
                            print(f"Найден обработчик для состояния /{state}: {handler_obj.callback.__name__}")

            # Проверяем наличие флагов (новый формат aiogram)
            if hasattr(handler_obj, 'flags') and 'commands' in handler_obj.flags:
                for cmd_filter in handler_obj.flags['commands']:
                    if hasattr(cmd_filter, 'commands'):
                        for command in cmd_filter.commands:
                            command_handlers[command] = handler_obj.callback
                            print(f"Найден обработчик для команды /{command} (из флагов): {handler_obj.callback.__name__}")
    
    return command_handlers

def extract_callback_handlers_from_router(router):
    """
    Извлекает обработчики callback из роутера.
    
    Args:
        router: Объект Router
        
    Returns:
        Словарь {callback_data: обработчик}
    """
    callback_handlers = {}
    
    # Проверяем наличие обработчиков callback_query
    if hasattr(router, 'callback_query') and hasattr(router.callback_query, 'handlers'):
        for handler_obj in router.callback_query.handlers:
            # Получаем имя функции обработчика для отладки
            handler_name = handler_obj.callback.__name__ if hasattr(handler_obj, 'callback') else "unknown"
            
            # Проверяем наличие фильтров
            if hasattr(handler_obj, 'filters') and handler_obj.filters:
                for filter_obj in handler_obj.filters:
                    # Проверка на F.data == "..."
                    if hasattr(filter_obj, 'magic') and filter_obj.magic:
                        magic_str = str(filter_obj.magic)
                        
                        # 1. Проверка на точное совпадение F.data == "callback_data"
                        import re
                        exact_match = re.search(r'data\s*==\s*[\'"]([^\'"]+)[\'"]', magic_str)
                        if exact_match:
                            callback_data = exact_match.group(1)
                            callback_handlers[callback_data] = handler_obj.callback
                            print(f"Найден обработчик для callback_data '{callback_data}': {handler_name}")
                        
                        # 2. Проверка F.data.startswith("prefix")
                        if 'startswith' in magic_str:
                            prefix_match = re.search(r'data\.startswith\([\'"]([^\'"]+)[\'"]\)', magic_str)
                            if prefix_match:
                                prefix = prefix_match.group(1)
                                callback_handlers[f"startswith:{prefix}"] = handler_obj.callback
                                print(f"Найден обработчик для префикса '{prefix}': {handler_name}")
                            
                            # 3. Проверка F.data.startswith(("prefix1", "prefix2", ...))
                            tuple_match = re.search(r'data\.startswith\(\(([^)]+)\)\)', magic_str)
                            if tuple_match:
                                prefixes_str = tuple_match.group(1)
                                prefix_matches = re.findall(r'[\'"]([^\'"]+)[\'"]', prefixes_str)
                                for prefix in prefix_matches:
                                    callback_handlers[f"startswith:{prefix}"] = handler_obj.callback
                                    print(f"Найден обработчик для префикса '{prefix}' из кортежа: {handler_name}")
                
    return callback_handlers
