#!/usr/bin/env python
"""
Script to seed MongoDB database with test data for Language Learning Bot project.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId
import random

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

# Test data
LANGUAGES = [
    {"name_ru": "Английский", "name_foreign": "English"},
    {"name_ru": "Испанский", "name_foreign": "Español"},
    {"name_ru": "Французский", "name_foreign": "Français"},
    {"name_ru": "Китайский", "name_foreign": "中文"},
    {"name_ru": "Японский", "name_foreign": "日本語"},
]

# Sample English words with transcriptions and translations
ENGLISH_WORDS = [
    {"word_number": 1, "word_foreign": "the", "transcription": "[ðə, ði]", "translation": "определенный артикль"},
    {"word_number": 2, "word_foreign": "be", "transcription": "[bi]", "translation": "быть"},
    {"word_number": 3, "word_foreign": "to", "transcription": "[tu, tʊ]", "translation": "к, в, на"},
    {"word_number": 4, "word_foreign": "of", "transcription": "[əv, ʌv]", "translation": "из, от"},
    {"word_number": 5, "word_foreign": "and", "transcription": "[ænd, ənd]", "translation": "и"},
    {"word_number": 6, "word_foreign": "a", "transcription": "[eɪ, ə]", "translation": "неопределенный артикль"},
    {"word_number": 7, "word_foreign": "in", "transcription": "[ɪn]", "translation": "в, на, по"},
    {"word_number": 8, "word_foreign": "that", "transcription": "[ðæt]", "translation": "тот, что"},
    {"word_number": 9, "word_foreign": "have", "transcription": "[hæv]", "translation": "иметь"},
    {"word_number": 10, "word_foreign": "I", "transcription": "[aɪ]", "translation": "я"},
    {"word_number": 11, "word_foreign": "it", "transcription": "[ɪt]", "translation": "это, оно"},
    {"word_number": 12, "word_foreign": "for", "transcription": "[fɔr]", "translation": "для, за, в течение"},
    {"word_number": 13, "word_foreign": "not", "transcription": "[nɑt]", "translation": "не"},
    {"word_number": 14, "word_foreign": "on", "transcription": "[ɑn, ɔn]", "translation": "на, по, в"},
    {"word_number": 15, "word_foreign": "with", "transcription": "[wɪð, wɪθ]", "translation": "с, вместе с"},
]

# Sample Spanish words with transcriptions and translations
SPANISH_WORDS = [
    {"word_number": 1, "word_foreign": "el", "transcription": "[el]", "translation": "определенный артикль (м.р.)"},
    {"word_number": 2, "word_foreign": "de", "transcription": "[de]", "translation": "из, от"},
    {"word_number": 3, "word_foreign": "que", "transcription": "[ke]", "translation": "что, который"},
    {"word_number": 4, "word_foreign": "y", "transcription": "[i]", "translation": "и"},
    {"word_number": 5, "word_foreign": "a", "transcription": "[a]", "translation": "к, в, на"},
    {"word_number": 6, "word_foreign": "en", "transcription": "[en]", "translation": "в, на"},
    {"word_number": 7, "word_foreign": "un", "transcription": "[un]", "translation": "один, неопределенный артикль"},
    {"word_number": 8, "word_foreign": "ser", "transcription": "[seɾ]", "translation": "быть (постоянное свойство)"},
    {"word_number": 9, "word_foreign": "estar", "transcription": "[es'taɾ]", "translation": "быть (временное состояние)"},
    {"word_number": 10, "word_foreign": "haber", "transcription": "[a'βeɾ]", "translation": "иметь, вспомогательный глагол"},
]

# Sample users
USERS = [
    {"telegram_id": 111111111, "username": "user1", "first_name": "Иван", "last_name": "Иванов", "is_admin": True},
    {"telegram_id": 222222222, "username": "user2", "first_name": "Мария", "last_name": "Петрова", "is_admin": False},
    {"telegram_id": 333333333, "username": "user3", "first_name": "Алексей", "last_name": "Сидоров", "is_admin": False},
]

# Sample hints for statistics
SAMPLE_HINTS = [
    {"hint_syllables": "дэ", "hint_association": "ДЭнь наступил", "hint_meaning": "день", "hint_writing": ""},
    {"hint_syllables": "ту-дэй", "hint_association": "ТУшь ДАЙ", "hint_meaning": "сегодня", "hint_writing": ""},
    {"hint_syllables": "пи-пл", "hint_association": "ПИанино для ПЛемени", "hint_meaning": "люди", "hint_writing": ""},
]

async def seed_db():
    """Seed MongoDB database with test data."""
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[MONGODB_DB_NAME]
        
        logger.info(f"Connected to MongoDB at {MONGODB_URL}")
        
        # Check if collections are already populated
        languages_count = await db.languages.count_documents({})
        if languages_count > 0:
            logger.warning("Database already contains data. Do you want to continue and add more test data? (y/n)")
            answer = input().strip().lower()
            if answer != 'y':
                logger.info("Seeding cancelled by user.")
                return
        
        # Insert languages
        language_ids = {}
        for language in LANGUAGES:
            # Check if language already exists
            existing = await db.languages.find_one({"name_ru": language["name_ru"]})
            if existing:
                language_ids[language["name_ru"]] = existing["_id"]
                logger.info(f"Language '{language['name_ru']}' already exists with ID: {existing['_id']}")
                continue
                
            language_data = {
                **language,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            result = await db.languages.insert_one(language_data)
            language_ids[language["name_ru"]] = result.inserted_id
            logger.info(f"Added language: {language['name_ru']} with ID: {result.inserted_id}")
        
        # Insert English words
        english_id = language_ids.get("Английский")
        if english_id:
            word_ids = []
            for word in ENGLISH_WORDS:
                # Check if word already exists
                existing = await db.words.find_one({
                    "language_id": english_id,
                    "word_number": word["word_number"]
                })
                if existing:
                    word_ids.append(existing["_id"])
                    logger.info(f"Word '{word['word_foreign']}' already exists with ID: {existing['_id']}")
                    continue
                    
                word_data = {
                    **word,
                    "language_id": english_id,
                    "sound_file_path": "",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                result = await db.words.insert_one(word_data)
                word_ids.append(result.inserted_id)
                logger.info(f"Added English word: {word['word_foreign']} with ID: {result.inserted_id}")
        
        # Insert Spanish words
        spanish_id = language_ids.get("Испанский")
        if spanish_id:
            for word in SPANISH_WORDS:
                # Check if word already exists
                existing = await db.words.find_one({
                    "language_id": spanish_id,
                    "word_number": word["word_number"]
                })
                if existing:
                    logger.info(f"Word '{word['word_foreign']}' already exists with ID: {existing['_id']}")
                    continue
                    
                word_data = {
                    **word,
                    "language_id": spanish_id,
                    "sound_file_path": "",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                result = await db.words.insert_one(word_data)
                logger.info(f"Added Spanish word: {word['word_foreign']} with ID: {result.inserted_id}")
        
        # Insert users
        user_ids = []
        for user in USERS:
            # Check if user already exists
            existing = await db.users.find_one({"telegram_id": user["telegram_id"]})
            if existing:
                user_ids.append(existing["_id"])
                logger.info(f"User '{user['username']}' already exists with ID: {existing['_id']}")
                continue
                
            user_data = {
                **user,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            result = await db.users.insert_one(user_data)
            user_ids.append(result.inserted_id)
            logger.info(f"Added user: {user['username']} with ID: {result.inserted_id}")
        
        # Generate some statistics for users
        if english_id and word_ids and user_ids:
            for user_id in user_ids:
                # Create statistics for 5 random words for each user
                for i in range(5):
                    word_id = random.choice(word_ids)
                    
                    # Check if statistics already exist
                    existing = await db.user_statistics.find_one({
                        "user_id": user_id,
                        "language_id": english_id,  # Добавлено поле language_id
                        "word_id": word_id
                    })
                    if existing:
                        logger.info(f"Statistics for user {user_id}, language {english_id} and word {word_id} already exist")
                        continue
                    
                    # Random sample hint
                    hint = random.choice(SAMPLE_HINTS)
                    
                    # Random score and check interval
                    score = random.choice([0, 1])
                    check_interval = 2 ** random.randint(0, 5) if score == 1 else 0
                    next_check_date = datetime.utcnow() + timedelta(days=check_interval) if check_interval > 0 else None
                    
                    stats_data = {
                        "user_id": user_id,
                        "language_id": english_id,  # Добавлено поле language_id
                        "word_id": word_id,
                        **hint,
                        "score": score,
                        "is_skipped": random.choice([True, False]),
                        "next_check_date": next_check_date,
                        "check_interval": check_interval,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                    
                    result = await db.user_statistics.insert_one(stats_data)
                    logger.info(f"Added statistics for user {user_id}, language {english_id} and word {word_id} with ID: {result.inserted_id}")
                    

        logger.info("Database seeding completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to seed database: {e}")
        raise
    finally:
        # Close MongoDB connection
        client.close()
        logger.info("MongoDB connection closed")

if __name__ == "__main__":
    logger.info("Starting database seeding...")
    asyncio.run(seed_db())