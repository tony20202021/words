"""
Tests for api_utils module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.utils.api_utils import (
    store_api_client,
    get_api_client_from_bot,
    get_api_client_from_dispatcher
)

class TestStoreApiClient:

    def test_store_api_client_success(self):
        # Setup
        bot = MagicMock()
        dispatcher = MagicMock()
        api_client = MagicMock()
        
        # Execute
        result = store_api_client(bot, dispatcher, api_client)
        
        # Verify
        assert result is True  # Успешное сохранение в обоих местах
        
        # Проверяем, что метод __setitem__ был вызван с правильными аргументами
        dispatcher.__setitem__.assert_called_once_with("api_client", api_client)
        
        # Проверяем, что у бота появился атрибут api_client с правильным значением
        assert hasattr(bot, "api_client")
        assert bot.api_client is api_client
        
    def test_store_api_client_fallback(self):
        # Setup
        bot = MagicMock()
        dispatcher = MagicMock()
        api_client = MagicMock()
        
        # Патчим builtins.setattr только в области функции store_api_client
        with patch('app.utils.api_utils.setattr', side_effect=AttributeError("Can't set attribute")):
            # Execute
            result = store_api_client(bot, dispatcher, api_client)
            
            # Verify
            assert result is False  # Не удалось сохранить в bot
            
            # Проверяем, что метод __setitem__ был вызван с правильными аргументами
            dispatcher.__setitem__.assert_called_once_with("api_client", api_client)

class TestGetApiClientFromBot:
    
    def test_get_api_client_from_bot_attribute(self):
        # Setup
        bot = MagicMock()
        api_client = MagicMock()
        
        # Настраиваем hasattr и getattr для эмуляции атрибута
        with patch('app.utils.api_utils.hasattr', return_value=True), \
             patch('app.utils.api_utils.getattr', return_value=api_client):
            
            # Execute
            result = get_api_client_from_bot(bot)
            
            # Verify
            assert result is api_client
    
    def test_get_api_client_from_bot_dictionary(self):
        # Setup
        bot = MagicMock()
        api_client = MagicMock()
        
        # Настраиваем hasattr для эмуляции отсутствия атрибута
        # и bot.get для возврата api_client
        with patch('app.utils.api_utils.hasattr', return_value=False):
            bot.get = MagicMock(return_value=api_client)
            
            # Execute
            result = get_api_client_from_bot(bot)
            
            # Verify
            assert result is api_client
            bot.get.assert_called_once_with("api_client")
    
    def test_get_api_client_from_bot_dispatcher(self):
        # Setup
        bot = MagicMock()
        dispatcher = MagicMock()
        api_client = MagicMock()
        
        # Последовательный патч для эмуляции полного сценария
        with patch('app.utils.api_utils.hasattr', side_effect=[False, True]), \
             patch.object(bot, 'get', side_effect=AttributeError("No get method")):
            
            # Настраиваем bot.dispatcher
            bot.dispatcher = dispatcher
            dispatcher.get = MagicMock(return_value=api_client)
            
            # Execute
            result = get_api_client_from_bot(bot)
            
            # Verify
            assert result is api_client
            dispatcher.get.assert_called_once_with("api_client")

    def test_get_api_client_from_bot_not_found(self):
        # Setup
        bot = MagicMock()
        
        # Настраиваем первый путь: атрибут bot.api_client есть, но равен None
        with patch('app.utils.api_utils.hasattr', return_value=True), \
            patch('app.utils.api_utils.getattr', return_value=None), \
            patch('app.utils.api_utils.logger'):  # Патчим логгер, чтобы не засорять вывод
            
            # Настраиваем второй путь: bot.get вызывает исключение
            bot.get = MagicMock(side_effect=AttributeError("No get method"))
            
            # Настраиваем третий путь: у бота есть диспетчер, но dispatcher.get возвращает None
            dispatcher = MagicMock()
            bot.dispatcher = dispatcher
            dispatcher.get = MagicMock(return_value=None)
            
            # Execute
            result = get_api_client_from_bot(bot)
            
            # Verify
            assert result is None
            # Проверяем, что был вызван get на диспетчере
            dispatcher.get.assert_called_once_with("api_client")

class TestGetApiClientFromDispatcher:
    
    def test_get_api_client_from_dispatcher_success(self):
        # Setup
        dispatcher = MagicMock()
        api_client = MagicMock()
        
        # Настраиваем dispatcher для возврата api_client
        dispatcher.get.return_value = api_client
        
        # Execute
        result = get_api_client_from_dispatcher(dispatcher)
        
        # Verify
        assert result is api_client
        dispatcher.get.assert_called_once_with("api_client")
    
    def test_get_api_client_from_dispatcher_not_found(self):
        # Setup
        dispatcher = MagicMock()
        
        # Патчим логгер, чтобы не засорять вывод
        with patch('app.utils.api_utils.logger'):
            # Настраиваем dispatcher для возврата None
            dispatcher.get.return_value = None
            
            # Execute
            result = get_api_client_from_dispatcher(dispatcher)
            
            # Verify
            assert result is None
            dispatcher.get.assert_called_once_with("api_client")