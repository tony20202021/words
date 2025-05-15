#!/usr/bin/env python
"""
Script to initialize MongoDB database for Language Learning Bot project.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# MongoDB connection settings
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "language_learning_bot")

async def init_db():
    """Initialize MongoDB database and collections."""
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[MONGODB_DB_NAME]
        
        logger.info(f"Connected to MongoDB at {MONGODB_URL}")
        
        # Create collections if they don't exist
        collections = await db.list_collection_names()
        
        # Languages collection
        if "languages" not in collections:
            await db.create_collection("languages")
            logger.info("Created 'languages' collection")
            
            # Create indexes
            await db.languages.create_index("name_ru", unique=True)
            logger.info("Created index on 'name_ru' field in 'languages' collection")
        
        # Words collection
        if "words" not in collections:
            await db.create_collection("words")
            logger.info("Created 'words' collection")
            
            # Create indexes
            await db.words.create_index([("language_id", 1), ("word_number", 1)], unique=True)
            logger.info("Created index on 'language_id' and 'word_number' fields in 'words' collection")
        
        # Users collection
        if "users" not in collections:
            await db.create_collection("users")
            logger.info("Created 'users' collection")
            
            # Create indexes
            await db.users.create_index("telegram_id", unique=True)
            logger.info("Created index on 'telegram_id' field in 'users' collection")
        
        # User statistics collection
        if "user_statistics" not in collections:
            await db.create_collection("user_statistics")
            logger.info("Created 'user_statistics' collection")
            
            # Create indexes
            await db.user_statistics.create_index([("user_id", 1), ("word_id", 1)], unique=True)
            logger.info("Created index on 'user_id' and 'word_id' fields in 'user_statistics' collection")
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        # Close MongoDB connection
        client.close()
        logger.info("MongoDB connection closed")

if __name__ == "__main__":
    logger.info("Starting database initialization...")
    asyncio.run(init_db())