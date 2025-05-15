"""
Database configuration for the backend application using MongoDB.
Supports both .env and Hydra configuration.
"""

import logging
import os
from typing import Optional, AsyncGenerator

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from fastapi import Depends
from app.utils.logger import setup_logger

# Попытка импорта Hydra - если он доступен, будет использоваться для конфигурации
try:
    from hydra import compose, initialize
    from omegaconf import OmegaConf
    hydra_available = True
except ImportError:
    hydra_available = False

# Загрузка переменных окружения
load_dotenv()

# Настройка логгера
logger = setup_logger(__name__)

# Клиент MongoDB
client: Optional[AsyncIOMotorClient] = None
db: Optional[AsyncIOMotorDatabase] = None

def get_mongodb_config():
    """
    Получает конфигурацию MongoDB из Hydra или переменных окружения.
    
    Returns:
        tuple: (mongodb_url, mongodb_db_name, connection_options)
    """
    # Значения по умолчанию
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_db_name = os.getenv("MONGODB_DB_NAME", "language_learning_bot")
    connection_options = {}
    
    # Если доступен Hydra, пытаемся получить конфигурацию из него
    if hydra_available:
        try:
            # Определяем, инициализирован ли уже Hydra
            if not hasattr(get_mongodb_config, "_hydra_initialized"):
                initialize(config_path="../conf/config", version_base=None)
                get_mongodb_config._hydra_initialized = True
            
            # Получаем конфигурацию
            cfg = compose(config_name="default")
            
            # Извлекаем настройки MongoDB из конфигурации
            if hasattr(cfg, "database") and hasattr(cfg.database, "mongodb"):
                mongodb_cfg = cfg.database.mongodb
                
                # URL для подключения
                if hasattr(mongodb_cfg, "url"):
                    mongodb_url = mongodb_cfg.url
                
                # Имя базы данных
                if hasattr(mongodb_cfg, "db_name"):
                    mongodb_db_name = mongodb_cfg.db_name
                
                # Настройки пула соединений
                connection_options = {}
                
                if hasattr(mongodb_cfg, "min_pool_size"):
                    connection_options["minPoolSize"] = mongodb_cfg.min_pool_size
                
                if hasattr(mongodb_cfg, "max_pool_size"):
                    connection_options["maxPoolSize"] = mongodb_cfg.max_pool_size
                
                if hasattr(mongodb_cfg, "connection_timeout_ms"):
                    connection_options["connectTimeoutMS"] = mongodb_cfg.connection_timeout_ms
                
                # Настройки аутентификации
                if hasattr(mongodb_cfg, "auth") and hasattr(mongodb_cfg.auth, "enabled") and mongodb_cfg.auth.enabled:
                    if hasattr(mongodb_cfg.auth, "username"):
                        connection_options["username"] = mongodb_cfg.auth.username
                    
                    if hasattr(mongodb_cfg.auth, "password"):
                        connection_options["password"] = mongodb_cfg.auth.password
                    
                    if hasattr(mongodb_cfg.auth, "auth_source"):
                        connection_options["authSource"] = mongodb_cfg.auth.auth_source
                    else:
                        connection_options["authSource"] = "admin"
                
                logger.info("MongoDB configuration loaded from Hydra")
            
        except Exception as e:
            logger.warning(f"Failed to load MongoDB config from Hydra: {e}")
            logger.info("Using default or .env configuration")
    
    return mongodb_url, mongodb_db_name, connection_options

async def connect_to_mongo():
    """Устанавливает соединение с MongoDB."""
    global client, db
    try:
        mongodb_url, mongodb_db_name, connection_options = get_mongodb_config()
        
        logger.info(f"Connecting to MongoDB at {mongodb_url}, database: {mongodb_db_name}")
        
        # Создаем клиента MongoDB с настройками
        client = AsyncIOMotorClient(mongodb_url, **connection_options)
        db = client[mongodb_db_name]
        
        logger.info("Successfully connected to MongoDB")
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}", exc_info=True)
        raise

async def close_mongo_connection():
    """Закрывает соединение с MongoDB."""
    global client
    if client:
        client.close()
        logger.info("Closed connection to MongoDB")

def get_database() -> AsyncIOMotorDatabase:
    """
    Возвращает объект базы данных MongoDB.
    
    Returns:
        AsyncIOMotorDatabase: Объект базы данных MongoDB
    """
    if db is None:
        raise Exception("Database not initialized. Call connect_to_mongo() first.")
    return db

async def get_db_session() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """
    Асинхронный генератор для получения сессии базы данных.
    Используется как зависимость FastAPI.
    
    Yields:
        AsyncIOMotorDatabase: Объект базы данных MongoDB
    """
    if db is None:
        await connect_to_mongo()
    try:
        yield db
    except Exception as e:
        logger.error(f"Error in database session: {e}")
        raise

# Зависимость для FastAPI
def get_db():
    """
    Возвращает зависимость для использования в FastAPI.
    
    Returns:
        Depends: Зависимость FastAPI для получения сессии базы данных
    """
    return Depends(get_db_session)