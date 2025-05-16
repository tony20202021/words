#!/usr/bin/env python
"""
Entry point for the frontend application.
This is the main script that initializes and starts the Telegram bot.
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

from app.api.client import APIClient
from app.bot.bot import BotManager
import app.bot.handlers.admin_handlers as admin_handlers
import app.bot.handlers.language_handlers as language_handlers
import app.bot.handlers.study_handlers as study_handlers
import app.bot.handlers.user_handlers as user_handlers
from app.bot.middleware.auth_middleware import AuthMiddleware
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

HANDLER_MODULES = [
    admin_handlers,
    user_handlers,
    language_handlers,
    study_handlers,
]

def register_all_handlers(dispatcher: Dispatcher) -> None:
    """
    Register all handlers for the bot.
    
    Args:
        dispatcher: Aiogram dispatcher
    """
    for module in HANDLER_MODULES:
        module.register_handlers(dispatcher)

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

async def on_startup(dispatcher: Dispatcher, bot: Bot) -> None:
    """
    Execute actions on application startup.
    
    Args:
        dispatcher: Aiogram dispatcher
        bot: Aiogram bot instance
    """
    logger.info("Starting Language Learning Bot...")
    
    # Получаем API client, который был создан в main()
    api_client = get_api_client_from_bot(bot)
    
    # Проверяем, успешно ли получен API клиент
    # вызвать ("/health", tags=["health"])
    #     """Health check endpoint that always returns 200 OK."""
    #      {"status": "ok", "environment": app_environment}
    
    if api_client:
        logger.info("API client found successfully.")
    else:
        logger.error("API client is not available. Bot might not work properly!")
        # Отправляем сообщение администратору о проблеме
        admin_ids = get_admin_ids_from_config(cfg)
        for admin_id in admin_ids:
            try:
                await bot.send_message(
                    admin_id, 
                    "⚠️ Внимание! API клиент недоступен. Бот может работать некорректно."
                )
            except Exception as e:
                logger.error(f"Failed to send error message to admin {admin_id}: {e}")
    
    # Register all handlers
    register_all_handlers(dispatcher)
    
    # Настройка команд бота через BotManager
    bot_manager = dispatcher.get("bot_manager")
    if bot_manager:
        await bot_manager.setup_commands()
    
    logger.info("Bot started successfully!")


async def on_shutdown(dispatcher: Dispatcher) -> None:
    """
    Execute actions on application shutdown.
    
    Args:
        dispatcher: Aiogram dispatcher
    """
    logger.info("Shutting down...")
    
    # В aiogram 3.x нет необходимости явно закрывать хранилище
    logger.info("Bot stopped successfully!")

def load_secrets(cfg, path):
    """
    Загружает конфиденциальные данные из внешнего файла.
    Обновляет конфигурацию Hydra с этими данными.
    """
    try:
        if os.path.exists(path):
            logger.info(f"Найден файл с секретами: {path}")
            with open(path, 'r') as f:
                secrets = yaml.safe_load(f)
            
            # Обновление токена бота, если он задан
            if secrets and isinstance(secrets, dict) and 'bot' in secrets and 'token' in secrets['bot']:
                # Обновляем токен в конфигурации
                cfg.bot.token = secrets['bot']['token']
                logger.info("Токен бота успешно загружен из внешнего файла")
                return True
    except Exception as e:
        logger.error(f"Ошибка при загрузке секретов из {path}: {e}")
    
    logger.error("Не удалось загрузить секреты из внешних файлов")
    return False

async def main() -> None:
    """
    Initialize and start the Telegram bot.
    Асинхронная версия для aiogram 3.x
    """
    try:
        load_secrets(cfg, "../../../../ssh/bot.yaml")

        # Get bot token from configuration
        bot_token = cfg.bot.token if hasattr(cfg, "bot") and hasattr(cfg.bot, "token") else None
        if not bot_token:
            logger.error("Bot token is not set in configuration!")
            sys.exit(1)
        
        # Create bot and dispatcher instances
        bot = Bot(token=bot_token)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
                
        # Initialize API client из конфигурации Hydra
        api_base_url = cfg.api.base_url if hasattr(cfg, "api") and hasattr(cfg.api, "base_url") else "http://localhost:8500"
        api_timeout = int(cfg.api.timeout) if hasattr(cfg, "api") and hasattr(cfg.api, "timeout") else 5
        api_retry_count = int(cfg.api.retry_count) if hasattr(cfg, "api") and hasattr(cfg.api, "retry_count") else 3
        api_prefix = cfg.api.prefix if hasattr(cfg, "api") and hasattr(cfg.api, "prefix") else "/api"

        logger.info(f"Initializing API client with base URL: {api_base_url}, timeout: {api_timeout}, retry count: {api_retry_count}")

        api_client = APIClient(
            base_url=api_base_url,
            api_prefix=api_prefix,
            timeout=api_timeout,
            retry_count=api_retry_count
        )        
        # Сохраняем api_client используя утилиту
        store_api_client(bot, dp, api_client)
        
        # Устанавливаем middleware с инъекцией зависимостей
        dp.update.middleware(AuthMiddleware())
        
        # Create bot manager
        bot_manager = BotManager(bot, dp)
        
        # Сохраняем bot_manager в диспетчере для доступа в других местах
        dp["bot_manager"] = bot_manager
        
        # Регистрация обработчиков для запуска и остановки
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        logger.info("Starting polling...")
        
        # Получаем настройки запуска из конфигурации
        skip_updates = cfg.bot.skip_updates if hasattr(cfg, "bot") and hasattr(cfg.bot, "skip_updates") else False
        
        # Связываем диспетчера с ботом для возможности доступа к диспетчеру через бот
        # Это нестандартная операция, но она поможет в обработчиках получать api_client через message.bot.dispatcher
        setattr(bot, "dispatcher", dp)
        
        await dp.start_polling(
            bot,
            skip_updates=skip_updates,
        )

    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description='Запуск приложения')
        
        # Добавляем аргумент process-name для идентификации процесса
        parser.add_argument('--process-name', type=str, help='Имя процесса для идентификации')
        
        # Парсим аргументы, но не выходим при ошибке для обратной совместимости
        args, unknown = parser.parse_known_args()
        
        # Логируем информацию о запуске
        if args.process_name:
            logger.info(f"Запуск процесса с идентификатором: {args.process_name}")
        else:
            logger.info("Запуск процесса без идентификатора")
        
        # Логируем информацию о процессе
        pid = os.getpid()
        logger.info(f"ID процесса (PID): {pid}")
        logger.info(f"Рабочий каталог: {os.getcwd()}")

        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания.")
        logger.info("Завершение...")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        logger.info("Процесс завершен!")


