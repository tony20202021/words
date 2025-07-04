"""
Обработчик сообщений для Bot Test Framework.
"""

import inspect
import importlib
import traceback
from unittest.mock import MagicMock, AsyncMock

from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup


class MessageHandler:
    """
    Класс для обработки обычных сообщений (не команд) в тестовом фреймворке.
    """
    def __init__(self, context):
        self.context = context
    
    async def send_message(self, text: str) -> None:
        """
        Отправляет обычное сообщение (не команду)
        """
        print(f"\n=== ОТПРАВКА СООБЩЕНИЯ: {text} ===")
        
        # Подготавливаем объект сообщения
        message = MagicMock(spec=Message)
        message.text = text
        message.from_user = self.context.user
        message.chat = self.context.chat
        message.bot = self.context.bot
        # Убедимся, что API клиент доступен
        message.bot.api_client = self.context.api_client
        
        message.voice = None  # или MagicMock() если нужен более сложный объект

        # Моки для методов сообщения
        message.answer = AsyncMock()
        message.reply = AsyncMock()
        
        # Находим обработчик для текущего состояния
        current_state = self.context.state_data.get("_state", None)
        print(f"Текущее состояние: {current_state}")
        handler_found = False
        
        # Поиск обработчика в диспетчере и роутерах
        handler_found = await self._find_and_call_message_handler(message, current_state)
        
        # Если обработчик так и не найден, выводим предупреждение
        if not handler_found:
            print(f"ПРЕДУПРЕЖДЕНИЕ: Обработчик для сообщения '{text}' в состоянии {current_state} не найден!")
        
        # Сохраняем ответы от бота
        print("Ответы бота после сообщения:")
        for i, call in enumerate(message.answer.call_args_list):
            args, kwargs = call
            self.context.sent_messages.append((args[0] if args else "", kwargs))
            print(f"  Ответ #{i}: {args[0] if args else ''}")
        
        for i, call in enumerate(message.edit_text.call_args_list):
            args, kwargs = call
            self.context.sent_messages.append((args[0] if args else "", kwargs))
            print(f"  edit_text #{i}: {args[0] if args else ''}")
        
        # Обратите внимание, что здесь больше не нужно сохранять историю состояний
        # это делается автоматически в методах state.update_data и state.set_state
        print(f"Текущее состояние после сообщения: {self.context.state_data}")
        print(f"=== КОНЕЦ ОБРАБОТКИ СООБЩЕНИЯ ===\n")
        
    async def _find_and_call_message_handler(self, message, current_state):
        """
        Поиск и вызов обработчика для сообщения в заданном состоянии.
        """
        handler_found = False
        
        if self.context.dispatcher:
            # Ищем в sub_routers диспетчера
            for router in self.context.dispatcher.sub_routers:
                if hasattr(router, 'message'):
                    for handler_obj in router.message.handlers:
                        # Проверка состояния или других фильтров
                        # print(f"Проверка обработчика: {handler_obj}")

                        # Пропускаем обработчики команд для обычных сообщений
                        if hasattr(handler_obj, 'flags') and 'commands' in handler_obj.flags and not message.text.startswith('/'):
                            # print(f"Пропускаем обработчик команды {handler_obj.callback} для обычного сообщения")
                            continue

                        filter_match = self._can_handle_message(handler_obj, message, current_state)
                        # print(f"Результат проверки фильтра: {filter_match}")
                        if filter_match:
                            handler = handler_obj.callback
                            print(f"Найден обработчик сообщения в диспетчере: {handler}")
                            try:
                                await handler(message, self.context.state)
                                handler_found = True
                                break
                            except Exception as e:
                                print(f"Ошибка при вызове обработчика: {e}")
                                traceback.print_exc()
                    if handler_found:
                        break
            
            # Если не нашли подходящий обработчик, пробуем в роутерах напрямую
            if not handler_found:
                print("Поиск обработчика в all_routers")
                for router in self.context.all_routers:
                    if hasattr(router, 'message'):
                        for handler_obj in router.message.handlers:
                            # Проверка состояния или других фильтров
                            # print(f"Проверка обработчика: {handler_obj}")

                            # Пропускаем обработчики команд для обычных сообщений
                            if hasattr(handler_obj, 'flags') and 'commands' in handler_obj.flags and not message.text.startswith('/'):
                                # print(f"Пропускаем обработчик команды {handler_obj.callback} для обычного сообщения")
                                continue

                            filter_match = self._can_handle_message(handler_obj, message, current_state)
                            # print(f"Результат проверки фильтра: {filter_match}")
                            if filter_match:
                                handler = handler_obj.callback
                                print(f"Найден обработчик сообщения в all_routers: {handler}")
                                try:
                                    await handler(message, self.context.state)
                                    handler_found = True
                                    break
                                except Exception as e:
                                    print(f"Ошибка при вызове обработчика: {e}")
                                    traceback.print_exc()
                        if handler_found:
                            break
            
            # Если все еще не нашли, ищем обработчики без фильтров состояния
            if not handler_found:
                for router in self.context.all_routers:
                    if hasattr(router, 'message'):
                        for handler_obj in router.message.handlers:
                            if not hasattr(handler_obj, 'filters') or not handler_obj.filters:
                                handler = handler_obj.callback
                                print(f"Найден обработчик без фильтров: {handler}")
                                try:
                                    await handler(message, self.context.state)
                                    handler_found = True
                                    break
                                except Exception as e:
                                    print(f"Ошибка при вызове обработчика: {e}")
                                    traceback.print_exc()
                        if handler_found:
                            break
        
        # Если все еще не нашли, пробуем импортировать обработчик напрямую
        if not handler_found:
            print(f"Поиск обработчика для сообщения в состоянии {current_state} через прямой импорт")
            try:
                for module_path in ["app.bot.handlers.user_handlers"]:
                    module = importlib.import_module(module_path)
                    # Если мы в состоянии ожидания начального слова, ищем обработчик process_start_word_input
                    if current_state and "waiting_start_word" in current_state:
                        handler_name = "process_start_word_input"
                        if hasattr(module, handler_name):
                            handler = getattr(module, handler_name)
                            print(f"Найден обработчик для ввода начального слова: {handler}")
                            try:
                                await handler(message, self.context.state)
                                handler_found = True
                                break
                            except Exception as e:
                                print(f"Ошибка при вызове обработчика {handler_name}: {e}")
                                traceback.print_exc()
                    
                    # Если не нашли специальный обработчик, ищем общие
                    if not handler_found:
                        # Ищем функции, которые могут обрабатывать это сообщение
                        potential_handlers = []
                        for name, obj in inspect.getmembers(module):
                            if name.startswith('process_') and callable(obj):
                                potential_handlers.append((name, obj))
                        
                        print(f"Потенциальные обработчики: {potential_handlers}")
                        
                        # Пробуем вызвать каждый потенциальный обработчик
                        for name, potential_handler in potential_handlers:
                            try:
                                print(f"Пробуем вызвать {name}")
                                await potential_handler(message, self.context.state)
                                handler_found = True
                                print(f"Успешно обработано с помощью {name}")
                                break
                            except Exception as e:
                                print(f"Ошибка при вызове {name}: {e}")
                    
                    if handler_found:
                        break
            except Exception as e:
                print(f"Ошибка при поиске обработчика через импорт: {e}")
                traceback.print_exc()
                
        return handler_found
            
    def _can_handle_message(self, handler_obj, message, current_state):
        """
        Проверяет, может ли обработчик обработать сообщение
        с учетом текущего состояния
        """
        # Если это обработчик команды, а сообщение не команда, то не подходит
        if hasattr(handler_obj, 'flags') and 'commands' in handler_obj.flags and not message.text.startswith('/'):
            return False
            
        # Проверяем фильтры состояния
        if hasattr(handler_obj, 'filters') and handler_obj.filters:
            for filter_obj in handler_obj.filters:
                # Для фильтра состояния проверяем соответствие текущему состоянию
                if hasattr(filter_obj, 'state'):
                    filter_state = filter_obj.state
                    if filter_state == current_state:
                        print(f"Совпадение состояния: {current_state}")
                        return True
                    else:
                        print(f"Несовпадение состояния: {filter_state}, type: {type(filter_state)} != {current_state}, type: {type(current_state)}")
                        return False
                        
                # Если это фильтр команды, проверяем соответствие
                if message.text.startswith('/') and isinstance(filter_obj, Command):
                    cmd = message.text.split()[0][1:]  # Извлекаем команду без "/"
                    if cmd in filter_obj.commands:
                        return True
                    else:
                        return False
                    
                # Проверка на состояние
                if isinstance(filter_obj.callback, State):
                    callback = filter_obj.callback
                    # print(type(callback))
                    # print(callback)
                    # filter_state = filter_obj.callback.state
                    # print(type(filter_state))
                    # print(filter_state)
                    # print(type(current_state))
                    # print(current_state)
                    if callback.state == current_state:
                        print(f"Совпадение состояния: {current_state}")
                        return True
                    else:
                        print(f"Несовпадение состояния: {str(callback)}, type: {type(callback)}, {callback.state} != {current_state}, type: {type(current_state)}")
                        return False

        # Если у обработчика нет фильтров, то его можно использовать 
        # только если нет активного состояния
        if not hasattr(handler_obj, 'filters') or not handler_obj.filters:
            if current_state:
                return False
            return True
            
        # В случае сомнений лучше не вызывать обработчик
        return False