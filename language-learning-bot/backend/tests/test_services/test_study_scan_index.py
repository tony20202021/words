"""
Просмотр номеров при подборе слов обходится одним индексом.

Утром 17, 19 и 20.11.2026 первый за день подбор слов не укладывался в
пять секунд, которые служба логики ждёт бэкенд, и падал с ошибкой 500. Замер
21.11 на словах Юрия: 5,7 с первый раз, 0,07 с — второй. Время уходило на
просмотр номеров: 1317 номеров ради ста подходящих слов, и на каждый база
доставала из памяти всю запись слова. Запрос просил номер и _id, а индекс
(language_id, word_number) не содержит _id — план был IXSCAN + FETCH. За ночь
память базы уходит в подкачку, и каждая такая запись поднималась оттуда по
странице.

Если в индексе есть каждое поле, которое просмотр фильтрует и возвращает,
база отвечает по одному индексу (PROJECTION_COVERED) и записей слов не трогает.
Проверяется договор между запросом и индексами, которые бэкенд создаёт при
запуске: план на живой базе сверен вручную, здесь база поддельная.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.db.repositories.word_repository import WordRepository  # noqa: E402
from tests.test_services.test_words_for_study import USER, LANG, _service, _stat, FUTURE  # noqa: E402


class _RecordingWords:
    """Запоминает индексы, которые создаёт ensure_indexes."""

    def __init__(self):
        self.indexes = []

    async def create_index(self, keys, **kwargs):
        self.indexes.append([k for k, _ in keys])


async def _created_indexes():
    repo = WordRepository.__new__(WordRepository)
    repo.collection = _RecordingWords()
    await repo.ensure_indexes()
    return repo.collection.indexes


def _number_scan(service):
    """(фильтр, проекция) просмотра номеров — запроса, отсортированного по номеру."""
    for query, projection in service.word_repository.collection.finds:
        if "word_number" in query:
            return query, projection
    raise AssertionError("просмотра по номеру не было")


@pytest.mark.asyncio
async def test_the_number_scan_is_answered_by_an_index_alone(monkeypatch):
    from tests.test_services import test_words_for_study as fakes

    original = fakes._Collection.find

    def recording_find(self, query, projection=None):
        self.finds = getattr(self, "finds", [])
        self.finds.append((query, projection or {}))
        return original(self, query, projection)

    monkeypatch.setattr(fakes._Collection, "find", recording_find)

    stats = [_stat(n, next_check_date=FUTURE) for n in range(1, 50)]
    service = _service(range(1, 200), stats)
    await service.get_words_for_study(USER, LANG, limit=10)
    query, projection = _number_scan(service)

    returned = {k for k, v in projection.items() if v} | (
        set() if projection.get("_id", 1) == 0 else {"_id"})
    needed = set(query) | returned

    indexes = await _created_indexes()
    covering = [ix for ix in indexes if needed <= set(ix) and ix[:2] == ["language_id", "word_number"]]
    assert covering, (
        f"просмотр номеров читает {sorted(needed)}, а ни один индекс из ensure_indexes "
        f"({indexes}) их все не содержит — база будет доставать записи слов")
