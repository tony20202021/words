"""
Отбор слов для занятия — сердце всего приложения.

Раньше на этот запрос не было ни одной проверки, хотя именно он решает, какие
слова человек увидит. И он делал не то, что от него ждали: брал сто слов подряд
по номеру и только потом выбрасывал помеченные и те, чья дата проверки в
будущем. «Сто» значило сто НОМЕРОВ, а не сто слов — в пройденной части словаря
запрос мог вернуть одно слово или ни одного, и вызывающая сторона сдвигала окно
и спрашивала снова.

Здесь проверяется новый договор: вернуть не больше `limit` ПОДХОДЯЩИХ слов,
начиная с номера start_word, в порядке номеров, вместе со статистикой человека.

База поддельная, но честная: хранит документы и отвечает на те же запросы, что
делает служба, — $gte по номеру, $in по идентификаторам, $or с $gt по дате.
Проверяется поведение отбора, а не то, как устроен MongoDB.
"""

import datetime
import sys
import os

import pytest
from bson.objectid import ObjectId

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.services.statistics_service import StatisticsService


# ── поддельная коллекция ────────────────────────────────────────────────────

class _Cursor:
    def __init__(self, docs):
        self._docs = docs

    def sort(self, field, direction=1):
        self._docs = sorted(self._docs, key=lambda d: d.get(field), reverse=direction < 0)
        return self

    def __aiter__(self):
        async def gen():
            for d in self._docs:
                yield dict(d)
        return gen()

    async def to_list(self, length=None):
        return [dict(d) for d in self._docs][:length]


class _Collection:
    """Ровно те условия, которыми пользуется get_words_for_study."""

    def __init__(self, docs):
        self.docs = docs
        self.scanned = 0          # сколько документов прочитано под фильтр
        self.queries = 0          # сколько раз спросили базу

    def find(self, query, projection=None):
        self.queries += 1
        matched = [d for d in self.docs if self._matches(d, query)]
        self.scanned += len(matched)
        return _Cursor(matched)

    def _matches(self, doc, query):
        for key, cond in query.items():
            if key == "$or":
                if not any(self._matches(doc, c) for c in cond):
                    return False
                continue
            value = doc.get(key)
            if isinstance(cond, dict):
                for op, operand in cond.items():
                    if op == "$gte" and not (value is not None and value >= operand):
                        return False
                    if op == "$gt" and not (value is not None and value > operand):
                        return False
                    if op == "$in" and value not in operand:
                        return False
            elif value != cond:
                return False
        return True


class _Repo:
    def __init__(self, docs):
        self.collection = _Collection(docs)


LANG = "507f1f77bcf86cd799439011"
USER = "user-1"
PAST = datetime.datetime.utcnow() - datetime.timedelta(days=1)
FUTURE = datetime.datetime.utcnow() + datetime.timedelta(days=3)


def _wid(n):
    """Устойчивый ObjectId по номеру слова — чтобы проверки были читаемыми."""
    return ObjectId(f"{n:024x}")


def _words(numbers):
    return [{"_id": _wid(n), "language_id": ObjectId(LANG), "word_number": n,
             "word_foreign": f"f{n}", "translation": f"t{n}"} for n in numbers]


def _stat(n, next_check_date=None, is_skipped=False):
    return {"_id": ObjectId(f"{n + 900000:024x}"), "user_id": USER, "language_id": LANG,
            "word_id": str(_wid(n)), "score": 1, "is_skipped": is_skipped,
            "next_check_date": next_check_date}


def _service(numbers, stats=()):
    return StatisticsService(_Repo(list(stats)), _Repo(_words(numbers)))


# ── проверки ────────────────────────────────────────────────────────────────

class TestHowManyWordsComeBack:
    @pytest.mark.asyncio
    async def test_limit_counts_suitable_words_not_numbers(self):
        """
        Из первой сотни номеров годятся два слова — но партия обязана набраться
        целиком, за счёт тех, что дальше. Прежде здесь возвращалось два слова.
        """
        stats = [_stat(n, next_check_date=FUTURE) for n in range(1, 101) if n not in (2, 7)]
        service = _service(range(1, 301), stats)
        words = await service.get_words_for_study(USER, LANG, limit=100)

        numbers = [w["word_number"] for w in words]
        assert len(numbers) == 100
        assert numbers[:2] == [2, 7]
        assert numbers[2:] == list(range(101, 199))

    @pytest.mark.asyncio
    async def test_gaps_in_numbering_do_not_shorten_the_batch(self):
        """
        В настоящих словарях номера идут с пропусками — в английском 1534 из
        10 000 пустые. Сотня слов по номерам шире сотни, и на этом ломался
        прежний шаг «плюс сто номеров».
        """
        service = _service(range(1, 1000, 7))
        words = await service.get_words_for_study(USER, LANG, limit=100)
        assert len(words) == 100
        assert words[0]["word_number"] == 1
        assert words[-1]["word_number"] == 1 + 99 * 7

    @pytest.mark.asyncio
    async def test_fewer_than_asked_when_the_dictionary_ends(self):
        service = _service(range(1, 31))
        words = await service.get_words_for_study(USER, LANG, limit=100)
        assert [w["word_number"] for w in words] == list(range(1, 31))

    @pytest.mark.asyncio
    async def test_nothing_when_everything_is_done(self):
        stats = [_stat(n, next_check_date=FUTURE) for n in range(1, 31)]
        service = _service(range(1, 31), stats)
        assert await service.get_words_for_study(USER, LANG) == []


