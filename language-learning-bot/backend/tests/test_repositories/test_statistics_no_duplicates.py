"""
Запись статистики слова не должна двоиться.

Откуда взялось. 30.09 у двенадцати слов появилось 27 лишних записей — все за
одну секунду. Так телефон отправлял накопленное офлайн: отправок уходит две
сразу (обычная и та, что идёт перед загрузкой сессии), обе видели, что записи
нет, и обе её создавали. Лишние записи врут в счётчиках, а график интервалов
повторения на них падал: доля в корзине становилась больше единицы.

База поддельная, но ведёт себя как настоящая в главном: каждое обращение к
ней уступает управление (иначе одновременные вызовы не пересекаются и проверка
ничего не стоит — на это уже попались), а find_one_and_update с upsert решает
и вставляет без разрыва, как одна операция Mongo.

Сторож для самой проверки: на прежнем коде — «посмотреть, потом вставить» —
она обязана падать. Это проверено отдельно: там выходит две записи.
"""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.api.models.statistics import UserStatisticsCreate  # noqa: E402
from app.db.repositories.statistics_repository import StatisticsRepository  # noqa: E402


class FakeCollection:
    """Минимальная коллекция: upsert, поиск и счёт — ровно что нужно записи."""

    def __init__(self):
        self.docs = []
        self.inserts = 0
        self.unique_index = False

    def _match(self, doc, flt):
        return all(doc.get(k) == v for k, v in flt.items())

    async def find_one_and_update(self, flt, update, upsert=False, return_document=None):
        # Пауза в начале — чтобы одновременные вызовы действительно пересеклись.
        # Дальше, как в Mongo, решение и запись идут без разрыва.
        await asyncio.sleep(0)
        found = next((d for d in self.docs if self._match(d, flt)), None)
        if found is not None:
            found.update(update.get("$set", {}))
            return dict(found)
        if not upsert:
            return None
        doc = dict(update.get("$setOnInsert", {}))
        doc.update(update.get("$set", {}))
        doc.update(flt)
        doc["_id"] = f"id-{len(self.docs) + 1}"
        if self.unique_index and any(self._match(d, flt) for d in self.docs):
            raise RuntimeError("duplicate key")
        self.docs.append(doc)
        self.inserts += 1
        return dict(doc)

    async def insert_one(self, doc):
        await asyncio.sleep(0)
        self.inserts += 1
        doc = dict(doc)
        doc["_id"] = f"id-{len(self.docs) + 1}"
        self.docs.append(doc)
        return type("R", (), {"inserted_id": doc["_id"]})()

    async def find_one(self, flt):
        await asyncio.sleep(0)
        return next((dict(d) for d in self.docs if self._match(d, flt)), None)

    def find(self, flt=None, *a, **kw):
        """Курсор как у motor: асинхронный обход найденного."""
        flt = {k: v for k, v in (flt or {}).items() if not isinstance(v, dict)}
        found = [dict(d) for d in self.docs if self._match(d, flt)]

        class _Cursor:
            def __aiter__(self):
                self._it = iter(found)
                return self

            async def __anext__(self):
                try:
                    return next(self._it)
                except StopIteration:
                    raise StopAsyncIteration

        return _Cursor()

    async def count_documents(self, flt):
        """Условия вида {"$lt": ...} поддельная коллекция понимает буквально."""
        await asyncio.sleep(0)
        n = 0
        for d in self.docs:
            ok = True
            for k, v in flt.items():
                if isinstance(v, dict):
                    if "$lt" in v and not (d.get(k) is not None and d[k] < v["$lt"]):
                        ok = False
                    if "$ne" in v and d.get(k) == v["$ne"]:
                        ok = False
                elif d.get(k) != v:
                    ok = False
            n += 1 if ok else 0
        return n

    async def update_one(self, flt, update):
        await asyncio.sleep(0)
        for d in self.docs:
            if self._match(d, flt):
                d.update(update.get("$set", {}))
                return type("R", (), {"modified_count": 1})()
        return type("R", (), {"modified_count": 0})()

    async def create_index(self, keys, **kw):
        self.unique_index = kw.get("unique", False)
        return "user_word_unique_idx"


