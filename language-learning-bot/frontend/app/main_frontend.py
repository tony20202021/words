#!/usr/bin/env python
"""
Entry point for the frontend application.
This is the main script that initializes and starts the Telegram bot.
Enhanced with common handlers registration and improved error handling.
"""

import asyncio
import argparse
import logging
import os
import sys
import yaml
from pathlib import Path
from typing import List

# Add the parent directory to sys.path to allow imports from other modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# aiogram 3.x импорты
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from hydra import compose, initialize
from omegaconf import OmegaConf
from datetime import datetime

from app.api.client import APIClient
from app.bot.bot import BotManager
import app.bot.handlers.admin_handlers as admin_handlers
import app.bot.handlers.language_handlers as language_handlers
import app.bot.handlers.study_handlers as study_handlers
import app.bot.handlers.user_handlers as user_handlers
# НОВОЕ: Импорт обработчиков для meta-состояний
import app.bot.handlers.common_handlers as common_handlers
from app.bot.middleware.auth_middleware import AuthMiddleware, StateValidationMiddleware
from app.utils.logger import setup_logger
from app.utils.api_utils import store_api_client, get_api_client_from_bot

# Load environment variables from .env file
load_dotenv()

# Initialize Hydra configuration
initialize(config_path="../conf/config", version_base=None)
cfg = compose(config_name="default")

# Ensure logs directory exists
log_dir = cfg.logging.log_dir if hasattr(cfg, "logging") and hasattr(cfg.logging, "log_dir") else "logs"
os.makedirs(os.path.join(os.getcwd(), log_dir), exist_ok=True)

# Set up logging
logger = setup_logger(
    __name__, 
    log_level=cfg.logging.level if hasattr(cfg, "logging") and hasattr(cfg.logging, "level") else "INFO",
    log_format=cfg.logging.format if hasattr(cfg, "logging") and hasattr(cfg.logging, "format") else None,
    log_dir=log_dir
)

# ОБНОВЛЕНО: Добавлен common_handlers в список модулей
HANDLER_MODULES = [
    common_handlers,    # НОВОЕ: Обработчики meta-состояний должны быть первыми
    admin_handlers,
    user_handlers,
    language_handlers,
    study_handlers,
]

def register_all_handlers(dispatcher: Dispatcher) -> None:
    """
    Register all handlers for the bot.
    Enhanced with common handlers registration.
    
    Args:
        dispatcher: Aiogram dispatcher
    """
    logger.info("Starting handler registration...")
    
    # Регистрируем обработчики в правильном порядке
    for i, module in enumerate(HANDLER_MODULES):
        try:
            if hasattr(module, 'register_handlers'):
                module.register_handlers(dispatcher)
                logger.info(f"✅ Registered handlers from {module.__name__}")
            elif hasattr(module, 'register_common_handlers'):
                # Специальная обработка для common_handlers
                module.register_common_handlers(dispatcher)
                logger.info(f"✅ Registered common handlers from {module.__name__}")
            else:
                logger.warning(f"⚠️ Module {module.__name__} has no register_handlers function")
        except Exception as e:
            logger.error(f"❌ Failed to register handlers from {module.__name__}: {e}", exc_info=True)
            # Не прерываем запуск бота из-за ошибки в одном модуле
            continue
    
    logger.info("Handler registration completed")

def get_admin_ids_from_config(cfg) -> List[int]:
    """
    Получает список ID администраторов из конфигурации
    
    Args:
        cfg: Объект конфигурации Hydra
        
    Returns:
        Список ID администраторов (целые числа)
    """
    admin_ids = []
    
    if hasattr(cfg, "bot") and hasattr(cfg.bot, "admin_ids") and cfg.bot.admin_ids:
        # Разбираем строку с ID, разделенными запятыми
        try:
            admin_ids_str = cfg.bot.admin_ids.split(",")
            admin_ids = [int(admin_id.strip()) for admin_id in admin_ids_str if admin_id.strip()]
        except (ValueError, AttributeError) as e:
            logger.error(f"Failed to parse admin IDs from config: {e}")
    
    return admin_ids

