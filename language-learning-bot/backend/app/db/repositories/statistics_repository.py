"""
Repository for user statistics operations.
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from pymongo import ReturnDocument

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
        statistics_dict = statistics.model_dump()
        statistics_dict["user_id"] = user_id
        
        # Convert IDs from string to ObjectId for MongoDB
        if "word_id" in statistics_dict and isinstance(statistics_dict["word_id"], str):
            statistics_dict["word_id"] = statistics_dict["word_id"]  # Keep as string for easier lookup
        
        if "language_id" in statistics_dict and isinstance(statistics_dict["language_id"], str):
            statistics_dict["language_id"] = statistics_dict["language_id"]  # Keep as string for easier lookup
        
        statistics_dict["created_at"] = datetime.utcnow()
        statistics_dict["updated_at"] = statistics_dict["created_at"]

        # Одна операция «создать или положить состояние», а не «посмотреть и
        # вставить».
        #
        # Телефон отправляет накопленное офлайн пачкой, и отправок может уйти
        # две сразу — обычная и та, что идёт перед загрузкой сессии. BLS на
        # каждую сначала читает запись, не находит её и просит создать: 30.09
        # так появилось 27 лишних записей у двенадцати слов за одну секунду.
        # Лишние записи врут в счётчиках и ломали график интервалов повторения.
        #
        # Почему $set, а не только $setOnInsert: сюда приходят уже посчитанные
        # счёт, интервал и дата следующей проверки — ровно то, что иначе
        # положил бы путь обновления. Если запись к этому моменту всё-таки
        # появилась, «не трогать её» означало бы потерять оценку человека
        # молча. Дату создания при этом сохраняем первоначальную.
        filter_ = {"user_id": user_id, "word_id": statistics_dict.get("word_id")}
        created_at = statistics_dict.pop("created_at")
        doc = await self.collection.find_one_and_update(
            filter_,
            {"$set": statistics_dict, "$setOnInsert": {"created_at": created_at}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        doc["id"] = str(doc.pop("_id"))
        return UserStatisticsInDB(**doc)
    
    async def _day_bounds(self, user_id: str, language_id: str):
        """
        (сейчас, начало учебных суток) — по настройкам этого человека.

        Зачем обе величины. Дата следующей проверки хранится ровно на границе
        учебных суток (см. common/study_day.py), поэтому «пора повторять» —
        это «граница уже прошла», то есть сравнение с ТЕКУЩИМ моментом. А
        «недопройдено» — это «прошла граница более РАННЕГО дня», и там нужно
        начало сегодняшних суток.

        Почему не полночь UTC, как было. 09.10.2026 владелец поставил
        Europe/Moscow и начало суток в 4 утра — границы легли на 01:00 UTC, а
        здесь всё ещё сравнивалось с 00:00 UTC. Слова со сроком «сегодня» в
        счёт на сегодня не попадали и всплывали только назавтра: «слов на
        сегодня» показывало ноль при четырёх назначенных.
        """
        from common.study_day import day_started_utc, settings_of, study_day

        settings = {}
        try:
            doc = await self.db.user_language_settings.find_one(
                {"user_id": ObjectId(user_id), "language_id": ObjectId(language_id)})
            settings = doc or {}
        except Exception:
            pass   # настроек нет или id не разбирается — берём умолчания
        tz_name, day_start = settings_of(settings)
        now = datetime.utcnow()
        return now, day_started_utc(study_day(now, tz_name, day_start), tz_name, day_start)

    async def align_check_dates(self, user_id: str, language_id: str) -> int:
        """
        Переложить даты следующей проверки на границу учебных суток человека.

        Зачем. Дата хранится как момент, когда слово становится нужным, и
        кладётся ровно на начало учебных суток. Стоит человеку сменить пояс
        или час начала — все накопленные даты оказываются не на границе, и
        день для них начинается не тогда, когда для всего остального.

        Чем это кончилось 10.10.2026. Границу вынесли в настройки, владелец
        поставил Europe/Moscow и 4 утра, а 219 уже накопленных дат остались
        на полуночи UTC — это 03:00 по Москве, последний час ПРЕДЫДУЩИХ
        суток. Слово становилось нужным в три ночи и через час объявлялось
        недопройденным. Наутро — «53 слова недопройдено», хотя накануне
        пройдено всё.

        Старое значение «полночь дня D» означало «повторить в день D»;
        новое того же — начало учебных суток дня D. Так и пересчитываем.
        Записи, уже лежащие на границе, не трогаем.

        Returns: сколько дат сдвинуто.
        """
        from common.study_day import day_started_utc, settings_of

        settings = {}
        try:
            doc = await self.db.user_language_settings.find_one(
                {"user_id": ObjectId(user_id), "language_id": ObjectId(language_id)})
            settings = doc or {}
        except Exception:
            return 0
        tz_name, day_start = settings_of(settings)

        moved = 0
        async for doc in self.collection.find(
                {"user_id": user_id, "language_id": language_id,
                 "next_check_date": {"$ne": None}}):
            old = doc.get("next_check_date")
            if not isinstance(old, datetime):
                continue
            want = day_started_utc(old.date(), tz_name, day_start)
            if want == old:
                continue
            await self.collection.update_one(
                {"_id": doc["_id"]}, {"$set": {"next_check_date": want}})
            moved += 1
        if moved:
            logger.info(f"даты проверки переложены на границу суток: {moved} "
                        f"(user={user_id}, lang={language_id}, {tz_name}/{day_start})")
            await self._refresh_today_overdue(user_id, language_id, tz_name, day_start)
        return moved

    async def _refresh_today_overdue(self, user_id, language_id, tz_name, day_start) -> None:
        """
        Пересчитать «недопройдено» в сегодняшнем дневном снимке.

        Снимок пишется ОДИН раз за сутки, на первом ответе дня, и потом не
        трогается — в нём состояние на начало дня. Но «недопройдено» выведено
        из дат, которые мы только что сдвинули, и без пересчёта график до
        вечера показывал бы вчерашнюю неправду: у владельца так и вышло —
        живой показатель стал 0, а на графике до конца дня висело 53.

        Остальные поля снимка не трогаем: они про начало дня и от сдвига дат
        не зависят.
        """
        from common.study_day import day_started_utc, study_day

        now = datetime.utcnow()
        today = study_day(now, tz_name, day_start)
        boundary = day_started_utc(today, tz_name, day_start)
        overdue = await self.collection.count_documents({
            "user_id": user_id, "language_id": language_id,
            "next_check_date": {"$lt": boundary},
            "score": 1, "is_skipped": {"$ne": True},
        })
        res = await self.daily_stats_collection.update_one(
            {"user_id": user_id, "language_id": language_id, "type": "daily",
             "date": datetime.combine(today, datetime.min.time())},
            {"$set": {"words_overdue": overdue}},
        )
        if res.modified_count:
            logger.info(f"в снимке за {today} «недопройдено» пересчитано: {overdue}")

    async def ensure_indexes(self):
        """
        Единственность пары «человек + слово».

        Правило в самой базе — последняя защита: даже если два запроса придут
        ровно одновременно и оба решат вставить, вторая вставка будет отвергнута.
        Создаётся не падая: если в данных ещё остались дубли, индекс не встанет,
        и это повод их вычистить, а не повод не запускаться.
        """
        try:
            await self.collection.create_index(
                [("user_id", 1), ("word_id", 1)],
                name="user_word_unique_idx", unique=True, background=True,
            )
        except Exception as e:
            logger.warning(f"не удалось создать индекс единственности: {e}")

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
        validate_words: bool = True,
        with_lists: bool = True,
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
        
        now, today = await self._day_bounds(user_id, language_id)

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
                            "$sum": {"$cond": [{"$lte": ["$next_check_date", now]}, 1, 0]}
                        },
                        # Два независимых счётчика недоученного.
                        # Слову, отвеченному «не знаю», дата проверки ставится на
                        # сегодня, и назавтра оно станет просроченным — попав бы
                        # сразу в оба. Поэтому просроченные считаются только среди
                        # известных: это слова, до которых не дошли.
                        "words_unknown_now": {
                            "$sum": {"$cond": [{"$and": [
                                {"$eq": ["$score", 0]},
                                {"$ne": ["$is_skipped", True]}
                            ]}, 1, 0]}
                        },
                        "words_overdue": {
                            "$sum": {"$cond": [{"$and": [
                                {"$lt": ["$next_check_date", today]},
                                {"$eq": ["$score", 1]},
                                {"$ne": ["$is_skipped", True]}
                            ]}, 1, 0]}
                        },

                        # Первый проход сегодняшней порции: сколько слов,
                        # назначенных НА сегодня, ещё ни разу сегодня не
                        # показывались, и сколько уже показано.
                        #
                        # Зачем. «Не знаю» переносит дату проверки на сегодня,
                        # поэтому words_for_today не опускается до нуля, пока
                        # человек не выучит всё, — и событие «порция пройдена»
                        # не наступает никогда. Ответ сегодняшнего дня видно по
                        # updated_at: оно обновляется на каждую оценку. Значит,
                        # «осталось» — это срок подошёл, а ответа сегодня не
                        # было; повторы того же дня в него не попадают.
                        #
                        # Подделать этот счётчик нельзя: слово, которому дату
                        # перенесли сегодняшним ответом, тем же ответом
                        # получает свежий updated_at и из «осталось» выпадает.
                        #
                        # Пропущенные не в счёт: их не выдают на занятии, и они
                        # держали бы порцию незакрытой вечно.
                        "words_portion_left": {
                            "$sum": {"$cond": [{"$and": [
                                {"$lte": ["$next_check_date", today]},
                                {"$lt": ["$updated_at", today]},
                                {"$ne": ["$is_skipped", True]}
                            ]}, 1, 0]}
                        },
                        # Занимался ли человек сегодня вообще. Нужно как
                        # оговорка к предыдущему: пустая порция тоже даёт ноль,
                        # и без этого запись легла бы в день, когда человек не
                        # открывал приложение.
                        #
                        # Считать «сколько порции уже пройдено» бессмысленно:
                        # слово, отвеченное «знаю», получает срок в будущем и из
                        # порции исчезает. Такой счётчик мерил бы не пройденное,
                        # а незнакомые повторы, и в день, когда человек знал всё,
                        # показывал бы ноль — то есть «порции не было».
                        "words_answered_today": {
                            "$sum": {"$cond": [{"$gte": ["$updated_at", today]}, 1, 0]}
                        },

                        # 🆕 списки номеров слов
                        **({} if not with_lists else {
                        "word_numbers_for_today": {
                            "$push": {
                                "$cond": [
                                    {"$lte": ["$next_check_date", now]},
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
                        },
                        "word_check_interval": {
                            "$push": {
                                "$cond": [
                                    {"$and": [
                                        {"$ne": ["$is_skipped", True]}
                                    ]},
                                    ("$word_number", "$check_interval"),
                                    "$$REMOVE"
                                ]
                            }
                        }
                        }),
                    }
                },
            ] + ([
                # 🆕 Сортируем списки номеров слов
                {
                    "$addFields": {
                        "word_numbers_for_today": {"$sortArray": {"input": "$word_numbers_for_today", "sortBy": 1}},
                        "word_numbers_unknown": {"$sortArray": {"input": "$word_numbers_unknown", "sortBy": 1}},
                        "word_check_interval": {"$sortArray": {"input": "$word_check_interval", "sortBy": 1}},
                    }
                }
            ] if with_lists else [])
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
                "words_unknown_now": result[0]["words_unknown_now"],
                "words_overdue": result[0]["words_overdue"],
                "words_portion_left": result[0]["words_portion_left"],
                "words_answered_today": result[0]["words_answered_today"],
                **({"word_numbers_for_today": result[0]["word_numbers_for_today"],
                    "word_numbers_unknown": result[0]["word_numbers_unknown"],
                    "word_check_interval": result[0]["word_check_interval"]}
                   if with_lists else {}),
            }
        else:
            return {
                "words_studied": 0,
                "words_known": 0,
                "words_skipped": 0,
                "words_for_today": 0,
                "words_unknown_now": 0,
                "words_overdue": 0,
                "words_portion_left": 0,
                "words_answered_today": 0,
                **({"word_numbers_for_today": [],
                    "word_numbers_unknown": [],
                    "word_check_interval": []} if with_lists else {}),
            }


    async def get_portion_state(self, user_id: str, language_id: str) -> Dict[str, int]:
        """
        Три числа о сегодняшней порции — чтобы спрашивать их на каждый ответ.

        Прогресс для этого не годится: в его ответе лежат массивы номеров слов
        (по записи на каждое изученное слово), а спрашивать надо после каждой
        оценки — иначе не поймать момент, когда порция только что закрылась.
        Поэтому та же агрегация, но без списков.
        """
        data = await self.count_user_statistics_by_conditions(
            user_id=user_id, language_id=language_id,
            validate_words=True, with_lists=False)
        return {
            "words_portion_left": data["words_portion_left"],
            "words_answered_today": data["words_answered_today"],
            "words_unknown_now": data["words_unknown_now"],
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
                    "word_number": "$word.word_number",
                    "radicals": "$word.radicals",
                    "references": "$word.references",
                    "tags": "$word.tags",
                    "tag_groups": "$word.tag_groups",
                    "tones": "$word.tones",
                    "part_of_speech": "$word.part_of_speech",
                    "lemma": "$word.lemma",
                    "sounds": "$word.sounds",
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
        statistics_dict = {k: v for k, v in statistics.model_dump().items() if v is not None}
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
        statistics_dict = {k: v for k, v in statistics.model_dump().items() if v is not None}
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
        now, _ = await self._day_bounds(user_id, language_id)

        pipeline = [
            # Match statistics for the user and language that are due for review
            {
                "$match": {
                    "user_id": user_id,
                    "language_id": language_id,
                    "next_check_date": {"$lte": now}
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
                    "word_number": "$word.word_number",
                    "radicals": "$word.radicals",
                    "references": "$word.references",
                    "tags": "$word.tags",
                    "tag_groups": "$word.tag_groups",
                    "tones": "$word.tones",
                    "part_of_speech": "$word.part_of_speech",
                    "lemma": "$word.lemma",
                    "sounds": "$word.sounds",
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
                words_unknown_now=stats_data["words_unknown_now"],
                words_overdue=stats_data["words_overdue"],
                words_portion_left=stats_data["words_portion_left"],
                words_answered_today=stats_data["words_answered_today"],
                progress_percentage=round(progress_percentage, 2),
                last_study_date=last_study_date,
                word_numbers_for_today=stats_data["word_numbers_for_today"],
                word_numbers_unknown=stats_data["word_numbers_unknown"],
                word_check_interval=stats_data["word_check_interval"]
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
                words_unknown_now=0,
                words_overdue=0,
                words_skipped=0,
                words_for_today=0,
                words_portion_left=0,
                words_answered_today=0,
                progress_percentage=0.0,
                last_study_date=None,
                word_numbers_for_today=[],
                word_numbers_unknown=[],
                word_check_interval=[]
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
            # ✅ Запись существует - обновляем

            if type == "first_finish":
                # С 16.09.2026 BLS пишет первый финиш РОВНО ОДИН раз в сутки и
                # при существующей записи не приходит сюда вовсе. Проверка ниже
                # осталась защитой от повторной записи мимо этого правила: она
                # не даёт затереть первый результат дня более поздним и лучшим.
                # Prefer words_unknown field if provided directly; fall back to computation.
                if stats_update.words_unknown is not None:
                    incoming_unknown = stats_update.words_unknown
                else:
                    incoming_unknown = (
                        (stats_update.words_studied or 0)
                        - (stats_update.words_known or 0)
                        - (stats_update.words_skipped or 0)
                    )
                existing_wu = existing_stats.get("words_unknown")
                if existing_wu is not None:
                    existing_unknown = existing_wu
                else:
                    existing_unknown = (
                        existing_stats.get("words_studied", 0)
                        - existing_stats.get("words_known", 0)
                        - existing_stats.get("words_skipped", 0)
                    )
                if incoming_unknown <= existing_unknown:
                    result = await self.daily_stats_collection.find_one({"_id": existing_stats["_id"]})
                    result["id"] = str(result.pop("_id"))
                    return UserDailyStatsInDB(**result)

            update_data = {k: v for k, v in stats_update.model_dump().items() if v is not None}
            max_word_number = update_data.pop("max_word_number", None)
            words_unknown_direct = update_data.pop("words_unknown", None)

            if type in ("first_finish", "last_finish") and words_unknown_direct is not None:
                # Clean path: only set words_unknown, leave other fields untouched.
                update_ops: dict = {"$set": {"words_unknown": words_unknown_direct, "updated_at": datetime.utcnow()}}
            else:
                # daily type (or legacy finish update without words_unknown):
                # $max protects words_known/words_for_today against BLS restart race conditions.
                words_known = update_data.pop("words_known", None)
                words_for_today = update_data.pop("words_for_today", None)
                update_data["updated_at"] = datetime.utcnow()
                update_ops = {"$set": update_data}
                max_ops_full: dict = {}
                if words_known is not None:
                    max_ops_full["words_known"] = words_known
                if words_for_today is not None:
                    max_ops_full["words_for_today"] = words_for_today
                if max_ops_full:
                    update_ops["$max"] = max_ops_full

            if max_word_number is not None:
                update_ops.setdefault("$max", {})["max_word_number"] = max_word_number

            await self.daily_stats_collection.update_one(
                {"_id": existing_stats["_id"]},
                update_ops
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
            update_data = {k: v for k, v in stats_update.model_dump().items() if v is not None}
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
        show_all: bool,
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
            "date": {"$lte": date_datetime} if show_all else {"$gt": start_date, "$lte": date_datetime},
            "type": type
        }).sort("date", 1)
        
        daily_stats = []
        
        async for stats in cursor:
            stats["id"] = str(stats.pop("_id"))
            one_day_stat = UserDailyStatsInDB(**stats)
            daily_stats.append(one_day_stat)
        
        # logger.info(f"daily_stats: {daily_stats}")

        return UserMonthlyStats(
            user_id=user_id,
            language_id=language_id,
            date=date_datetime,
            daily_stats=daily_stats
        )