class FakeDb:
    """Любая коллекция этой базы — одна и та же поддельная."""

    def __init__(self, collection):
        self._c = collection

    def __getattr__(self, name):
        return self._c

    def __getitem__(self, name):
        return self._c

    def get_collection(self, name):
        return self._c


def _repo():
    col = FakeCollection()
    repo = StatisticsRepository(FakeDb(col))
    repo.collection = col
    return repo, col


def _payload(word_id="w1", score=1):
    return UserStatisticsCreate(
        word_id=word_id, language_id="l1", score=score, is_skipped=False,
    )


class TestOneRecordPerWord:
    @pytest.mark.asyncio
    async def test_two_simultaneous_writes_make_one_record(self):
        """Ровно тот случай, что случился в бою: две отправки пачки разом."""
        repo, col = _repo()
        await asyncio.gather(
            repo.create("u1", _payload()),
            repo.create("u1", _payload()),
        )
        assert len(col.docs) == 1, col.docs
        assert col.inserts == 1

    @pytest.mark.asyncio
    async def test_a_whole_batch_applied_twice_makes_one_record_per_word(self):
        repo, col = _repo()
        words = [f"w{i}" for i in range(1, 6)]
        await asyncio.gather(
            *[repo.create("u1", _payload(w)) for w in words],
            *[repo.create("u1", _payload(w)) for w in words],
        )
        assert len(col.docs) == len(words), col.docs

    @pytest.mark.asyncio
    async def test_an_existing_record_is_returned_not_duplicated(self):
        repo, col = _repo()
        first = await repo.create("u1", _payload())
        second = await repo.create("u1", _payload())
        assert len(col.docs) == 1
        assert first.id == second.id

    @pytest.mark.asyncio
    async def test_different_people_keep_their_own_records(self):
        repo, col = _repo()
        await repo.create("u1", _payload())
        await repo.create("u2", _payload())
        assert len(col.docs) == 2

    @pytest.mark.asyncio
    async def test_different_words_keep_their_own_records(self):
        repo, col = _repo()
        await repo.create("u1", _payload("w1"))
        await repo.create("u1", _payload("w2"))
        assert len(col.docs) == 2

    @pytest.mark.asyncio
    async def test_the_second_answer_lands_on_the_same_record(self):
        """Не двоить — не значит потерять: оценка обязана дойти.

        Если бы запись только «вставлялась, когда нет», проигравший запрос
        молча уносил бы ответ человека с собой.
        """
        repo, col = _repo()
        await repo.create("u1", _payload(score=1))
        await repo.create("u1", _payload(score=0))
        assert len(col.docs) == 1
        assert col.docs[0]["score"] == 0

    @pytest.mark.asyncio
    async def test_the_original_creation_date_is_kept(self):
        repo, col = _repo()
        first = await repo.create("u1", _payload())
        born = col.docs[0]["created_at"]
        await repo.create("u1", _payload(score=0))
        assert col.docs[0]["created_at"] == born
        assert first.id == str(col.docs[0]["_id"])

    @pytest.mark.asyncio
    async def test_the_uniqueness_rule_is_declared(self):
        """Последняя защита — правило в самой базе, а не только наша осторожность."""
        repo, col = _repo()
        await repo.ensure_indexes()
        assert col.unique_index is True