async def check_system_health(bot: Bot, api_client: APIClient) -> dict:
    """
    НОВОЕ: Проверяет состояние системы при запуске.
    
    Args:
        bot: Экземпляр бота
        api_client: API клиент
        
    Returns:
        dict: Статус различных компонентов системы
    """
    health_status = {
        "bot": True,  # Если мы дошли до этой точки, бот работает
        "api_connection": False,
        "database": False,
        "admin_notification_sent": False
    }
    
    try:
        # Проверяем API соединение
        logger.info("Checking API connection...")
        health_response = await api_client._make_request("GET", "/health")
        health_status["api_connection"] = health_response.get("success", False)
        
        if health_status["api_connection"]:
            logger.info("✅ API connection successful")
            
            # Проверяем доступность базы данных через API
            logger.info("Checking database connectivity...")
            languages_response = await api_client.get_languages()
            health_status["database"] = languages_response.get("success", False)
            
            if health_status["database"]:
                logger.info("✅ Database connectivity successful")
            else:
                logger.error("❌ Database connectivity failed")
        else:
            logger.error("❌ API connection failed")
            
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}", exc_info=True)
    
    return health_status

async def notify_admins_about_startup(bot: Bot, health_status: dict, admin_ids: List[int]) -> bool:
    """
    НОВОЕ: Уведомляет администраторов о запуске бота и статусе системы.
    
    Args:
        bot: Экземпляр бота
        health_status: Статус компонентов системы
        admin_ids: Список ID администраторов
        
    Returns:
        bool: True если хотя бы один администратор был уведомлен
    """
    if not admin_ids:
        logger.info("No admin IDs configured, skipping admin notifications")
        return False
    
    # Формируем сообщение о статусе
    status_icon = "✅" if all([health_status["api_connection"], health_status["database"]]) else "⚠️"
    
    startup_message = (
        f"{status_icon} **Бот запущен**\n\n"
        f"🤖 Бот: {'✅ Работает' if health_status['bot'] else '❌ Ошибка'}\n"
        f"🔗 API: {'✅ Доступен' if health_status['api_connection'] else '❌ Недоступен'}\n"
        f"🗄️ База данных: {'✅ Доступна' if health_status['database'] else '❌ Недоступна'}\n\n"
        f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Версия: Language Learning Bot v1.0"
    )
    
    if not health_status["api_connection"] or not health_status["database"]:
        startup_message += (
            f"\n\n⚠️ **Внимание!** Обнаружены проблемы с системой.\n"
            f"Бот может работать некорректно."
        )
    
    successful_notifications = 0
    
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, startup_message, parse_mode="Markdown")
            successful_notifications += 1
            logger.info(f"✅ Startup notification sent to admin {admin_id}")
        except Exception as e:
            logger.error(f"❌ Failed to send startup notification to admin {admin_id}: {e}")
    
    if successful_notifications > 0:
        logger.info(f"Startup notifications sent to {successful_notifications}/{len(admin_ids)} admins")
        return True
    else:
        logger.warning("Failed to send startup notifications to any admins")
        return False

async def setup_middleware(dispatcher: Dispatcher) -> None:
    """
    НОВОЕ: Настройка middleware с улучшенной обработкой ошибок.
    
    Args:
        dispatcher: Диспетчер aiogram
    """
    logger.info("Setting up middleware...")
    
    try:
        # Основной middleware для аутентификации (должен быть первым)
        auth_middleware = AuthMiddleware()
        dispatcher.update.middleware(auth_middleware)
        logger.info("✅ AuthMiddleware registered")
        
        # НОВОЕ: Middleware для валидации состояний FSM
        state_validation_middleware = StateValidationMiddleware(
            validate_states=True,
            auto_recover=True
        )
        dispatcher.update.middleware(state_validation_middleware)
        logger.info("✅ StateValidationMiddleware registered")
        
        logger.info("All middleware registered successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to setup middleware: {e}", exc_info=True)
        raise

