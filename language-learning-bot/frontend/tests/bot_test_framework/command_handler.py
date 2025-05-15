"""
Обработчик команд для Bot Test Framework.
"""

import inspect
import importlib
import traceback
from unittest.mock import MagicMock, AsyncMock

from aiogram.types import Message
from aiogram.filters import Command


class CommandHandler:
    """
    Класс для обработки команд бота в тестовом фреймворке.
    """
    def __init__(self, context):
        self.context = context
    
    async def execute_command(self, command: str, args: str = "") -> None:
        """
        Выполняет команду пользователя
        """
        print(f"\n=== ВЫПОЛНЕНИЕ КОМАНДЫ /{command} {args} ===")
        
        # Подготавливаем объект сообщения
        message = MagicMock(spec=Message)
        message.text = f"/{command} {args}".strip()
        message.from_user = self.context.user
        message.chat = self.context.chat
        message.bot = self.context.bot
        
        # Проверяем настройку API клиента
        if hasattr(self.context.bot, 'api_client') and self.context.bot.api_client:
            print(f"API клиент доступен в боте: {self.context.bot.api_client}")
        else:
            print("ПРЕДУПРЕЖДЕНИЕ: API клиент не настроен в боте!")
            # Добавляем API клиент в бот
            if self.context.api_client:
                self.context.bot.api_client = self.context.api_client
                print(f"API клиент установлен в боте: {self.context.bot.api_client}")
        
        # Моки для методов сообщения
        message.answer = AsyncMock()
        message.reply = AsyncMock()
        
        # Запоминаем вызов для истории
        self.context.command_history.append((command, args))
        
        # Находим обработчик команды
        handler = self._find_command_handler(command)
        
        if handler:
            print(f"Вызываем обработчик команды: {handler}")
            
            # Вызываем обработчик
            await handler(message, self.context.state)
            
            # Сохраняем ответы от бота
            print("Ответы бота:")
            for i, call in enumerate(message.answer.call_args_list):
                args, kwargs = call
                self.context.sent_messages.append((args[0] if args else "", kwargs))
                print(f"  Ответ #{i}: {args[0] if args else ''}")
            
            # Обратите внимание, что здесь больше не нужно сохранять историю состояний
            # это делается автоматически в методах state.update_data и state.set_state
            print(f"Текущее состояние: {self.context.state_data}")
        else:
            print(f"Обработчик для команды /{command} не найден!")
            # Попробуем вызвать обработчик напрямую через импорт
            try:
                print(f"Попытка импортировать и вызвать обработчик напрямую: cmd_{command}")
                
                for module_path in ["app.bot.handlers.user_handlers"]:
                    module = importlib.import_module(module_path)
                    handler_name = f"cmd_{command}"
                    
                    if hasattr(module, handler_name):
                        handler = getattr(module, handler_name)
                        print(f"Найден обработчик через прямой импорт: {handler}")
                        
                        # Вызываем обработчик
                        print(f"Вызываем импортированный обработчик: {handler}")
                        await handler(message, self.context.state)
                        
                        # Сохраняем ответы от бота
                        for call in message.answer.call_args_list:
                            args, kwargs = call
                            self.context.sent_messages.append((args[0] if args else "", kwargs))
                        
                        # Обратите внимание, что здесь больше не нужно сохранять историю состояний
                        # это делается автоматически в методах state.update_data и state.set_state
                        print(f"Импортированный обработчик выполнен успешно!")
                        return
                    
                raise ValueError(f"Обработчик для команды /{command} не найден")
            except Exception as e:
                print(f"Ошибка при попытке импорта обработчика: {e}")
                traceback.print_exc()
                raise ValueError(f"Обработчик для команды /{command} не найден")
   
    def _find_command_handler(self, command: str):
        """
        Поиск обработчика команды по имени команды.
        """
        # Проверяем, есть ли сохраненные обработчики команд
        if hasattr(self.context, 'command_handlers') and command in self.context.command_handlers:
            handler = self.context.command_handlers[command]
            print(f"Найден обработчик из сохраненных: {handler}")
            return handler
            
        print("Поиск обработчика в диспетчере и роутерах")
        
        # Проверка, есть ли диспетчер
        if self.context.dispatcher:
            print(f"Поиск обработчика команды в диспетчере: {self.context.dispatcher}")
            
            # В новых версиях aiogram структура изменилась
            # Ищем обработчики команд в роутерах диспетчера
            if hasattr(self.context.dispatcher, 'sub_routers'):
                for router in self.context.dispatcher.sub_routers:
                    # print(f"Проверка sub_router: {router}")
                    if hasattr(router, 'message'):
                        # print(f"Проверка router.message: {router.message}")
                        for handler_obj in router.message.handlers:
                            # print(f"Проверка обработчика: {handler_obj}")
                            
                            # ИСПРАВЛЕНИЕ: Проверка через флаги команд
                            if hasattr(handler_obj, 'flags') and 'commands' in handler_obj.flags:
                                for cmd_filter in handler_obj.flags['commands']:
                                    if hasattr(cmd_filter, 'commands') and command in cmd_filter.commands:
                                        handler = handler_obj.callback
                                        print(f"Найден обработчик через флаги в диспетчере: {handler}")
                                        return handler
                            
                            # ИСПРАВЛЕНИЕ: Проверка через список фильтров
                            if hasattr(handler_obj, 'filters') and handler_obj.filters:
                                for filter_obj in handler_obj.filters:
                                    # Проверка на объект Command через callback
                                    if hasattr(filter_obj, 'callback') and hasattr(filter_obj.callback, 'commands'):
                                        if command in filter_obj.callback.commands:
                                            handler = handler_obj.callback
                                            print(f"Найден обработчик через фильтр callback в диспетчере: {handler}")
                                            return handler
                                    
                                    # Проверка на прямой объект Command (aiogram 3.x)
                                    if hasattr(filter_obj, 'commands') and command in filter_obj.commands:
                                        handler = handler_obj.callback
                                        print(f"Найден обработчик через прямой фильтр в диспетчере: {handler}")
                                        return handler
        
        # Если не нашли в диспетчере, ищем в роутерах напрямую
        print("Поиск обработчика в all_routers")
        for router in self.context.all_routers:
            # print(f"Проверка роутера из all_routers: {router}")
            if hasattr(router, 'message'):
                # print(f"Проверка router.message: {router.message}")
                for handler_obj in router.message.handlers:
                    # print(f"Проверка обработчика: {handler_obj}")
                    
                    # ИСПРАВЛЕНИЕ: Проверка через флаги команд
                    if hasattr(handler_obj, 'flags') and 'commands' in handler_obj.flags:
                        for cmd_filter in handler_obj.flags['commands']:
                            if hasattr(cmd_filter, 'commands') and command in cmd_filter.commands:
                                handler = handler_obj.callback
                                print(f"Найден обработчик через флаги в роутере: {handler}")
                                return handler
                    
                    # ИСПРАВЛЕНИЕ: Проверка через список фильтров
                    if hasattr(handler_obj, 'filters') and handler_obj.filters:
                        for filter_obj in handler_obj.filters:
                            # Проверка на объект Command через callback
                            if hasattr(filter_obj, 'callback') and hasattr(filter_obj.callback, 'commands'):
                                if command in filter_obj.callback.commands:
                                    handler = handler_obj.callback
                                    print(f"Найден обработчик через фильтр callback в роутере: {handler}")
                                    return handler
                            
                            # Проверка на прямой объект Command (aiogram 3.x)
                            if hasattr(filter_obj, 'commands') and command in filter_obj.commands:
                                handler = handler_obj.callback
                                print(f"Найден обработчик через прямой фильтр в роутере: {handler}")
                                return handler
        
        # Если ничего не нашли
        return None