class TestTheDayBoundaryComesFromTheUser:
    """
    «Слов на сегодня» считается от границы суток ЭТОГО человека.

    Что сломалось. 09.10.2026 границу суток вынесли в настройки, и дата
    следующей проверки стала ложиться на неё: у владельца с Europe/Moscow и
    началом суток в 4 утра это 01:00 UTC. А подсчёт здесь остался сравнением
    с полуночью UTC — и слова со сроком «сегодня» в счёт не попадали, всплывая
    только назавтра. На экране было «слов на сегодня: 0» при четырёх
    назначенных.

    Правило теперь такое: срок наступил — значит, граница уже прошла, то есть
    сравниваем с ТЕКУЩИМ моментом. А «недопройдено» — это граница более
    раннего дня, и там нужно начало сегодняшних суток.
    """

    @pytest.mark.asyncio
    async def test_a_word_due_at_the_user_boundary_counts_today(self):
        from datetime import datetime, timedelta

        from bson import ObjectId

        repo, col = _repo()
        repo.db = FakeDb(col)
        uid, lid = "507f1f77bcf86cd799439033", "507f1f77bcf86cd799439011"
        col.docs.append({"user_id": ObjectId(uid), "language_id": ObjectId(lid),
                         "timezone": "Europe/Moscow", "day_start_hour": 4})
        now, day_start = await repo._day_bounds(uid, lid)

        # 04:00 по Москве — это 01:00 UTC.
        assert day_start.hour == 1, f"начало суток посчитано как {day_start}"
        assert day_start <= now, "начало суток оказалось в будущем"
        assert now - day_start < timedelta(days=1)

        # Слово со сроком ровно на границе уже пора повторять...
        assert day_start <= now
        # ...а «недопройденным» оно станет только завтра.
        assert not (day_start < day_start)

    @pytest.mark.asyncio
    async def test_without_settings_the_boundary_is_utc_midnight(self):
        repo, col = _repo()
        repo.db = FakeDb(col)
        _, day_start = await repo._day_bounds("u1", "l1")
        assert (day_start.hour, day_start.minute) == (0, 0), day_start

    @pytest.mark.asyncio
    async def test_broken_settings_do_not_break_the_count(self):
        """Кривой id или пояс с опечаткой — берём умолчания, а не падаем."""
        repo, col = _repo()
        repo.db = FakeDb(col)
        col.docs.append({"user_id": "u1", "language_id": "l1", "timezone": "Нет/Такого"})
        _, day_start = await repo._day_bounds("не-objectid", "тоже-не-objectid")
        assert day_start.hour == 0


class TestCheckDatesFollowTheDayStart:
    """
    Даты проверки обязаны лежать на границе учебных суток человека.

    Что сломалось 10.10.2026. Границу вынесли в настройки, владелец поставил
    Europe/Moscow и начало суток в 4 утра — а 219 уже накопленных дат остались
    на полуночи UTC. Полночь UTC это 03:00 по Москве, то есть ПОСЛЕДНИЙ час
    предыдущих суток: слово становилось нужным в три ночи и через час, с
    началом новых суток, объявлялось недопройденным. Наутро владелец увидел
    «53 слова недопройдено», пройдя накануне всё.

    Старое значение «полночь дня D» означало «повторить в день D»; новое того
    же — начало учебных суток дня D.
    """

    @pytest.mark.asyncio
    async def test_dates_are_moved_onto_the_new_boundary(self):
        from bson import ObjectId
        from datetime import datetime

        repo, col = _repo()
        repo.db = FakeDb(col)
        uid, lid = "507f1f77bcf86cd799439033", "507f1f77bcf86cd799439011"
        col.docs.append({"user_id": ObjectId(uid), "language_id": ObjectId(lid),
                         "timezone": "Europe/Moscow", "day_start_hour": 4})
        col.docs.append({"user_id": uid, "language_id": lid, "word_id": "w1",
                         "_id": "s1", "next_check_date": datetime(2026, 10, 11, 0, 0)})

        moved = await repo.align_check_dates(uid, lid)
        assert moved == 1
        assert col.docs[-1]["next_check_date"] == datetime(2026, 10, 11, 1, 0), (
            "дата не легла на 04:00 по Москве")

    @pytest.mark.asyncio
    async def test_a_date_already_on_the_boundary_is_left_alone(self):
        from bson import ObjectId
        from datetime import datetime

        repo, col = _repo()
        repo.db = FakeDb(col)
        uid, lid = "507f1f77bcf86cd799439033", "507f1f77bcf86cd799439011"
        col.docs.append({"user_id": ObjectId(uid), "language_id": ObjectId(lid),
                         "timezone": "Europe/Moscow", "day_start_hour": 4})
        col.docs.append({"user_id": uid, "language_id": lid, "word_id": "w1",
                         "_id": "s1", "next_check_date": datetime(2026, 10, 11, 1, 0)})
        assert await repo.align_check_dates(uid, lid) == 0

    @pytest.mark.asyncio
    async def test_default_settings_move_nothing(self):
        """У границы по умолчанию (UTC, полночь) двигать нечего."""
        from datetime import datetime

        repo, col = _repo()
        repo.db = FakeDb(col)
        col.docs.append({"user_id": "u1", "language_id": "l1", "word_id": "w1",
                         "_id": "s1", "next_check_date": datetime(2026, 10, 11, 0, 0)})
        assert await repo.align_check_dates("u1", "l1") == 0


