"""
Service for statistics operations.
"""

from typing import List, Optional, Dict, Any
import datetime
from bson.objectid import ObjectId

from app.db.repositories.statistics_repository import StatisticsRepository
from app.db.repositories.word_repository import WordRepository
from app.api.models.statistics import (
    UserStatisticsCreate, 
    UserStatisticsUpdate, 
    UserStatistics, 
    UserStatisticsInDB,
    UserProgress,
    UserDailyStatsUpdate,
    UserDailyStatsInDB,
    UserMonthlyStats
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
        limit: int = 100,
        validate_words: bool = False
    ) -> List[UserStatisticsInDB]:
        """
        Get statistics for a specific user with optional language filter.
        
        Args:
            user_id: ID of the user
            language_id: Optional ID of the language to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            validate_words: If True, only return statistics for existing words
            
        Returns:
            List of statistics objects
        """
        logger.info(f"Getting statistics for user_id={user_id}, language_id={language_id}, "
                   f"validate_words={validate_words}")
        
        return await self.repository.get_by_user_id(
            user_id=user_id,
            language_id=language_id,
            skip=skip,
            limit=limit,
            validate_words=validate_words
        )
    
    async def count_user_statistics(
        self,
        user_id: str,
        language_id: Optional[str] = None,
        validate_words: bool = False
    ) -> int:
        """
        НОВЫЙ МЕТОД: Подсчет статистики пользователя без получения записей.
        Намного быстрее чем get_user_statistics + len().
        
        Args:
            user_id: ID пользователя
            language_id: Опционально ID языка
            validate_words: Проверять существование слов
            
        Returns:
            Количество записей статистики
        """
        logger.info(f"Counting statistics for user_id={user_id}, language_id={language_id}, "
                   f"validate_words={validate_words}")
        
        return await self.repository.count_user_statistics(
            user_id=user_id,
            language_id=language_id,
            validate_words=validate_words
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
    
    async def delete_user_word_statistics(self, user_id: str, word_id: str) -> bool:
        return await self.repository.delete(user_id, word_id)

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
        ПРОВЕРЕНО: repository метод уже корректно использует JOIN.
        
        Args:
            user_id: ID of the user
            language_id: ID of the language
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of statistics with word information
        """
        logger.info(f"Getting words for review: user_id={user_id}, language_id={language_id}")
        
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
        теперь использует исправленный repository метод с эффективными подсчетами.
        
        Args:
            user_id: ID of the user
            language_id: ID of the language
            
        Returns:
            User progress object
        """
        logger.info(f"Getting user progress: user_id={user_id}, language_id={language_id}")
        
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
        Слова для занятия: не более `limit` ПОДХОДЯЩИХ, начиная с номера start_word.

        Отбор идёт в базе, а не после неё. Прежде бралась сотня слов подряд по
        номеру, к ней подтягивалась статистика, и уже в памяти выбрасывались
        помеченные и те, чья дата проверки в будущем. «Сто» значило сто НОМЕРОВ,
        а не сто слов: в пройденной части словаря такое окно могло дать одно
        слово или ни одного, и вызывающая сторона сдвигала его на сто номеров и
        спрашивала снова — до сотни пустых запросов подряд, и каждый всё равно
        читал сотню слов и их статистику.

        Хуже того, сотня слов от номера N по номерам шире сотни: в словарях есть
        пропуски — в английском 1534 номера из 10 000 пустые. Шаг в сто номеров
        попадал внутрь уже прочитанного, офлайн-партия добирала дубли и
        обрывалась на первом же шаге: у живого пользователя в ней оказывалось
        13 слов вместо ста.

        Теперь: один запрос за непригодными словами (индекс user_id +
        language_id + next_check_date), просмотр номеров по индексу
        (language_id, word_number) только по полю номера — без чтения самих
        слов, — и чтение ровно отобранных. Сколько просмотрено, столько и
        нужно, чтобы набрать `limit`.

        `skip` отсчитывается среди подходящих слов: раньше он отсчитывался среди
        номеров, что при включённых фильтрах значило непредсказуемое.
        """
        logger.info(f"Getting words for study: user_id={user_id}, language_id={language_id}, "
                f"start_word={start_word}, skip_marked={skip_marked}, "
                f"use_check_date={use_check_date}, skip={skip}, limit={limit}")

        if limit <= 0:
            return []

        now = datetime.datetime.utcnow()

        # 1. Какие слова этому человеку сейчас не годятся.
        blocked = set()
        conditions = []
        if skip_marked:
            conditions.append({"is_skipped": True})
        if use_check_date:
            conditions.append({"next_check_date": {"$gt": now}})
        if conditions:
            blocked_cursor = self.repository.collection.find(
                {"user_id": user_id, "language_id": language_id, "$or": conditions},
                {"word_id": 1},
            )
            blocked = {doc.get("word_id") async for doc in blocked_cursor}
            logger.info(f"Not due or marked: {len(blocked)} words")

        # 2. Идём по номерам и берём первые подходящие. Читаем только номер:
        #    сами слова достанем потом, ровно отобранные.
        scan = self.word_repository.collection.find(
            {"language_id": ObjectId(language_id), "word_number": {"$gte": start_word}},
            {"word_number": 1},
        ).sort("word_number", 1)

        chosen: List[Any] = []
        left_to_skip = skip
        scanned = 0
        async for doc in scan:
            scanned += 1
            if str(doc.get("_id")) in blocked:
                continue
            if left_to_skip > 0:
                left_to_skip -= 1
                continue
            chosen.append(doc.get("_id"))
            if len(chosen) >= limit:
                break

        logger.info(f"Selected {len(chosen)} words for study out of {scanned} scanned "
                    f"from word_number >= {start_word}")
        if not chosen:
            return []

        # 3. Сами слова и статистика по отобранным — по одному запросу.
        #    Прежде здесь на КАЖДУЮ запись статистики шёл отдельный $lookup
        #    «а существует ли такое слово» — сотня лишних обращений на запрос,
        #    хотя слова только что прочитаны и их id на руках.
        words_by_id: Dict[str, Dict[str, Any]] = {}
        words_cursor = self.word_repository.collection.find({"_id": {"$in": chosen}})
        async for word in words_cursor:
            word["_id"] = str(word["_id"])
            if isinstance(word.get("language_id"), ObjectId):
                word["language_id"] = str(word["language_id"])
            words_by_id[word["_id"]] = word

        chosen_ids = [str(wid) for wid in chosen]
        stats_by_word: Dict[str, Dict[str, Any]] = {}
        stats_cursor = self.repository.collection.find(
            {"user_id": user_id, "word_id": {"$in": chosen_ids}})
        async for stat in stats_cursor:
            for field in ("_id", "user_id", "word_id", "language_id"):
                if isinstance(stat.get(field), ObjectId):
                    stat[field] = str(stat[field])
            stats_by_word[stat.get("word_id")] = stat

        result: List[Dict[str, Any]] = []
        for wid in chosen_ids:
            word = words_by_id.get(wid)
            if word is None:
                # Слово исчезло между просмотром и чтением — пропускаем молча:
                # для занятия это просто одно слово меньше.
                continue
            stats = stats_by_word.get(wid)
            if stats:
                word["user_word_data"] = stats
            result.append(word)

        logger.info(f"Returning {len(result)} words for study")
        return result

    async def get_data_integrity_report(self) -> Dict[str, Any]:
        """
        Получить отчет о целостности данных статистики.
        
        Returns:
            Отчет с информацией о мертвых ссылках в статистике
        """
        logger.info("Getting data integrity report for statistics")
        
        return await self.repository.get_data_integrity_report()

    async def cleanup_orphaned_statistics(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Очистка статистики с мертвыми ссылками.
        
        Args:
            dry_run: Если True, только подсчитывает, не удаляет
            
        Returns:
            Отчет об операции очистки
        """
        logger.info(f"Starting cleanup of orphaned statistics, dry_run={dry_run}")
        
        # Находим статистику без соответствующих слов
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
            # Найти статистику БЕЗ соответствующих слов
            {"$match": {"word_exists": {"$eq": []}}},
            {"$project": {"_id": 1, "user_id": 1, "word_id": 1, "language_id": 1}}
        ]
        
        cursor = self.repository.collection.aggregate(pipeline)
        orphaned_records = await cursor.to_list(length=None)
        
        orphaned_count = len(orphaned_records)
        
        if dry_run:
            logger.info(f"Dry run: found {orphaned_count} orphaned statistics records")
            return {
                "dry_run": True,
                "orphaned_found": orphaned_count,
                "deleted": 0,
                "sample_orphaned": orphaned_records[:5]  # Показываем первые 5 для примера
            }
        else:
            # Реальное удаление
            if orphaned_count > 0:
                orphaned_ids = [record["_id"] for record in orphaned_records]
                
                delete_result = await self.repository.collection.delete_many({
                    "_id": {"$in": orphaned_ids}
                })
                
                deleted_count = delete_result.deleted_count
                logger.info(f"Deleted {deleted_count} orphaned statistics records")
                
                return {
                    "dry_run": False,
                    "orphaned_found": orphaned_count,
                    "deleted": deleted_count,
                    "success": deleted_count == orphaned_count
                }
            else:
                logger.info("No orphaned statistics found")
                return {
                    "dry_run": False,
                    "orphaned_found": 0,
                    "deleted": 0,
                    "success": True
                }
            

    async def update_daily_statistics(
        self,
        user_id: str,
        language_id: str,
        date: datetime.date,
        stats_update: UserDailyStatsUpdate,
        type: str = "daily"
    ) -> Optional[UserDailyStatsInDB]:
        """
        Update daily statistics for a specific user, language, and date.
        Uses upsert to create if not exists.
        
        Args:
            user_id: User ID
            language_id: Language ID
            date: Date for statistics
            stats_update: Statistics data to update
            
        Returns:
            Updated daily statistics
        """
        logger.info(f"Updating daily statistics for user_id={user_id}, language_id={language_id}, "
                   f"date={date}, updates={stats_update.model_dump()}")
        
        return await self.repository.create_or_update_daily_stats(
            user_id, language_id, date, stats_update, type
        )


    async def get_daily_statistics(
        self,
        user_id: str,
        language_id: str,
        date: datetime.date,
        type: str = "daily"
    ) -> Optional[UserDailyStatsInDB]:
        """
        Get daily statistics for a specific user, language, and date.
        
        Args:
            user_id: User ID
            language_id: Language ID
            date: Date for statistics
            
        Returns:
            Daily statistics or None if not found
        """
        logger.info(f"Getting daily statistics for user_id={user_id}, language_id={language_id}, date={date}")
        
        return await self.repository.get_daily_stats(user_id, language_id, date, type)


    async def get_monthly_statistics(
        self,
        user_id: str,
        language_id: str,
        show_all: bool,
        date: datetime.date,
        type: str = "daily"
    ) -> UserMonthlyStats:
        """
        Get monthly statistics aggregation for a user and language.
        
        Args:
            user_id: User ID
            language_id: Language ID
            date: Date for statistics
            
        Returns:
            Monthly statistics aggregation
        """
        logger.info(f"Getting monthly statistics for user_id={user_id}, language_id={language_id}, "
                   f"date={date}, type={type}")
        
        return await self.repository.get_monthly_stats(user_id, language_id, show_all, date, type)