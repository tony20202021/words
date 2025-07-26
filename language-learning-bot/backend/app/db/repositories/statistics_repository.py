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
    UserProgress,
    UserMonthlyStats,
    UserDailyStatsInDB,
    UserDailyStatsUpdate
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
        self.daily_stats_collection = db.user_daily_statistics
    
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
    ) -> Dict[str, Any]:
        """
        Подсчет всех метрик + списки номеров слов одним запросом.
        все данные получаются одним aggregation pipeline.
        
        Returns:
            Dict с ключами: counts + lists
        """
        match_stage = {
            "user_id": user_id,
            "language_id": language_id
        }
        
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        if validate_words:
            # С валидацией существования слов + получение word_number
            pipeline = [
                {"$match": match_stage},
                
                # JOIN для проверки существования слов + получение word_number
                {
                    "$lookup": {
                        "from": "words",
                        "let": {"word_id_str": "$word_id"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$eq": [{"$toObjectId": "$$word_id_str"}, "$_id"]
                                    }
                                }
                            },
                            {"$project": {"word_number": 1}}  # 🆕 Получаем word_number
                        ],
                        "as": "word_info"
                    }
                },
                
                # Только существующие слова
                {"$match": {"word_info": {"$ne": []}}},
                
                # Извлекаем word_number из массива
                {"$addFields": {"word_number": {"$arrayElemAt": ["$word_info.word_number", 0]}}},
                
                # 🆕 подсчет + группировка списков в одном $group
                {
                    "$group": {
                        "_id": None,
                        "words_studied": {"$sum": 1},
                        "words_known": {
                            "$sum": {"$cond": [{"$eq": ["$score", 1]}, 1, 0]}
                        },
                        "words_skipped": {
                            "$sum": {"$cond": [{"$eq": ["$is_skipped", True]}, 1, 0]}
                        },
                        "words_for_today": {                        
                            "$sum": {"$cond": [{"$lte": ["$next_check_date", today]}, 1, 0]}
                        },
                        
                        # 🆕 списки номеров слов
                        "word_numbers_for_today": {
                            "$push": {
                                "$cond": [
                                    {"$lte": ["$next_check_date", today]},
                                    "$word_number",
                                    "$$REMOVE"  # Исключаем из списка если условие не выполнено
                                ]
                            }
                        },
                        "word_numbers_unknown": {
                            "$push": {
                                "$cond": [
                                    # score = 0 И НЕ пропущено
                                    {"$and": [
                                        {"$eq": ["$score", 0]},
                                        {"$ne": ["$is_skipped", True]}
                                    ]},
                                    "$word_number",
                                    "$$REMOVE"
                                ]
                            }
                        }
                    }
                },
                
                # 🆕 Сортируем списки номеров слов
                {
                    "$addFields": {
                        "word_numbers_for_today": {"$sortArray": {"input": "$word_numbers_for_today", "sortBy": 1}},
                        "word_numbers_unknown": {"$sortArray": {"input": "$word_numbers_unknown", "sortBy": 1}}
                    }
                }
            ]
        else:
            # Упрощенная версия без валидации - НО БЕЗ word_number
            # (нужен отдельный запрос для получения word_number без валидации)
            raise NotImplementedError("Without validation, word_number is not available in statistics")
        
        cursor = self.collection.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        
        if result:
            return {
                "words_studied": result[0]["words_studied"],
                "words_known": result[0]["words_known"], 
                "words_skipped": result[0]["words_skipped"],
                "words_for_today": result[0]["words_for_today"],
                "word_numbers_for_today": result[0]["word_numbers_for_today"],
                "word_numbers_unknown": result[0]["word_numbers_unknown"]
            }
        else:
            return {
                "words_studied": 0,
                "words_known": 0,
                "words_skipped": 0,
                "words_for_today": 0,
                "word_numbers_for_today": [],
                "word_numbers_unknown": []
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
                    "let": {"word_id_str": "$word_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    # "$eq": [{"$toString": "$_id"}, "$$wordId"]
                                    "$eq": [{"$toObjectId": "$$word_id_str"}, "$_id"]
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
        использует минимальное количество запросов и эффективные aggregation pipelines.
        
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
            stats_data  = await self.count_user_statistics_by_conditions(
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
                stats_data["words_known"] / total_words * 100
            ) if total_words > 0 else 0
            
            return UserProgress(
                user_id=user_id,
                language_id=language_id,
                language_name_ru=language.get("name_ru", ""),
                language_name_foreign=language.get("name_foreign", ""),
                total_words=total_words,
                words_studied=stats_data["words_studied"],
                words_known=stats_data["words_known"],
                words_skipped=stats_data["words_skipped"],
                words_for_today=stats_data["words_for_today"],
                progress_percentage=round(progress_percentage, 2),
                last_study_date=last_study_date,
                word_numbers_for_today=stats_data["word_numbers_for_today"],
                word_numbers_unknown=stats_data["word_numbers_unknown"]
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
                words_for_today=0,
                progress_percentage=0.0,
                last_study_date=None,
                word_numbers_for_today=[],
                word_numbers_unknown=[]
            )

    async def get_data_integrity_report(self) -> Dict[str, Any]:
        """
        Отчет о целостности данных - какой процент статистики имеет мертвые ссылки.
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
    

    async def create_or_update_daily_stats(
        self, 
        user_id: str, 
        language_id: str, 
        date: datetime.date,
        stats_update: UserDailyStatsUpdate,
        type: str = "daily"
    ) -> UserDailyStatsInDB:
        """
        Create or update daily statistics for a user.
        """
        date_datetime = datetime.combine(date, datetime.min.time())
        
        # ✅ Сначала пытаемся найти существующую запись
        existing_stats = await self.daily_stats_collection.find_one({
            "user_id": user_id,
            "language_id": language_id,
            "date": date_datetime,
            "type": type
        })
        
        if existing_stats:
            # ✅ Запись существует - просто обновляем
            update_data = {k: v for k, v in stats_update.dict().items() if v is not None}
            update_data["updated_at"] = datetime.utcnow()
            
            await self.daily_stats_collection.update_one(
                {"_id": existing_stats["_id"]},
                {"$set": update_data}
            )
            
            # Получаем обновленную запись
            updated_stats = await self.daily_stats_collection.find_one({"_id": existing_stats["_id"]})
            updated_stats["id"] = str(updated_stats.pop("_id"))
            return UserDailyStatsInDB(**updated_stats)
        
        else:
            # ✅ Записи нет - создаем новую
            new_stats = {
                "user_id": user_id,
                "language_id": language_id,
                "date": date_datetime,
                "words_studied": 0,
                "words_known": 0,
                "words_skipped": 0,
                "words_for_today": 0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "type": type
            }
            
            # Применяем переданные обновления
            update_data = {k: v for k, v in stats_update.dict().items() if v is not None}
            new_stats.update(update_data)
            
            result = await self.daily_stats_collection.insert_one(new_stats)
            
            # Получаем созданную запись
            created_stats = await self.daily_stats_collection.find_one({"_id": result.inserted_id})
            created_stats["id"] = str(created_stats.pop("_id"))
            return UserDailyStatsInDB(**created_stats)
            

    async def get_daily_stats(
        self, 
        user_id: str, 
        language_id: str, 
        date: datetime.date,
        type: str = "daily"
    ) -> Optional[UserDailyStatsInDB]:
        """
        Get daily statistics for a specific user, language, and date.
        """
        date_datetime = datetime.combine(date, datetime.min.time())
        
        stats = await self.daily_stats_collection.find_one({
            "user_id": user_id,
            "language_id": language_id,
            "date": date_datetime,
            "type": type
        })
        
        if stats:
            stats["id"] = str(stats.pop("_id"))
            return UserDailyStatsInDB(**stats)
        else:        
            return None


    async def get_monthly_stats(
        self, 
        user_id: str, 
        language_id: str, 
        date: datetime.date,
        type: str = "daily"
    ) -> UserMonthlyStats:
        """
        Get monthly statistics aggregation for a user and language.
        """
        # ✅ Преобразуем date в datetime для MongoDB
        date_datetime = datetime.combine(date, datetime.min.time())
        start_date = date_datetime - timedelta(days=31)

        # Get all daily stats for the month
        cursor = self.daily_stats_collection.find({
            "user_id": user_id,
            "language_id": language_id,
            "date": {"$gt": start_date, "$lte": date_datetime},
            "type": type
        }).sort("date", 1)
        
        daily_stats = []
        
        async for stats in cursor:
            stats["id"] = str(stats.pop("_id"))
            one_day_stat = UserDailyStatsInDB(**stats)
            daily_stats.append(one_day_stat)
        
        return UserMonthlyStats(
            user_id=user_id,
            language_id=language_id,
            date=date_datetime,
            daily_stats=daily_stats
        )