class TestTodaysSnapshotFollowsTheMovedDates:
    """
    Сдвинули даты — пересчитай «недопройдено» в сегодняшнем снимке.

    Дневной снимок пишется ОДИН раз за сутки, на первом ответе дня, и потом
    не трогается. Это правильно: в нём состояние на начало дня. Но
    «недопройдено» выведено из дат следующей проверки, и когда эти даты
    переложили на новую границу суток, снимок остался с прежним числом.

    У владельца так и вышло: живой показатель стал 0, а график до вечера
    показывал 53 — он рисуется по снимку, а не по живым данным. Вопрос «за
    сегодня всё ещё показывает 53 просроченных» был именно про это.
    """

    @pytest.mark.asyncio
    async def test_the_snapshot_is_recomputed_after_the_move(self):
        from bson import ObjectId
        from datetime import datetime

        repo, col = _repo()
        repo.db = FakeDb(col)
        repo.daily_stats_collection = col
        uid, lid = "507f1f77bcf86cd799439033", "507f1f77bcf86cd799439011"
        col.docs.append({"user_id": ObjectId(uid), "language_id": ObjectId(lid),
                         "timezone": "Europe/Moscow", "day_start_hour": 4})
        # Дата на полуночи UTC — её и переложит выравнивание. Берём ЗАВТРАШНЮЮ
        # относительно сегодня: с жёстко вписанным числом проверка жила ровно
        # до этой даты, а потом слово становилось просроченным само собой и
        # проверка падала на ровном месте.
        from datetime import timedelta

        tomorrow = (datetime.utcnow() + timedelta(days=1)).date()
        col.docs.append({"user_id": uid, "language_id": lid, "word_id": "w1", "_id": "s1",
                         "score": 1,
                         "next_check_date": datetime.combine(tomorrow, datetime.min.time())})
        # Снимок именно за СЕГОДНЯШНИЕ учебные сутки — по ним его и находят.
        from common.study_day import study_day

        today = study_day(datetime.utcnow(), "Europe/Moscow", 4)
        snapshot = {"user_id": uid, "language_id": lid, "type": "daily",
                    "date": datetime.combine(today, datetime.min.time()),
                    "words_overdue": 53}
        col.docs.append(snapshot)

        moved = await repo.align_check_dates(uid, lid)
        assert moved == 1
        assert snapshot["words_overdue"] == 0, (
            "снимок остался с прежним числом — график покажет неправду")

    @pytest.mark.asyncio
    async def test_nothing_moved_nothing_touched(self):
        """Если двигать было нечего, снимок не трогаем вовсе."""
        from datetime import datetime

        repo, col = _repo()
        repo.db = FakeDb(col)
        repo.daily_stats_collection = col
        col.docs.append({"user_id": "u1", "language_id": "l1", "word_id": "w1", "_id": "s1",
                         "score": 1, "next_check_date": datetime(2026, 10, 11, 0, 0)})
        snapshot = {"user_id": "u1", "language_id": "l1", "type": "daily",
                    "words_overdue": 7}
        col.docs.append(snapshot)
        assert await repo.align_check_dates("u1", "l1") == 0
        assert snapshot["words_overdue"] == 7
