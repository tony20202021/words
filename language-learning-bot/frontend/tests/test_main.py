"""
Unit tests for the main_frontend.py module of the frontend application.
"""

import pytest
import sys
import os
import logging
from unittest.mock import patch, MagicMock, AsyncMock, call
from aiogram import Bot, Dispatcher
from app.api.client import APIClient
from aiogram.fsm.storage.memory import MemoryStorage


with patch('hydra.initialize'):
    with patch('hydra.compose') as mock_compose:
        with patch('app.utils.logger.setup_logger') as mock_setup_logger:  # ← Добавить патч
            mock_cfg = MagicMock()
            mock_compose.return_value = mock_cfg
            mock_setup_logger.return_value = MagicMock()  # Мок логгера
            
            # Import the module to test
            import app.main_frontend


class TestMain:
    """Tests for the main module."""

    def setup_method(self):
        """Setup before each test method."""
        # Сбрасываем состояние Hydra перед каждым тестом
        with patch('hydra.core.global_hydra.GlobalHydra.instance') as mock_instance:
            mock_hydra = MagicMock()
            mock_instance.return_value = mock_hydra
            mock_hydra.is_initialized.return_value = True
            mock_hydra.clear.return_value = None

    @pytest.mark.asyncio
    async def test_main_initialization(self):
        """
        Проверка правильной инициализации основных компонентов.
        """
        # Моки для внешних зависимостей
        mock_bot = MagicMock()
        mock_dp = MagicMock()
        mock_storage = MagicMock()
        mock_api_client = MagicMock()
        mock_bot_manager = MagicMock()
        mock_logger = MagicMock()
        mock_cfg = MagicMock()
        
        # Патчим Hydra
        with patch('hydra.initialize') as mock_initialize, \
            patch('hydra.compose') as mock_compose:
            
            mock_compose.return_value = mock_cfg
            
            # Настраиваем параметры конфигурации
            mock_cfg.bot = MagicMock()
            mock_cfg.bot.token = "fake_token"
            mock_cfg.bot.skip_updates = True
            
            mock_cfg.api = MagicMock()
            mock_cfg.api.base_url = "http://localhost:8500"
            mock_cfg.api.timeout = 5
            mock_cfg.api.retry_count = 3
            mock_cfg.api.prefix = "/api"
            
            mock_cfg.logging = MagicMock()
            mock_cfg.logging.level = "INFO"
            mock_cfg.logging.log_dir = "logs"
            
            # Патчим загрузку секретов - новое
            with patch('app.main_frontend.load_secrets', return_value=True) as mock_load_secrets, \
                patch('app.main_frontend.Bot', return_value=mock_bot) as mock_bot_class, \
                patch('app.main_frontend.Dispatcher', return_value=mock_dp) as mock_dp_class, \
                patch('app.main_frontend.MemoryStorage', return_value=mock_storage) as mock_storage_class, \
                patch('app.main_frontend.APIClient', return_value=mock_api_client) as mock_api_client_class, \
                patch('app.main_frontend.BotManager', return_value=mock_bot_manager) as mock_bot_manager_class, \
                patch('app.main_frontend.store_api_client') as mock_store_api_client, \
                patch('app.main_frontend.AuthMiddleware') as mock_auth_middleware, \
                patch.object(mock_dp, 'start_polling', new_callable=AsyncMock) as mock_start_polling, \
                patch('app.main_frontend.logger', mock_logger), \
                patch.object(app.main_frontend, 'cfg', mock_cfg), \
                patch('asyncio.run'), \
                patch('os.makedirs') as mock_makedirs, \
                patch('app.main_frontend.setup_logger') as mock_setup_logger, \
                patch('sys.exit'):
                
                mock_setup_logger.return_value = mock_logger
                
                # Запускаем main
                await app.main_frontend.main()
                
                # Проверяем вызов load_secrets
                mock_load_secrets.assert_called_once_with(mock_cfg, "~/.ssh/bot.yaml")
                
                # Проверяем, что все объекты созданы с правильными параметрами
                mock_bot_class.assert_called_once_with(token='fake_token')
                mock_storage_class.assert_called_once()
                mock_dp_class.assert_called_once_with(storage=mock_storage)
                mock_api_client_class.assert_called_once()
                mock_bot_manager_class.assert_called_once_with(mock_bot, mock_dp)
                
                # Проверяем, что API клиент сохранен
                mock_store_api_client.assert_called_once_with(mock_bot, mock_dp, mock_api_client)
                
                # Проверяем, что bot_manager сохранен в диспетчере
                mock_dp.__setitem__.assert_any_call("bot_manager", mock_bot_manager)
                
                # Проверяем, что обработчики запуска и остановки зарегистрированы
                mock_dp.startup.register.assert_called_once()
                mock_dp.shutdown.register.assert_called_once()
                
                # Проверяем, что start_polling был вызван
                mock_start_polling.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_missing_bot_token(self):
        """
        Проверка корректной обработки отсутствия токена бота.
        """
        # Создаем мок для конфигурации
        mock_cfg = MagicMock()
        mock_cfg.bot = MagicMock()
        mock_cfg.bot.token = None  # Отсутствующий токен
        
        # Настраиваем остальные атрибуты конфигурации
        mock_cfg.logging = MagicMock()
        mock_cfg.logging.level = "INFO"
        mock_cfg.logging.log_dir = "logs"
        
        # Моки для объектов
        mock_logger = MagicMock()
        
        # Патчим Hydra и ВСЕ НЕОБХОДИМЫЕ КОМПОНЕНТЫ
        with patch('hydra.initialize') as mock_initialize, \
            patch('hydra.compose') as mock_compose, \
            patch('app.main_frontend.logger', mock_logger), \
            patch('app.main_frontend.setup_logger', return_value=mock_logger) as mock_setup_logger, \
            patch('app.main_frontend.load_secrets', return_value=False), \
            patch('app.main_frontend.validate_configuration', return_value=False), \
            patch('os.makedirs'):
            
            mock_compose.return_value = mock_cfg
            
            try:
                # Вызываем main
                await app.main_frontend.main()
                
                assert False, "main() должен вызвать sys.exit(1)"

            except SystemExit as e:
                # Проверяем, что sys.exit был вызван с кодом 1
                assert e.code == 1
            
            # Проверяем, что логгер был
            mock_logger.info.assert_called_with("Using environment variables for configuration")
            mock_logger.error.assert_called_with("❌ Configuration validation failed!")

    @pytest.mark.asyncio
    async def test_on_startup(self):
        """
        Проверка успешного запуска и регистрации команд бота.
        """
        # Создаем моки для основных объектов
        mock_bot = MagicMock(spec=Bot)
        mock_dp = MagicMock(spec=Dispatcher)
        mock_bot_manager = AsyncMock()
        mock_api_client = MagicMock(spec=APIClient)
        
        # Создаем моки для logger и cfg
        mock_logger = MagicMock()
        mock_cfg = MagicMock()

        health_status = {
            "bot": True,  # Если мы дошли до этой точки, бот работает
            "api_connection": True,
            "database": True,
            "admin_notification_sent": False
        }
        
        # Определяем функцию для получения ID администраторов из конфигурации
        def get_admin_ids_from_config(cfg):
            return []
        
        # Настраиваем мок диспетчера
        mock_dp.get.return_value = mock_bot_manager
        
        # Патчим все необходимые зависимости
        with patch.object(app.main_frontend, 'get_api_client_from_bot', return_value=mock_api_client), \
            patch('app.main_frontend.check_system_health', return_value=health_status), \
            patch('app.main_frontend.register_all_handlers') as mock_register_handlers, \
            patch('app.main_frontend.setup_middleware') as mock_setup_middleware, \
            patch('app.main_frontend.logger', mock_logger), \
            patch.object(app.main_frontend, 'cfg', mock_cfg), \
            patch('app.main_frontend.get_admin_ids_from_config', return_value=[]):
            
            # Вызываем тестируемую функцию
            await app.main_frontend.on_startup(mock_dp, mock_bot)
            
            # Проверяем, что setup_commands был вызван
            mock_bot_manager.setup_commands.assert_awaited_once()
            
            # Проверяем, что register_all_handlers был вызван с правильным параметром
            mock_register_handlers.assert_called_once_with(mock_dp)
            
            # Проверяем, что диспетчер вызвал get для получения bot_manager
            mock_dp.get.assert_called_with('bot_manager')
            
            # Проверяем логирование
            mock_logger.info.assert_any_call("🚀 Starting Language Learning Bot...")
            mock_logger.info.assert_any_call("✅ API client found successfully")
            mock_logger.info.assert_any_call("✅ All systems operational")
            mock_logger.info.assert_any_call("✅ Bot commands configured")
            mock_logger.info.assert_any_call("🎉 Bot started successfully!")
                        
    @pytest.mark.asyncio
    async def test_on_shutdown_successful(self):
        """
        Проверка корректного завершения работы.
        """
        # Создаем мок диспетчера
        mock_dp = MagicMock(spec=Dispatcher)
        
        # Патчим логгер
        with patch('app.main_frontend.logger.info') as mock_logger_info:
            # Вызываем on_shutdown
            await app.main_frontend.on_shutdown(mock_dp)
            
            # Проверяем, что были залогированы сообщения о начале и успешном завершении
            assert mock_logger_info.call_count == 5
            mock_logger_info.assert_any_call("🛑 Shutting down bot...")
            mock_logger_info.assert_any_call("🏁 Bot stopped successfully!")


    @pytest.mark.asyncio
    async def test_api_client_configuration(self):
        """
        Проверка правильной конфигурации API клиента.
        """
        # Создаем моки для конфигурации
        mock_cfg = MagicMock()
        mock_cfg.api.base_url = "http://testapi.example.com"
        mock_cfg.api.timeout = 10
        mock_cfg.api.retry_count = 5
        mock_cfg.api.prefix = "/test-api"
        mock_cfg.bot.token = "fake_token"
        
        # Моки для объектов
        mock_bot = MagicMock(spec=Bot)
        mock_dp = MagicMock(spec=Dispatcher)
        mock_storage = MagicMock(spec=MemoryStorage)
        mock_api_client = MagicMock()
        mock_bot_manager = AsyncMock()
        
        # Настраиваем мок диспетчера
        mock_dp.startup = MagicMock()
        mock_dp.shutdown = MagicMock()
        
        # Мок для логгера
        mock_logger = MagicMock()
        
        # Патчим зависимости и конфигурацию
        with patch('hydra.initialize') as mock_initialize, \
            patch('hydra.compose') as mock_compose, \
            patch('app.main_frontend.Bot', return_value=mock_bot), \
            patch('app.main_frontend.Dispatcher', return_value=mock_dp), \
            patch('app.main_frontend.MemoryStorage', return_value=mock_storage), \
            patch('app.main_frontend.APIClient', return_value=mock_api_client) as mock_api_client_class, \
            patch.object(app.main_frontend, 'cfg', mock_cfg), \
            patch('app.main_frontend.BotManager', return_value=mock_bot_manager), \
            patch('app.main_frontend.store_api_client') as mock_store_api_client, \
            patch.object(mock_dp, 'start_polling', new_callable=AsyncMock), \
            patch('app.main_frontend.logger', mock_logger), \
            patch('app.main_frontend.setup_logger', return_value=mock_logger), \
            patch('sys.exit'):
            
            mock_compose.return_value = mock_cfg
            
            # Запускаем main
            await app.main_frontend.main()
            
            # Проверяем, что APIClient был создан с правильными параметрами
            mock_api_client_class.assert_called_once_with(
                base_url="http://testapi.example.com",
                api_prefix="/test-api",
                timeout=10,
                retry_count=5
            )
            
            # Проверяем, что API клиент был сохранен
            mock_store_api_client.assert_called_once_with(mock_bot, mock_dp, mock_api_client)
            
    @pytest.mark.asyncio
    async def test_bot_polling_start(self):
        """
        Проверка успешного запуска поллинга бота.
        """
        # Создаем мок для конфигурации с skip_updates=True
        mock_cfg = MagicMock()
        mock_cfg.bot.skip_updates = True
        mock_cfg.bot.token = "fake_token"
        
        # Моки для внешних зависимостей
        mock_bot = MagicMock()
        mock_dp = MagicMock()
        mock_storage = MagicMock()
        mock_api_client = MagicMock()
        mock_bot_manager = MagicMock()
        mock_logger = MagicMock()
        
        # Патчим зависимости
        with patch('hydra.initialize'), \
            patch('hydra.compose') as mock_compose, \
            patch('app.main_frontend.Bot', return_value=mock_bot), \
            patch('app.main_frontend.Dispatcher', return_value=mock_dp), \
            patch('app.main_frontend.MemoryStorage', return_value=mock_storage), \
            patch('app.main_frontend.APIClient', return_value=mock_api_client), \
            patch('app.main_frontend.BotManager', return_value=mock_bot_manager), \
            patch('app.main_frontend.store_api_client'), \
            patch('app.main_frontend.AuthMiddleware'), \
            patch.object(mock_dp, 'start_polling', new_callable=AsyncMock) as mock_start_polling, \
            patch('app.main_frontend.logger', mock_logger), \
            patch('app.main_frontend.setup_logger', return_value=mock_logger), \
            patch.object(app.main_frontend, 'cfg', mock_cfg), \
            patch('asyncio.run'), \
            patch('sys.exit'):
            
            mock_compose.return_value = mock_cfg
                        
            # Запускаем main
            await app.main_frontend.main()
            
            # Проверяем, что start_polling вызван с правильными параметрами
            mock_dp.start_polling.assert_awaited_once()
            args, kwargs = mock_dp.start_polling.await_args
            assert args[0] == mock_bot  # Первый аргумент должен быть ботом
            assert kwargs.get('skip_updates') is True

    @pytest.mark.asyncio
    async def test_bot_dispatcher_linking(self):
        """
        Проверка корректной связи между объектами бота и диспетчера.
        """
        # Моки для объектов
        mock_bot = MagicMock()
        mock_dp = MagicMock()
        mock_storage = MagicMock()
        mock_api_client = MagicMock()
        mock_bot_manager = MagicMock()
        mock_logger = MagicMock()
        mock_cfg = MagicMock()
        mock_cfg.bot.token = "fake_token"
        
        # Патчим зависимости
        with patch('hydra.initialize'), \
            patch('hydra.compose') as mock_compose, \
            patch('app.main_frontend.Bot', return_value=mock_bot), \
            patch('app.main_frontend.Dispatcher', return_value=mock_dp), \
            patch('app.main_frontend.MemoryStorage', return_value=mock_storage), \
            patch('app.main_frontend.APIClient', return_value=mock_api_client), \
            patch('app.main_frontend.BotManager', return_value=mock_bot_manager), \
            patch('app.main_frontend.store_api_client'), \
            patch('app.main_frontend.AuthMiddleware'), \
            patch.object(mock_dp, 'start_polling', new_callable=AsyncMock), \
            patch('app.main_frontend.logger', mock_logger), \
            patch('app.main_frontend.setup_logger', return_value=mock_logger), \
            patch.object(app.main_frontend, 'cfg', mock_cfg), \
            patch('asyncio.run'), \
            patch('sys.exit'):
            
            mock_compose.return_value = mock_cfg
            
            # Запускаем main
            await app.main_frontend.main()
            
            # Проверяем, что setattr вызван для установки связи bot.dispatcher = dp
            assert hasattr(mock_bot, 'dispatcher')
            assert mock_bot.dispatcher == mock_dp