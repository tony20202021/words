#!/usr/bin/env python
"""
Script to update the index for user_statistics collection in MongoDB.
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

async def update_index():
    """Update the index for user_statistics collection."""
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[MONGODB_DB_NAME]
        
        logger.info(f"Connected to MongoDB at {MONGODB_URL}")
        
        # Drop the existing index
        try:
            await db.user_statistics.drop_index("user_id_1_word_id_1")
            logger.info("Existing index 'user_id_1_word_id_1' dropped")
        except Exception as e:
            logger.warning(f"Could not drop existing index: {e}")
        
        # Create a new index including language_id
        await db.user_statistics.create_index(
            [("user_id", 1), ("language_id", 1), ("word_id", 1)], 
            unique=True,
            name="user_language_word_index"
        )
        logger.info("Created new index 'user_language_word_index' on fields 'user_id', 'language_id', and 'word_id'")
        
        # Verify the new index
        indexes = await db.user_statistics.index_information()
        logger.info(f"Current indexes for user_statistics collection: {indexes}")
        
        logger.info("Index update completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to update index: {e}")
        raise
    finally:
        # Close MongoDB connection
        client.close()
        logger.info("MongoDB connection closed")

if __name__ == "__main__":
    logger.info("Starting index update...")
    asyncio.run(update_index())