#!/usr/bin/env python
"""
Скрипт для создания коллекции user_language_settings в MongoDB.
"""
import asyncio
import sys
import os
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# MongoDB connection settings
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "language_learning_bot")


async def create_collection():
    """
    Создает коллекцию user_language_settings и индексы для нее.
    """
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[MONGODB_DB_NAME]
        
        logger.info(f"Connected to MongoDB at {MONGODB_URL}")
        logger.info("Creating user_language_settings collection...")
        
        # Проверяем, существует ли уже коллекция
        collections = await db.list_collection_names()
        if "user_language_settings" in collections:
            logger.info("Collection user_language_settings already exists. Skipping creation.")
        else:
            # Создаем коллекцию
            await db.create_collection("user_language_settings")
            logger.info("Collection user_language_settings created successfully.")
        
        # Проверяем существующие индексы
        existing_indexes = await db.user_language_settings.index_information()
        composite_index_exists = any('user_id_1_language_id_1' in idx_name for idx_name in existing_indexes)
        
        if not composite_index_exists:
            # Создаем уникальный составной индекс для user_id и language_id
            await db.user_language_settings.create_index(
                [("user_id", 1), ("language_id", 1)],
                unique=True
            )
            logger.info("Created unique index on user_id and language_id.")
        else:
            logger.info("Index on user_id and language_id already exists.")
        
        logger.info("Collection user_language_settings setup completed.")
        
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        raise
    finally:
        # Close MongoDB connection
        client.close()
        logger.info("MongoDB connection closed")


async def main():
    """
    Основная функция скрипта.
    """
    try:
        logger.info("Starting user_language_settings collection creation...")
        
        # Создаем коллекцию и индексы
        await create_collection()
        
        logger.info("User language settings setup completed successfully.")
    except Exception as e:
        logger.error(f"Error setting up user language settings: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    logger.info("Starting database initialization...")
    asyncio.run(main())

# python scripts/create_user_language_settings_collection.py