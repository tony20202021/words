"""
Repository for user statistics operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bson.objectid import ObjectId

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.models.statistics import (
    UserStatisticsCreate, 
    UserStatisticsUpdate, 
    UserStatistics, 
    UserStatisticsInDB,
    UserProgress
)

class StatisticsRepository:
    """Repository for user statistics operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize repository.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection = db.user_statistics
    
    async def create(self, user_id: str, statistics: UserStatisticsCreate) -> UserStatisticsInDB:
        """
        Create user statistics for a word.
        
        Args:
            user_id: ID of the user
            statistics: Statistics data
            
        Returns:
            Created statistics
        """
        statistics_dict = statistics.dict()
        statistics_dict["user_id"] = user_id
        
        # Convert IDs from string to ObjectId for MongoDB
        if "word_id" in statistics_dict and isinstance(statistics_dict["word_id"], str):
            statistics_dict["word_id"] = statistics_dict["word_id"]  # Keep as string for easier lookup
        
        if "language_id" in statistics_dict and isinstance(statistics_dict["language_id"], str):
            statistics_dict["language_id"] = statistics_dict["language_id"]  # Keep as string for easier lookup
        
        statistics_dict["created_at"] = datetime.utcnow()
        statistics_dict["updated_at"] = statistics_dict["created_at"]
        
        result = await self.collection.insert_one(statistics_dict)
        
        created_stats = await self.collection.find_one({"_id": result.inserted_id})
        created_stats["id"] = str(created_stats.pop("_id"))
        
        return UserStatisticsInDB(**created_stats)
    
    async def get_by_id(self, id: str) -> Optional[UserStatisticsInDB]:
        """
        Get statistics by ID.
        
        Args:
            id: Statistics ID
            
        Returns:
            Statistics or None if not found
        """
        try:
            stats = await self.collection.find_one({"_id": ObjectId(id)})
            if stats:
                stats["id"] = str(stats.pop("_id"))
                return UserStatisticsInDB(**stats)
        except Exception:
            return None
        
        return None
    
    async def get_by_user_id(
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
            List of statistics
        """
        filters = {"user_id": user_id}
        
        if language_id:
            filters["language_id"] = language_id
        
        cursor = self.collection.find(filters).skip(skip).limit(limit).sort("updated_at", -1)
        
        stats_list = []
        async for stats in cursor:
            stats["id"] = str(stats.pop("_id"))
            stats_list.append(UserStatisticsInDB(**stats))
        
        return stats_list
    
    async def get_by_user_and_word(
        self, 
        user_id: str, 
        word_id: str
    ) -> Optional[UserStatisticsInDB]:
        """
        Get statistics for a specific user and word.
        
        Args:
            user_id: ID of the user
            word_id: ID of the word
            
        Returns:
            Statistics or None if not found
        """
        stats = await self.collection.find_one({
            "user_id": user_id,
            "word_id": word_id
        })
        
        if stats:
            stats["id"] = str(stats.pop("_id"))
            return UserStatisticsInDB(**stats)
        
        return None
    
    async def get_with_word_info(
        self, 
        user_id: str, 
        word_id: str
    ) -> Optional[UserStatistics]:
        """
        Get statistics with word information.
        
        Args:
            user_id: ID of the user
            word_id: ID of the word
            
        Returns:
            Statistics with word info or None if not found
        """
        pipeline = [
            {"$match": {"user_id": user_id, "word_id": word_id}},
            {
                "$lookup": {
                    "from": "words",
                    "let": {"wordId": "$word_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$eq": [{"$toString": "$_id"}, "$$wordId"]
                                }
                            }
                        }
                    ],
                    "as": "word"
                }
            },
            {"$unwind": {"path": "$word", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "_id": 1,
                    "user_id": 1,
                    "word_id": 1,
                    "language_id": 1,
                    "hint_syllables": 1,
                    "hint_association": 1,
                    "hint_meaning": 1,
                    "hint_writing": 1,
                    "score": 1,
                    "is_skipped": 1,
                    "next_check_date": 1,
                    "check_interval": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "word_foreign": "$word.word_foreign",
                    "translation": "$word.translation",
                    "transcription": "$word.transcription",
                    "word_number": "$word.word_number"
                }
            }
        ]
        
        cursor = self.collection.aggregate(pipeline)
        stats = None
        
        async for document in cursor:
            stats = document
            break
        
        if stats:
            stats["id"] = str(stats.pop("_id"))
            return UserStatistics(**stats)
        
        return None
    
    async def update(self, id: str, statistics: UserStatisticsUpdate) -> Optional[UserStatisticsInDB]:
        """
        Update statistics.
        
        Args:
            id: Statistics ID
            statistics: Updated statistics data
            
        Returns:
            Updated statistics or None if not found
        """
        statistics_dict = {k: v for k, v in statistics.dict().items() if v is not None}
        if not statistics_dict:
            # Nothing to update
            return await self.get_by_id(id)
        
        statistics_dict["updated_at"] = datetime.utcnow()
        
        try:
            await self.collection.update_one(
                {"_id": ObjectId(id)},
                {"$set": statistics_dict}
            )
            
            return await self.get_by_id(id)
        except Exception:
            return None
    
    async def update_by_user_and_word(
        self, 
        user_id: str, 
        word_id: str, 
        statistics: UserStatisticsUpdate
    ) -> Optional[UserStatisticsInDB]:
        """
        Update statistics by user ID and word ID.
        
        Args:
            user_id: ID of the user
            word_id: ID of the word
            statistics: Updated statistics data
            
        Returns:
            Updated statistics or None if not found
        """
        statistics_dict = {k: v for k, v in statistics.dict().items() if v is not None}
        if not statistics_dict:
            # Nothing to update
            return await self.get_by_user_and_word(user_id, word_id)
        
        statistics_dict["updated_at"] = datetime.utcnow()
        
        try:
            result = await self.collection.update_one(
                {"user_id": user_id, "word_id": word_id},
                {"$set": statistics_dict}
            )
            
            if result.matched_count == 0:
                return None
            
            return await self.get_by_user_and_word(user_id, word_id)
        except Exception:
            return None
    
    async def update_score_and_interval(
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
            Updated statistics or None if not found
        """
        # Get current statistics
        stats = await self.get_by_user_and_word(user_id, word_id)
        if not stats:
            return None
        
        update_data = UserStatisticsUpdate(score=score)
        
        # Calculate new check interval and next check date
        if score == 0:
            # If score is 0 (not known), reset interval
            update_data.check_interval = 0
            update_data.next_check_date = None
        else:
            # If score is 1 (known), increase interval using spaced repetition
            current_interval = stats.check_interval
            
            if current_interval == 0:
                # First successful review
                new_interval = 1
            else:
                # Double the interval, with a maximum of 32 days
                new_interval = min(current_interval * 2, 32)
            
            update_data.check_interval = new_interval
            update_data.next_check_date = datetime.utcnow() + timedelta(days=new_interval)
        
        # Update the statistics
        try:
            stats_id = stats.id
            return await self.update(stats_id, update_data)
        except Exception:
            return None
    
    async def delete(self, id: str) -> bool:
        """
        Delete statistics.
        
        Args:
            id: Statistics ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await self.collection.delete_one({"_id": ObjectId(id)})
            return result.deleted_count > 0
        except Exception:
            return False
    
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
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        pipeline = [
            # Match statistics for the user and language that are due for review
            {
                "$match": {
                    "user_id": user_id,
                    "language_id": language_id,
                    "next_check_date": {"$lte": today}
                }
            },
            
            # Join with words collection to get word details
            {
                "$lookup": {
                    "from": "words",
                    "let": {"wordId": "$word_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$eq": [{"$toString": "$_id"}, "$$wordId"]
                                }
                            }
                        }
                    ],
                    "as": "word"
                }
            },
            
            # Unwind word array to get single objects
            {"$unwind": "$word"},
            
            # Project only needed fields
            {
                "$project": {
                    "_id": 0,
                    "id": {"$toString": "$_id"},
                    "user_id": 1,
                    "word_id": 1,
                    "language_id": 1,
                    "score": 1,
                    "is_skipped": 1,
                    "check_interval": 1,
                    "next_check_date": 1,
                    "hint_syllables": 1,
                    "hint_association": 1,
                    "hint_meaning": 1,
                    "hint_writing": 1,
                    "word_foreign": "$word.word_foreign",
                    "translation": "$word.translation",
                    "transcription": "$word.transcription",
                    "word_number": "$word.word_number"
                }
            },
            
            # Sort by next_check_date, then by word_number
            {"$sort": {"next_check_date": 1, "word_number": 1}},
            
            # Skip and limit for pagination
            {"$skip": skip},
            {"$limit": limit}
        ]
        
        results = []
        try:
            cursor = self.collection.aggregate(pipeline)
            async for document in cursor:
                results.append(document)
            
            return results
        except Exception:
            return []
    
    async def get_user_progress(self, user_id: str, language_id: str) -> UserProgress:
        """
        Get user progress for a specific language.
        
        Args:
            user_id: ID of the user
            language_id: ID of the language
            
        Returns:
            User progress
        """
        try:
            # Get language info
            language = await self.db.languages.find_one({"_id": ObjectId(language_id)})
            if not language:
                raise ValueError(f"Language with ID {language_id} not found")
            
            # Count total words for the language
            total_words = await self.db.words.count_documents({"language_id": ObjectId(language_id)})
            
            # Count studied words (words with statistics)
            studied_words = await self.collection.count_documents({
                "user_id": user_id,
                "language_id": language_id
            })
            
            # Count known words (score = 1)
            known_words = await self.collection.count_documents({
                "user_id": user_id,
                "language_id": language_id,
                "score": 1
            })
            
            # Count skipped words
            skipped_words = await self.collection.count_documents({
                "user_id": user_id,
                "language_id": language_id,
                "is_skipped": True
            })
            
            # Calculate progress percentage
            progress_percentage = (known_words / total_words * 100) if total_words > 0 else 0
            
            # Get last study date
            last_study_stats = await self.collection.find_one(
                {"user_id": user_id, "language_id": language_id},
                sort=[("updated_at", -1)]
            )
            last_study_date = last_study_stats.get("updated_at") if last_study_stats else None
            
            return UserProgress(
                user_id=user_id,
                language_id=language_id,
                language_name_ru=language.get("name_ru", ""),
                language_name_foreign=language.get("name_foreign", ""),
                total_words=total_words,
                words_studied=studied_words,
                words_known=known_words,
                words_skipped=skipped_words,
                progress_percentage=round(progress_percentage, 2),
                last_study_date=last_study_date
            )
        except Exception as e:
            # Return empty progress on error
            return UserProgress(
                user_id=user_id,
                language_id=language_id,
                language_name_ru="",
                language_name_foreign="",
                total_words=0,
                words_studied=0,
                words_known=0,
                words_skipped=0,
                progress_percentage=0.0,
                last_study_date=None
            )