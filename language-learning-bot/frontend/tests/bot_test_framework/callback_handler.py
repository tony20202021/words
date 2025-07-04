"""
Обработчик callback-запросов для Bot Test Framework.
"""

import inspect
import importlib
import traceback
from unittest.mock import MagicMock, AsyncMock

from aiogram.types import CallbackQuery, Message


class CallbackHandler:
    """
    Класс для обработки callback-запросов в тестовом фреймворке.
    """
    def __init__(self, context):
        self.context = context
        
    async def trigger_callback(self, callback_data: str) -> None:
        """
        Вызывает обработчик для callback_query
        """
        print(f"\n=== ОБРАБОТКА CALLBACK {callback_data} ===")
        
        # Создаем объект callback_query
        callback = MagicMock(spec=CallbackQuery)
        callback.data = callback_data
        callback.from_user = self.context.user
        callback.bot = self.context.bot
        callback.bot.api_client = self.context.api_client
        callback.message = MagicMock(spec=Message)
        callback.message.chat = self.context.chat
        callback.message.bot = self.context.bot
        callback.message.bot.api_client = self.context.api_client
        callback.message.answer = AsyncMock()
        callback.message.edit_text = AsyncMock()
        callback.message.edit_reply_markup = AsyncMock()
        callback.answer = AsyncMock()
        
        # Запоминаем вызов для истории
        self.context.callback_history.append(callback_data)

        # Пробуем обработать callback
        handler_found = await self._process_callback(callback, callback_data)
        
        if not handler_found:
            print(f"ПРЕДУПРЕЖДЕНИЕ: Обработчик для callback с данными '{callback_data}' не найден!")
        
        # Сохраняем ответы от бота
        print("Ответы бота после callback:")
        for i, call in enumerate(callback.message.answer.call_args_list):
            args, kwargs = call
            self.context.sent_messages.append((args[0] if args else "", kwargs))
            print(f"  Ответ #{i}: {args[0] if args else ''}")

        for i, call in enumerate(callback.message.edit_text.call_args_list):
            args, kwargs = call
            self.context.sent_messages.append((args[0] if args else "", kwargs))
            print(f"  edit_text #{i}: {args[0] if args else ''}")

        # Обратите внимание, что здесь больше не нужно сохранять историю состояний
        # это делается автоматически в методах state.update_data и state.set_state
        print(f"Текущее состояние после callback: {self.context.state_data}")
        print(f"=== КОНЕЦ ОБРАБОТКИ CALLBACK ===\n")

    async def _process_callback(self, callback, callback_data):
        """
        Обработка callback запроса с поиском и вызовом обработчика.
        """
        handler_found = False
        
        if hasattr(self.context, 'callback_handlers') and callback_data in self.context.callback_handlers:
            handler = self.context.callback_handlers[callback_data]
            print(f"Найден обработчик из сохраненных callback_handlers: {handler}")
            try:
                await handler(callback, self.context.state)
                handler_found = True
            except Exception as e:
                print(f"Ошибка при вызове обработчика callback: {e}")
                traceback.print_exc()
                
        if not handler_found:
            # Ищем обработчики префиксов
            for handler_key, handler_func in self.context.callback_handlers.items():
                if handler_key.startswith("startswith:"):
                    prefix = handler_key.split(":", 1)[1]
                    if callback_data.startswith(prefix):
                        handler_found = True
                        print(f"Найден обработчик из сохраненных callback_handlers: {prefix} для callback {callback_data} с обработчиком {handler_key}")

                        try:
                            await handler_func(callback, self.context.state)
                        except Exception as e:
                            print(f"Ошибка при вызове обработчика callback: {e}")
                            traceback.print_exc()

        # Если прямой поиск не дал результатов, ищем обработчик через роутеры
        if not handler_found:
            handler_found = await self._find_and_call_handler_via_routers(callback, callback_data)
            
        # Если через роутеры не нашли, пробуем через импорт модулей
        if not handler_found:
            handler_found = await self._find_and_call_handler_via_import(callback, callback_data)
        
        return handler_found
        
    async def _find_and_call_handler_via_routers(self, callback, callback_data):
        """
        Поиск и вызов обработчика через диспетчер и роутеры.
        """
        handler_found = False
        
        print("Поиск обработчика для callback в диспетчере")
        if self.context.dispatcher:
            # В новых версиях aiogram структура изменилась
            for router in self.context.dispatcher.sub_routers:
                # print(f"Проверка sub_router: {router}")
                if hasattr(router, 'callback_query'):
                    # print(f"Проверка callback_query обработчиков: {router.callback_query}")
                    for handler_obj in router.callback_query.handlers:
                        # print(f"Проверка обработчика: {handler_obj}")
                        # Различные проверки фильтров
                        filter_match = self._check_callback_filter(handler_obj, callback, callback_data)
                        # print(f"Результат проверки фильтра: {filter_match}")
                        if filter_match:
                            handler = handler_obj.callback
                            print(f"Найден обработчик в диспетчере: {handler}")
                            try:
                                await handler(callback, self.context.state)
                                handler_found = True
                                break
                            except Exception as e:
                                print(f"Ошибка при вызове обработчика: {e}")
                                traceback.print_exc()
                    if handler_found:
                        break
    
        # Если не нашли в диспетчере, ищем в роутерах напрямую
        if not handler_found:
            print("Поиск обработчика в all_routers")
            for router in self.context.all_routers:
                # print(f"Проверка роутера из all_routers: {router}")
                if hasattr(router, 'callback_query'):
                    # print(f"Проверка callback_query обработчиков: {router.callback_query}")
                    for handler_obj in router.callback_query.handlers:
                        # print(f"Проверка обработчика: {handler_obj}")
                        # Различные проверки фильтров
                        filter_match = self._check_callback_filter(handler_obj, callback, callback_data)
                        # print(f"Результат проверки фильтра: {filter_match}")
                        if filter_match:
                            handler = handler_obj.callback
                            print(f"Найден обработчик в all_routers: {handler}")
                            try:
                                await handler(callback, self.context.state)
                                handler_found = True
                                break
                            except Exception as e:
                                print(f"Ошибка при вызове обработчика: {e}")
                                traceback.print_exc()
                    if handler_found:
                        break
                        
        return handler_found

    async def _find_and_call_handler_via_import(self, callback, callback_data):
        """
        Поиск и вызов обработчика через прямой импорт модулей.
        """
        handler_found = False
        
        print(f"Поиск обработчика для callback {callback_data} через прямой импорт модулей")
        try:
            for module_path in ["app.bot.handlers.user_handlers"]:
                module = importlib.import_module(module_path)
                
                # Ищем функции, которые могут обрабатывать этот callback
                potential_handlers = []
                for name, obj in inspect.getmembers(module):
                    if name.startswith('process_') and callable(obj):
                        potential_handlers.append((name, obj))
                
                print(f"Потенциальные обработчики: {potential_handlers}")
                
                # Пробуем искать точное соответствие имени обработчика и callback_data
                callback_name_match = f"process_{callback_data}"
                for name, potential_handler in potential_handlers:
                    if name == callback_name_match:
                        try:
                            print(f"Найдено точное соответствие имени: {name}")
                            await potential_handler(callback, self.context.state)
                            handler_found = True
                            print(f"Успешно обработано с помощью {name}")
                            break
                        except Exception as e:
                            print(f"Ошибка при вызове {name}: {e}")
                
                # Если точное соответствие не найдено, пробуем вызвать каждый потенциальный обработчик
                if not handler_found:
                    for name, potential_handler in potential_handlers:
                        try:
                            print(f"Пробуем вызвать {name}")
                            await potential_handler(callback, self.context.state)
                            handler_found = True
                            print(f"Успешно обработано с помощью {name}")
                            break
                        except Exception as e:
                            print(f"Ошибка при вызове {name}: {e}")
                
                if handler_found:
                    break
        except Exception as e:
            print(f"Ошибка при поиске обработчика callback через импорт: {e}")
            traceback.print_exc()
            
        return handler_found

    def _check_callback_filter(self, handler_obj, callback, callback_data):
        """
        Вспомогательная функция для проверки фильтров обработчиков callback'ов
        """
        handler_name = handler_obj.callback.__name__ if handler_obj and hasattr(handler_obj, 'callback') else "unknown"
        
        # Проверяем обработчики, зарегистрированные в callback_handlers
        if hasattr(self.context, 'callback_handlers'):
            # Прямая проверка на точное совпадение в callback_handlers
            if callback_data in self.context.callback_handlers:
                registered_handler = self.context.callback_handlers[callback_data]
                if registered_handler == handler_obj.callback:
                    print(f"Найден подходящий обработчик {handler_name} для точного совпадения: {callback_data}")
                    return True
                
            # Ищем обработчики префиксов
            for handler_key, handler_func in self.context.callback_handlers.items():
                if handler_key.startswith("startswith:"):
                    prefix = handler_key.split(":", 1)[1]
                    if callback_data.startswith(prefix) and handler_func == handler_obj.callback:
                        print(f"Найдено соответствие префиксу {prefix} для callback {callback_data} с обработчиком {handler_name}")
                        return True
        
        # Проверка фильтров в обработчике
        if hasattr(handler_obj, 'filters') and handler_obj.filters:
            for filter_obj in handler_obj.filters:
                # Проверка на F.data == "..."
                if hasattr(filter_obj, 'magic') and filter_obj.magic:
                    magic_str = str(filter_obj.magic)
                    
                    # 1. Проверка на точное совпадение F.data == "callback_data"
                    if f"'{callback_data}'" in magic_str or f'"{callback_data}"' in magic_str:
                        # Для точного совпадения необходимо проверить фактическое содержимое `data == "..."`
                        # с использованием регулярного выражения для исключения ложных срабатываний
                        import re
                        exact_match = re.search(r'data\s*==\s*[\'"]([^\'"]+)[\'"]', magic_str)
                        if exact_match and exact_match.group(1) == callback_data:
                            print(f"Совпадение по точному значению в magic для обработчика {handler_name}: {callback_data}")
                            return True
                    
                    # 2. Проверка F.data.startswith("prefix")
                    if 'startswith' in magic_str:
                        # Для обычного startswith с одним префиксом
                        import re
                        prefix_match = re.search(r'data\.startswith\([\'"]([^\'"]+)[\'"]\)', magic_str)
                        if prefix_match and callback_data.startswith(prefix_match.group(1)):
                            print(f"Совпадение по startswith в magic для обработчика {handler_name}: {prefix_match.group(1)}")
                            return True
                        
                        # 3. Проверка F.data.startswith(("prefix1", "prefix2", ...))
                        tuple_match = re.search(r'data\.startswith\(\(([^)]+)\)\)', magic_str)
                        if tuple_match:
                            prefixes_str = tuple_match.group(1)
                            prefix_matches = re.findall(r'[\'"]([^\'"]+)[\'"]', prefixes_str)
                            for prefix in prefix_matches:
                                if callback_data.startswith(prefix):
                                    print(f"Совпадение по префиксу {prefix} из кортежа для обработчика {handler_name}")
                                    return True
                
                # 4. Пробуем использовать метод resolve, если он доступен
                if hasattr(filter_obj, 'resolve'):
                    try:
                        # Убедимся, что у callback есть атрибут data
                        callback.data = callback_data
                        result = filter_obj.resolve(callback)
                        if result:
                            print(f"Совпадение через resolve для {callback_data} с обработчиком {handler_name}")
                            return True
                    except Exception as e:
                        print(f"Ошибка при вызове resolve для {handler_name}: {e}")
                        pass
                        
        return False