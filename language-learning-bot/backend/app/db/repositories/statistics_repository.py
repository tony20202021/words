"""
Repository for user statistics operations.
"""

import asyncio
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
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


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
        limit: int = 100,
        validate_words: bool = False
    ) -> List[UserStatisticsInDB]:
        """
        Get statistics for a specific user with optional language filter.
        ОПТИМИЗИРОВАНО: добавлена валидация слов и правильный порядок операций.
        
        Args:
            user_id: ID of the user
            language_id: Optional ID of the language to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            validate_words: If True, only return statistics for existing words
            
        Returns:
            List of statistics
        """
        if not validate_words:
            # Старая быстрая логика без валидации
            filters = {"user_id": user_id}
            if language_id:
                filters["language_id"] = language_id
            
            cursor = self.collection.find(filters).skip(skip).limit(limit).sort("updated_at", -1)
            
            stats_list = []
            async for stats in cursor:
                stats["id"] = str(stats.pop("_id"))
                stats_list.append(UserStatisticsInDB(**stats))
            
            return stats_list
        else:
            # ОПТИМИЗИРОВАННАЯ логика: сначала пагинация, потом валидация
            match_stage = {"user_id": user_id}
            if language_id:
                match_stage["language_id"] = language_id
            
            pipeline = [
                {"$match": match_stage},
                {"$sort": {"updated_at": -1}},
                {"$skip": skip},
                {"$limit": limit},  # ❗ КЛЮЧЕВОЕ: пагинация ДО JOIN
                
                # JOIN только для отобранных записей
                {
                    "$lookup": {
                        "from": "words",
                        "let": {"word_id_str": "$word_id"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$eq": [{"$toString": "$_id"}, "$$word_id_str"]
                                    }
                                }
                            },
                            {"$project": {"_id": 1}}  # Минимальная проекция для скорости
                        ],
                        "as": "word_exists"
                    }
                },
                
                # Фильтруем только существующие слова
                {"$match": {"word_exists": {"$ne": []}}},
                
                # Убираем служебное поле
                {"$project": {"word_exists": 0}}
            ]
            
            stats_list = []
            cursor = self.collection.aggregate(pipeline)
            async for stats in cursor:
                stats["id"] = str(stats.pop("_id"))
                stats_list.append(UserStatisticsInDB(**stats))
            
            return stats_list
    
    async def count_user_statistics(
        self,
        user_id: str,
        language_id: Optional[str] = None,
        validate_words: bool = False
    ) -> int:
        """
        НОВЫЙ МЕТОД: Подсчет статистики пользователя без получения записей.
        НАМНОГО быстрее чем get_by_user_id + len().
        
        Args:
            user_id: ID пользователя
            language_id: Опционально ID языка
            validate_words: Проверять существование слов
            
        Returns:
            Количество записей статистики
        """
        if not validate_words:
            # Простой подсчет без валидации - ОЧЕНЬ быстро
            filters = {"user_id": user_id}
            if language_id:
                filters["language_id"] = language_id
            
            return await self.collection.count_documents(filters)
        else:
            # Подсчет с валидацией через aggregation
            match_stage = {"user_id": user_id}
            if language_id:
                match_stage["language_id"] = language_id
            
            pipeline = [
                {"$match": match_stage},
                
                # JOIN для проверки существования слов
                {
                    "$lookup": {
                        "from": "words",
                        "let": {"word_id_str": "$word_id"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$eq": [{"$toString": "$_id"}, "$$word_id_str"]
                                    }
                                }
                            },
                            {"$project": {"_id": 1}}  # Минимальная проекция для скорости
                        ],
                        "as": "word_exists"
                    }
                },
                
                # Фильтруем только существующие слова
                {"$match": {"word_exists": {"$ne": []}}},
                
                # ❗ КЛЮЧЕВОЕ: только подсчет, без возврата данных
                {"$count": "total"}
            ]
            
            cursor = self.collection.aggregate(pipeline)
            result = await cursor.to_list(length=1)
            
            return result[0]["total"] if result else 0

    async def count_user_statistics_by_conditions(
        self,
        user_id: str,
        language_id: str,
        validate_words: bool = True
    ) -> Dict[str, int]:
        """
        НОВЫЙ МЕТОД: Подсчет всех метрик одним запросом - МАКСИМАЛЬНО эффективно.
        Заменяет множественные вызовы count_documents().
        
        Returns:
            Dict с ключами: words_studied, words_known, words_skipped
        """
        match_stage = {
            "user_id": user_id,
            "language_id": language_id
        }
        
        if validate_words:
            # С валидацией существования слов
            pipeline = [
                {"$match": match_stage},
                
                # JOIN для проверки существования слов
                {
                    "$lookup": {
                        "from": "words",
                        "let": {"word_id_str": "$word_id"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$eq": [{"$toString": "$_id"}, "$$word_id_str"]
                                    }
                                }
                            },
                            {"$project": {"_id": 1}}  # Минимальная проекция
                        ],
                        "as": "word_exists"
                    }
                },
                
                # Только существующие слова
                {"$match": {"word_exists": {"$ne": []}}},
                
                # ❗ Подсчет всех метрик ОДНИМ запросом
                {
                    "$group": {
                        "_id": None,
                        "words_studied": {"$sum": 1},  # Общее количество
                        "words_known": {
                            "$sum": {"$cond": [{"$eq": ["$score", 1]}, 1, 0]}
                        },
                        "words_skipped": {
                            "$sum": {"$cond": [{"$eq": ["$is_skipped", True]}, 1, 0]}
                        }
                    }
                }
            ]
        else:
            # Без валидации - еще быстрее
            pipeline = [
                {"$match": match_stage},
                {
                    "$group": {
                        "_id": None,
                        "words_studied": {"$sum": 1},
                        "words_known": {
                            "$sum": {"$cond": [{"$eq": ["$score", 1]}, 1, 0]}
                        },
                        "words_skipped": {
                            "$sum": {"$cond": [{"$eq": ["$is_skipped", True]}, 1, 0]}
                        }
                    }
                }
            ]
        
        cursor = self.collection.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        
        if result:
            return {
                "words_studied": result[0]["words_studied"],
                "words_known": result[0]["words_known"], 
                "words_skipped": result[0]["words_skipped"]
            }
        else:
            return {
                "words_studied": 0,
                "words_known": 0,
                "words_skipped": 0
            }

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
                    "hint_phoneticsound": 1,
                    "hint_phoneticassociation": 1,
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
        ПРОВЕРЕНО: уже использует JOIN и корректно фильтрует существующие слова.
        
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
            
            # Join with words collection to get word details - КОРРЕКТНО
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
            
            # Unwind word array - только статистика с существующими словами попадет дальше
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
                    "hint_phoneticsound": 1,
                    "hint_phoneticassociation": 1,
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
        УЛЬТРА-ОПТИМИЗИРОВАНО: использует минимальное количество запросов и эффективные aggregation pipelines.
        
        Args:
            user_id: ID of the user
            language_id: ID of the language
            
        Returns:
            User progress
        """
        try:
            # 1. Получаем информацию о языке и общее количество слов параллельно
            language_task = self.db.languages.find_one({"_id": ObjectId(language_id)})
            total_words_task = self.db.words.count_documents({"language_id": ObjectId(language_id)})
            
            # ❗ Параллельное выполнение для скорости
            language, total_words = await asyncio.gather(language_task, total_words_task)
            
            if not language:
                raise ValueError(f"Language with ID {language_id} not found")
            
            # 2. Получаем все метрики статистики одним оптимизированным запросом
            stats_counts = await self.count_user_statistics_by_conditions(
                user_id=user_id,
                language_id=language_id,
                validate_words=True  # С валидацией существующих слов
            )
            
            # 3. Получаем последнюю дату изучения отдельным быстрым запросом
            last_study_cursor = self.collection.find(
                {"user_id": user_id, "language_id": language_id},
                {"updated_at": 1}  # ❗ Проекция только нужного поля
            ).sort("updated_at", -1).limit(1)
            
            last_study_docs = await last_study_cursor.to_list(length=1)
            last_study_date = last_study_docs[0]["updated_at"] if last_study_docs else None
            
            # 4. Вычисляем прогресс
            progress_percentage = (
                stats_counts["words_known"] / total_words * 100
            ) if total_words > 0 else 0
            
            return UserProgress(
                user_id=user_id,
                language_id=language_id,
                language_name_ru=language.get("name_ru", ""),
                language_name_foreign=language.get("name_foreign", ""),
                total_words=total_words,
                words_studied=stats_counts["words_studied"],
                words_known=stats_counts["words_known"],
                words_skipped=stats_counts["words_skipped"],
                progress_percentage=round(progress_percentage, 2),
                last_study_date=last_study_date
            )
            
        except Exception as e:
            logger.error(f"Error getting user progress: {e}", exc_info=True)
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

    async def get_data_integrity_report(self) -> Dict[str, Any]:
        """
        НОВЫЙ МЕТОД: Отчет о целостности данных - какой процент статистики имеет мертвые ссылки.
        """
        # Общее количество записей статистики
        total_stats = await self.collection.count_documents({})
        
        # Количество записей с существующими словами
        pipeline = [
            {
                "$lookup": {
                    "from": "words",
                    "let": {"word_id_str": "$word_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$eq": [{"$toString": "$_id"}, "$$word_id_str"]
                                }
                            }
                        },
                        {"$project": {"_id": 1}}
                    ],
                    "as": "word_exists"
                }
            },
            {"$match": {"word_exists": {"$ne": []}}},
            {"$count": "valid_stats"}
        ]
        
        cursor = self.collection.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        valid_stats = result[0]["valid_stats"] if result else 0
        
        orphaned_stats = total_stats - valid_stats
        orphaned_percentage = (orphaned_stats / total_stats * 100) if total_stats > 0 else 0
        
        return {
            "total_statistics": total_stats,
            "valid_statistics": valid_stats, 
            "orphaned_statistics": orphaned_stats,
            "orphaned_percentage": round(orphaned_percentage, 2)
        }
    