async def on_startup(dispatcher: Dispatcher, bot: Bot) -> None:
    """
    Execute actions on application startup.
    Enhanced with system health checks and admin notifications.
    
    Args:
        dispatcher: Aiogram dispatcher
        bot: Aiogram bot instance
    """
    logger.info("=" * 50)
    logger.info("🚀 Starting Language Learning Bot...")
    logger.info("=" * 50)
    
    # Получаем API client, который был создан в main()
    api_client = get_api_client_from_bot(bot)
    
    # НОВОЕ: Проверяем состояние системы
    health_status = await check_system_health(bot, api_client)
    
    # Получаем список администраторов
    admin_ids = get_admin_ids_from_config(cfg)
    
    if api_client:
        logger.info("✅ API client found successfully")
        
        if health_status["api_connection"] and health_status["database"]:
            logger.info("✅ All systems operational")
        else:
            logger.warning("⚠️ Some systems are not fully operational")
            
    else:
        logger.error("❌ API client is not available. Bot might not work properly!")
        health_status["api_connection"] = False
        health_status["database"] = False
    
    # НОВОЕ: Уведомляем администраторов о запуске
    if admin_ids:
        health_status["admin_notification_sent"] = await notify_admins_about_startup(
            bot, health_status, admin_ids
        )
    
    # Настройка middleware
    await setup_middleware(dispatcher)
    
    # Register all handlers
    register_all_handlers(dispatcher)
    
    # Настройка команд бота через BotManager
    bot_manager = dispatcher.get("bot_manager")
    if bot_manager:
        try:
            await bot_manager.setup_commands()
            logger.info("✅ Bot commands configured")
        except Exception as e:
            logger.error(f"❌ Failed to setup bot commands: {e}")
    
    logger.info("=" * 50)
    logger.info("🎉 Bot started successfully!")
    logger.info("=" * 50)

