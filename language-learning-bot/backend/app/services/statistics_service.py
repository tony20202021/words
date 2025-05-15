"""
Service for statistics operations.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bson.objectid import ObjectId

from app.db.repositories.statistics_repository import StatisticsRepository
from app.db.repositories.word_repository import WordRepository
from app.api.models.statistics import (
    UserStatisticsCreate, 
    UserStatisticsUpdate, 
    UserStatistics, 
    UserStatisticsInDB,
    UserProgress
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class StatisticsService:
    """Service for handling statistics operations."""
    
    def __init__(self, repository: StatisticsRepository, word_repository: WordRepository):
        """
        Initialize the statistics service.
        
        Args:
            repository: Statistics repository instance
            word_repository: Word repository instance
        """
        self.repository = repository
        self.word_repository = word_repository
    
    async def get_user_statistics(
        self, 
        user_id: str, 
        language_id: Optional[str] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> List[UserStatisticsInDB]:
        """
        Get statistics for a specific user with optional language filter.
        
        Args:
            user_id: ID of the user
            language_id: Optional ID of the language to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of statistics objects
        """
        return await self.repository.get_by_user_id(
            user_id=user_id,
            language_id=language_id,
            skip=skip,
            limit=limit
        )
    
    async def get_user_word_statistics(
        self, 
        user_id: str, 
        word_id: str
    ) -> Optional[UserStatistics]:
        """
        Get statistics for a specific user and word.
        
        Args:
            user_id: ID of the user
            word_id: ID of the word
            
        Returns:
            Statistics object or None if not found
        """
        return await self.repository.get_with_word_info(
            user_id=user_id,
            word_id=word_id
        )
    
    async def create_user_word_statistics(
        self, 
        user_id: str, 
        statistics: UserStatisticsCreate
    ) -> UserStatisticsInDB:
        """
        Create user statistics for a word.
        
        Args:
            user_id: ID of the user
            statistics: Statistics data
            
        Returns:
            Created statistics object
        """
        return await self.repository.create(user_id, statistics)
    
    async def update_user_word_statistics(
        self, 
        user_id: str, 
        word_id: str, 
        statistics: UserStatisticsUpdate
    ) -> Optional[UserStatisticsInDB]:
        """
        Update statistics for a specific user and word.
        
        Args:
            user_id: ID of the user
            word_id: ID of the word
            statistics: Updated statistics data
            
        Returns:
            Updated statistics object or None if not found
        """
        return await self.repository.update_by_user_and_word(
            user_id=user_id,
            word_id=word_id,
            statistics=statistics
        )
    
    async def update_score(
        self, 
        user_id: str, 
        word_id: str, 
        score: int
    ) -> Optional[UserStatisticsInDB]:
        """
        Update score and adjust check interval and next check date based on spaced repetition algorithm.
        
        Args:
            user_id: ID of the user
            word_id: ID of the word
            score: New score (0 or 1)
            
        Returns:
            Updated statistics object or None if not found
        """
        return await self.repository.update_score_and_interval(
            user_id=user_id,
            word_id=word_id,
            score=score
        )
    
    async def get_words_for_review(
        self, 
        user_id: str, 
        language_id: str,
        skip: int = 0, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get words due for review today.
        
        Args:
            user_id: ID of the user
            language_id: ID of the language
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of statistics with word information
        """
        # Use the repository to get words for review
        return await self.repository.get_words_for_review(
            user_id=user_id,
            language_id=language_id,
            skip=skip,
            limit=limit
        )
    
    async def get_user_progress(
        self, 
        user_id: str, 
        language_id: str
    ) -> UserProgress:
        """
        Get user progress for a specific language.
        
        Args:
            user_id: ID of the user
            language_id: ID of the language
            
        Returns:
            User progress object
        """
        return await self.repository.get_user_progress(
            user_id=user_id,
            language_id=language_id
        )
  
    async def get_words_for_study(
        self,
        user_id: str,
        language_id: str,
        start_word: int = 1,
        skip_marked: bool = False,
        use_check_date: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get words for study with various filters.
        
        Args:
            user_id: The user ID
            language_id: The language ID
            start_word: The word number to start from 
            skip_marked: Whether to skip marked words
            use_check_date: Whether to consider next check date
            skip: Number of records to skip
            limit: Maximum number of words to return
            
        Returns:
            List of words for study
        """
        logger.info(f"Getting words for study: user_id={user_id}, language_id={language_id}, "
                f"start_word={start_word}, skip_marked={skip_marked}, "
                f"use_check_date={use_check_date}, skip={skip}, limit={limit}")
                
        # Get all words for the language that have word_number >= start_word
        # Добавлен этап $addFields для преобразования ObjectId в строки
        pipeline = [
            {"$match": {"language_id": ObjectId(language_id), "word_number": {"$gte": start_word}}},
            {"$sort": {"word_number": 1}},
            {"$skip": skip},
            {"$limit": limit},
            # Преобразуем ObjectId в строки
            {
                "$addFields": {
                    "_id": {"$toString": "$_id"},
                    "language_id": {"$toString": "$language_id"}
                }
            }
        ]
        
        logger.debug(f"MongoDB pipeline for words: {pipeline}")
        
        words_cursor = self.word_repository.collection.aggregate(pipeline)
        words = await words_cursor.to_list(length=None)
        
        logger.info(f"Found {len(words)} words in language_id={language_id} with word_number >= {start_word}")
        
        # Если нет слов, сразу возвращаем пустой список
        if not words:
            logger.warning(f"No words found for language_id={language_id} with word_number >= {start_word}")
            return []
        
        # Независимо от фильтрации, нам нужно получить статистику пользователя для всех слов
        # Get user statistics for these words
        word_ids = [word.get("_id") for word in words]
        
        logger.debug(f"Looking for statistics with user_id={user_id} and word_ids in {word_ids}")
        
        statistics_cursor = self.repository.collection.find({
            "user_id": user_id,
            "word_id": {"$in": word_ids}
        })
        statistics = await statistics_cursor.to_list(length=None)
        
        logger.info(f"Found {len(statistics)} statistics records for user_id={user_id}")
        
        # Преобразуем ObjectId в строки в статистике
        for stat in statistics:
            if "_id" in stat and isinstance(stat["_id"], ObjectId):
                stat["_id"] = str(stat["_id"])
            if "user_id" in stat and isinstance(stat["user_id"], ObjectId):
                stat["user_id"] = str(stat["user_id"])
            if "word_id" in stat and isinstance(stat["word_id"], ObjectId):
                stat["word_id"] = str(stat["word_id"])
            if "language_id" in stat and isinstance(stat["language_id"], ObjectId):
                stat["language_id"] = str(stat["language_id"])
        
        # Create a dictionary of statistics by word_id for quick lookup
        statistics_by_word_id = {stat.get("word_id"): stat for stat in statistics}
        
        # Если фильтрация не нужна, просто добавим статистику к словам и вернем все слова
        if not skip_marked and not use_check_date:
            logger.info("No filtering needed, adding statistics to words and returning all words")
            
            # Добавляем данные пользователя к словам, если они есть
            for word in words:
                word_id = word.get("_id")
                stats = statistics_by_word_id.get(word_id)
                
                if stats:
                    word["user_word_data"] = stats
                    
            return words
        
        # В противном случае, применяем фильтрацию
        filtered_words = []
        now = datetime.now()
        
        # Apply filters
        for word in words:
            word_id = word.get("_id")
            stats = statistics_by_word_id.get(word_id)
            
            # Skip this word if it has stats and we need to filter
            if stats:
                # Skip marked words if requested
                if skip_marked and stats.get("is_skipped", False):
                    logger.debug(f"Skipping word_id={word_id} because it is marked and skip_marked={skip_marked}")
                    continue
                    
                # Skip words that are not due for review if requested
                if use_check_date and stats.get("next_check_date"):
                    next_check = stats.get("next_check_date")
                    if next_check > now:
                        logger.debug(f"Skipping word_id={word_id} because next_check_date is in future: {next_check}")
                        continue
            
            # Add user word data if available
            if stats:
                word["user_word_data"] = stats
                
            filtered_words.append(word)
        
        logger.info(f"After filtering, {len(filtered_words)} words remain for study")
        
        return filtered_words