class TestWhichWordsAreSuitable:
    @pytest.mark.asyncio
    async def test_a_word_whose_check_date_has_come_is_due(self):
        service = _service([1, 2], [_stat(1, next_check_date=PAST),
                                    _stat(2, next_check_date=FUTURE)])
        words = await service.get_words_for_study(USER, LANG)
        assert [w["word_number"] for w in words] == [1]

    @pytest.mark.asyncio
    async def test_a_word_answered_dont_know_has_no_date_and_stays_due(self):
        """score=0 обнуляет дату проверки — слово остаётся в обороте."""
        service = _service([1], [_stat(1, next_check_date=None)])
        words = await service.get_words_for_study(USER, LANG)
        assert [w["word_number"] for w in words] == [1]

    @pytest.mark.asyncio
    async def test_untouched_words_are_always_due(self):
        service = _service([5, 6])
        words = await service.get_words_for_study(USER, LANG)
        assert [w["word_number"] for w in words] == [5, 6]

    @pytest.mark.asyncio
    async def test_marked_words_are_left_out_only_when_asked(self):
        stats = [_stat(1, next_check_date=PAST, is_skipped=True)]
        service = _service([1, 2], stats)
        assert [w["word_number"] for w in await service.get_words_for_study(
            USER, LANG, skip_marked=True)] == [2]
        assert [w["word_number"] for w in await service.get_words_for_study(
            USER, LANG, skip_marked=False)] == [1, 2]

    @pytest.mark.asyncio
    async def test_without_the_date_filter_everything_comes_back(self):
        stats = [_stat(n, next_check_date=FUTURE) for n in (1, 2, 3)]
        service = _service([1, 2, 3], stats)
        words = await service.get_words_for_study(USER, LANG, use_check_date=False)
        assert [w["word_number"] for w in words] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_another_users_progress_does_not_block_words(self):
        other = _stat(1, next_check_date=FUTURE)
        other["user_id"] = "user-2"
        service = _service([1], [other])
        words = await service.get_words_for_study(USER, LANG)
        assert [w["word_number"] for w in words] == [1]


class TestWhereTheBatchStarts:
    @pytest.mark.asyncio
    async def test_start_word_is_inclusive(self):
        service = _service(range(1, 21))
        words = await service.get_words_for_study(USER, LANG, start_word=15)
        assert [w["word_number"] for w in words] == list(range(15, 21))

    @pytest.mark.asyncio
    async def test_skip_counts_suitable_words(self):
        """Прежде skip отсчитывался среди номеров — при фильтрах это значило непредсказуемое."""
        stats = [_stat(2, next_check_date=FUTURE)]
        service = _service([1, 2, 3, 4], stats)
        words = await service.get_words_for_study(USER, LANG, skip=1)
        assert [w["word_number"] for w in words] == [3, 4]


class TestWhatComesWithTheWords:
    @pytest.mark.asyncio
    async def test_the_users_progress_is_attached(self):
        service = _service([1, 2], [_stat(1, next_check_date=PAST)])
        words = await service.get_words_for_study(USER, LANG)
        assert words[0]["user_word_data"]["score"] == 1
        assert "user_word_data" not in words[1], "у нетронутого слова статистики нет"

    @pytest.mark.asyncio
    async def test_identifiers_come_back_as_strings(self):
        """ObjectId не сериализуется в JSON — клиент получил бы ошибку."""
        service = _service([1], [_stat(1, next_check_date=PAST)])
        word = (await service.get_words_for_study(USER, LANG))[0]
        assert isinstance(word["_id"], str) and isinstance(word["language_id"], str)
        assert isinstance(word["user_word_data"]["_id"], str)


class TestHowMuchItReads:
    @pytest.mark.asyncio
    async def test_it_stops_scanning_once_the_batch_is_full(self):
        """
        База просматривает столько, сколько нужно набрать, а не весь словарь:
        на этом и держится отказ от окон.
        """
        service = _service(range(1, 10001))
        await service.get_words_for_study(USER, LANG, limit=10)
        # Слова читаются дважды: просмотр номеров и чтение отобранных.
        assert service.word_repository.collection.queries == 2

    @pytest.mark.asyncio
    async def test_statistics_are_asked_for_once_per_request(self):
        """
        Прежде на КАЖДУЮ запись статистики делался отдельный запрос «а
        существует ли такое слово» — сотня лишних обращений, хотя слова только
        что прочитаны и их идентификаторы на руках.
        """
        stats = [_stat(n, next_check_date=PAST) for n in range(1, 51)]
        service = _service(range(1, 51), stats)
        await service.get_words_for_study(USER, LANG)
        assert service.repository.collection.queries == 2  # непригодные + статистика отобранных
