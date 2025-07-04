"""
Bot Test Framework - основной контекст для тестирования бота.
"""

import os
import sys
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, AsyncMock, patch

from aiogram import Router, Dispatcher, Bot
from aiogram.types import Message, CallbackQuery, User, Chat
from aiogram.fsm.context import FSMContext

from .command_handler import CommandHandler
from .message_handler import MessageHandler
from .callback_handler import CallbackHandler


class BotTestContext:
    """
    Контекст для тестирования бота, хранит состояние и мок-объекты.
    """
    def __init__(self, user_id: int = 12345, username: str = "test_user", 
                first_name: str = "Test", last_name: str = "User"):
        # Создаем мок-объекты для бота
        self.bot = MagicMock(spec=Bot)
        self.dispatcher = None
        self.all_routers = []
        
        # Создаем мок-объекты для пользователя
        self.user = MagicMock(spec=User)
        self.user.id = user_id
        self.user.username = username
        self.user.first_name = first_name
        self.user.last_name = last_name
        self.user.full_name = f"{first_name} {last_name}"
        
        # Создаем мок-объект для чата
        self.chat = MagicMock(spec=Chat)
        self.chat.id = user_id  # Для личных сообщений id чата равен id пользователя
        
        # Реальные данные состояния
        self.state_data = {}
        
        # Состояние FSM с корректными мок-методами, сохраняющими состояние
        self.state = MagicMock(spec=FSMContext)
        
        # Настраиваем методы мока с доступом к self.state_data
        async def mock_get_data():
            # print(f"Получение данных состояния: {self.state_data}")
            return self.state_data.copy()
        
        async def mock_update_data(*args, **kwargs):
            print(f"Обновление данных состояния: args={args}, kwargs={kwargs}")
            
            # Обработка как позиционных, так и именованных аргументов
            if len(args) > 0 and isinstance(args[0], dict):
                # Если первый аргумент - словарь, используем его для обновления state_data
                self.state_data.update(args[0])
            
            # Обработка именованных аргументов (как было раньше)
            if kwargs:
                self.state_data.update(kwargs)
            
            # Сохраняем историю состояний после каждого обновления
            self.state_history.append(self.state_data.copy())
            return self.state_data
            
        async def mock_set_state(state):
            print(f"type(state) = {type(state)}, state = {state}")
            if state is not None:
                print(f"state.state = {state.state}")
            state_str = str(state.state) if state else None
            print(f"Установка состояния: {state_str}")
            self.state_data['_state'] = state_str
            # Сохраняем историю состояний после каждого изменения
            self.state_history.append(self.state_data.copy())
        
        async def mock_get_state():
            print(f"Получение состояния: {self.state_data['_state']}")
            return self.state_data['_state']
        
        async def mock_clear():
            print("Очистка состояния")
            self.state_data.clear()
            # Сохраняем историю состояний после очистки
            self.state_history.append(self.state_data.copy())
        
        # Применяем мок-методы
        self.state.get_data = AsyncMock(side_effect=mock_get_data)
        self.state.update_data = AsyncMock(side_effect=mock_update_data)
        self.state.set_state = AsyncMock(side_effect=mock_set_state)
        self.state.get_state = AsyncMock(side_effect=mock_get_state)
        self.state.clear = AsyncMock(side_effect=mock_clear)
        
        # Моки для API
        self.api_client = None
        
        # История взаимодействий
        self.sent_messages = []  # Сообщения, отправленные ботом
        self.command_history = []  # История выполненных команд
        self.callback_history = []  # История выполненных callbacks
        self.state_history = []  # История изменений состояния

        # Патчи
        self.patches = []
        
        # Обработчики
        self.command_handlers = {}
        self.callback_handlers = {}
        
        # Создаем специализированные обработчики
        self.command_handler = CommandHandler(self)
        self.message_handler = MessageHandler(self)
        self.callback_handler = CallbackHandler(self)    
        
    def configure_api_client(self, mock_api_client: AsyncMock) -> None:
        """
        Настройка мок-объекта API клиента
        """
        self.api_client = mock_api_client
        
        # Сохраняем API клиент в атрибутах бота и диспетчера
        self.bot.api_client = mock_api_client
        if self.dispatcher:
            self.dispatcher.api_client = mock_api_client
        
        # Важно! Заменяем get_api_client_from_bot на функцию, которая возвращает наш API клиент
        def mock_get_api_client_from_bot(bot, *args, **kwargs):
            print(f"Мок get_api_client_from_bot вызван с аргументами: {args}, {kwargs}")
            return mock_api_client
        
        # Создаем патч для функции get_api_client_from_bot
        patch_obj = patch('app.utils.api_utils.get_api_client_from_bot', mock_get_api_client_from_bot)
        self.patches.append(patch_obj)
        patch_obj.start()
        
        print(f"API клиент настроен и установлен для бота и диспетчера")

    async def execute_command(self, command: str, args: str = "") -> None:
        """
        Выполняет команду пользователя
        """
        await self.command_handler.execute_command(command, args)
        
    async def send_message(self, text: str) -> None:
        """
        Отправляет обычное сообщение (не команду)
        """
        await self.message_handler.send_message(text)
    
    async def trigger_callback(self, callback_data: str) -> None:
        """
        Вызывает обработчик для callback_query
        """
        await self.callback_handler.trigger_callback(callback_data)

    def cleanup(self):
        """
        Очистка ресурсов после тестов
        """
        # Останавливаем все патчи
        for patch_obj in self.patches:
            patch_obj.stop()