async def on_shutdown(dispatcher: Dispatcher) -> None:
    """
    Execute actions on application shutdown.
    Enhanced with cleanup and admin notifications.
    
    Args:
        dispatcher: Aiogram dispatcher
    """
    logger.info("=" * 30)
    logger.info("🛑 Shutting down bot...")
    logger.info("=" * 30)
    
    # НОВОЕ: Уведомляем администраторов об остановке
    try:
        admin_ids = get_admin_ids_from_config(cfg)
        if admin_ids:
            bot = dispatcher.get("bot")  # Попробуем получить бот из диспетчера
            if bot:
                shutdown_message = (
                    f"🛑 **Бот остановлен**\n\n"
                    f"Время остановки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                
                for admin_id in admin_ids:
                    try:
                        await bot.send_message(admin_id, shutdown_message, parse_mode="Markdown")
                        logger.info(f"✅ Shutdown notification sent to admin {admin_id}")
                    except Exception as e:
                        logger.error(f"❌ Failed to send shutdown notification to admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Error during admin shutdown notification: {e}")
    
    # В aiogram 3.x нет необходимости явно закрывать хранилище
    logger.info("🏁 Bot stopped successfully!")

def load_secrets(cfg, path):
    """
    Загружает конфиденциальные данные из внешнего файла.
    Обновляет конфигурацию Hydra с этими данными.
    """
    try:
        path = os.path.expanduser(path)
        path = os.path.expandvars(path)
        logger.info(f"Looking for secrets file at: {path}")

        if os.path.exists(path):
            logger.info(f"Found secrets file: {path}")
            with open(path, 'r') as f:
                secrets = yaml.safe_load(f)
            
            # Обновление токена бота, если он задан
            if secrets and isinstance(secrets, dict) and 'bot' in secrets and 'token' in secrets['bot']:
                # Обновляем токен в конфигурации
                cfg.bot.token = secrets['bot']['token']
                logger.info("✅ Bot token successfully loaded from external file")
                return True
    except Exception as e:
        logger.error(f"Error loading secrets from {path}: {e}")
    
    logger.error("❌ Failed to load secrets from external files")
    return False

async def main() -> None:
    """
    Initialize and start the Telegram bot.
    Enhanced with improved error handling and system monitoring.
    """
    try:
        # Загружаем секреты
        secrets_loaded = load_secrets(cfg, "~/.ssh/bot.yaml")
        if not secrets_loaded:
            logger.warning("⚠️ External secrets not loaded, using environment variables")

        # Get bot token from configuration
        bot_token = cfg.bot.token if hasattr(cfg, "bot") and hasattr(cfg.bot, "token") else None
        if not bot_token:
            logger.error("❌ Bot token is not set in configuration!")
            sys.exit(1)
        
        logger.info("✅ Bot token configured")
        
        # Create bot and dispatcher instances
        bot = Bot(token=bot_token)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        logger.info("✅ Bot and dispatcher instances created")
                
        # Initialize API client из конфигурации Hydra
        api_base_url = cfg.api.base_url if hasattr(cfg, "api") and hasattr(cfg.api, "base_url") else "http://localhost:8500"
        api_timeout = int(cfg.api.timeout) if hasattr(cfg, "api") and hasattr(cfg.api, "timeout") else 5
        api_retry_count = int(cfg.api.retry_count) if hasattr(cfg, "api") and hasattr(cfg.api, "retry_count") else 3
        api_prefix = cfg.api.prefix if hasattr(cfg, "api") and hasattr(cfg.api, "prefix") else "/api"

        logger.info(f"Initializing API client:")
        logger.info(f"  - Base URL: {api_base_url}")
        logger.info(f"  - Timeout: {api_timeout}s")
        logger.info(f"  - Retry count: {api_retry_count}")
        logger.info(f"  - API prefix: {api_prefix}")

        api_client = APIClient(
            base_url=api_base_url,
            api_prefix=api_prefix,
            timeout=api_timeout,
            retry_count=api_retry_count
        )        
        
        # Сохраняем api_client используя утилиту
        store_api_client(bot, dp, api_client)
        logger.info("✅ API client stored successfully")
        
        # Create bot manager
        bot_manager = BotManager(bot, dp)
        
        # Сохраняем bot_manager в диспетчере для доступа в других местах
        dp["bot_manager"] = bot_manager
        
        # Связываем диспетчера с ботом для возможности доступа к диспетчеру через бот
        # Это нестандартная операция, но она поможет в обработчиках получать api_client через message.bot.dispatcher
        setattr(bot, "dispatcher", dp)
        
        # НОВОЕ: Регистрация обработчиков для запуска и остановки с улучшенной обработкой ошибок
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        logger.info("✅ Startup and shutdown handlers registered")
        logger.info("🔄 Starting polling...")
        
        # Получаем настройки запуска из конфигурации
        skip_updates = cfg.bot.skip_updates if hasattr(cfg, "bot") and hasattr(cfg.bot, "skip_updates") else False
        
        await dp.start_polling(
            bot,
            skip_updates=skip_updates,
        )

    except KeyboardInterrupt:
        logger.info("🔴 Keyboard interrupt received")
        raise
    except Exception as e:
        logger.error(f"❌ Critical error during bot startup: {e}", exc_info=True)
        
        # НОВОЕ: Попытка уведомить администраторов о критической ошибке
        try:
            admin_ids = get_admin_ids_from_config(cfg)
            if admin_ids and 'bot' in locals():
                error_message = (
                    f"🔥 **Критическая ошибка при запуске бота**\n\n"
                    f"Ошибка: {str(e)}\n"
                    f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"Проверьте логи для подробной информации."
                )
                
                for admin_id in admin_ids:
                    try:
                        await bot.send_message(admin_id, error_message, parse_mode="Markdown")
                    except:
                        pass  # Игнорируем ошибки отправки в критической ситуации
        except:
            pass  # Игнорируем ошибки уведомления в критической ситуации
        
        sys.exit(1)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description='Запуск Language Learning Bot')
        
        # Добавляем аргумент process-name для идентификации процесса
        parser.add_argument('--process-name', type=str, help='Имя процесса для идентификации')
        parser.add_argument('--debug', action='store_true', help='Включить отладочный режим')
        parser.add_argument('--no-admin-notifications', action='store_true', help='Отключить уведомления администраторов')
        
        # Парсим аргументы, но не выходим при ошибке для обратной совместимости
        args, unknown = parser.parse_known_args()
        
        # Устанавливаем уровень логирования в зависимости от режима отладки
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.setLevel(logging.DEBUG)
            logger.info("🔍 Debug mode enabled")
        
        # Логируем информацию о запуске
        if args.process_name:
            logger.info(f"🏷️ Process identifier: {args.process_name}")
        else:
            logger.info("🏷️ Process started without identifier")
        
        # Логируем информацию о процессе
        pid = os.getpid()
        logger.info(f"🆔 Process ID (PID): {pid}")
        logger.info(f"📁 Working directory: {os.getcwd()}")
        logger.info(f"🐍 Python version: {sys.version}")
        
        # НОВОЕ: Добавляем информацию о системе
        logger.info(f"💾 Platform: {sys.platform}")
        logger.info(f"🖥️ Architecture: {os.uname().machine if hasattr(os, 'uname') else 'Unknown'}")

        # Запускаем основной цикл
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("⏹️ Received interrupt signal")
        logger.info("🔄 Shutting down gracefully...")
    except Exception as e:
        logger.error(f"💥 Critical error in main: {e}", exc_info=True)
    finally:
        logger.info("🏁 Process terminated!")
        