"""
Загрузка словаря не должна называть успехом то, что не вышло.

08.11.2026, замена словаря английского. Проба на двух словах: сервер ответил
«words_updated: 1», а запись не изменилась — updated_at остался прошлогодним.
Причина: в коллекции words уникальный индекс (language_id, word_foreign), а
новый словарь переставляет слова по номерам — «it» переезжает с номера 10 на
12, и в этот миг оно ещё занято прежним владельцем. База отказывает, но
репозиторий глушил исключение и возвращал None, а загрузка увеличивала
счётчик «обновлено», не глядя на результат.

Опасность не в самой коллизии, а в отчёте: «обновлено 8466» при словаре,
изменившемся наполовину, выглядит как успех, и заметить нечего. Проверка
держит именно это: когда обновление не удалось, оно обязано попасть в ошибки,
а не в успехи.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.excel_service import ExcelService  # noqa: E402


class ОтказВОбновлении:
    """Служба слов, у которой обновление не выходит, как при дубликате."""

    def __init__(self):
        self.попыток = 0

    async def get_word_by_number(self, language_id, word_number):
        class Слово:
            id = "aaaaaaaaaaaaaaaaaaaaaaaa"
        return Слово()

    async def update_word(self, word_id, data):
        self.попыток += 1
        return None            # ровно то, что отдаёт репозиторий при отказе

    async def create_word(self, data):          # pragma: no cover
        raise AssertionError("слово существует, создавать его не должны")


def _файл_с_двумя_словами():
    """Excel в памяти: заголовок и две строки."""
    import io

    import pandas as pd

    буфер = io.BytesIO()
    pd.DataFrame([
        {"word": "it", "translation": "это", "transcription": "/ɪt/",
         "radicals": None, "references": None, "tones": None, "sounds": None},
        {"word": "at", "translation": "у", "transcription": "/æt/",
         "radicals": None, "references": None, "tones": None, "sounds": None},
    ]).to_excel(буфер, index=False, header=True)
    return буфер.getvalue()


@pytest.mark.asyncio
async def test_неудачное_обновление_не_считается_обновлённым():
    служба = ОтказВОбновлении()
    excel = ExcelService(word_service=служба)

    итог = await excel.process_excel_file(
        contents=_файл_с_двумя_словами(), language_id="l1",
        column_word=0, column_translation=1, column_transcription=2,
        column_radicals=3, column_references=4, column_tones=5,
        column_sounds=6, column_number=None, start_row=1)

    assert служба.попыток == 2, "обе строки должны были дойти до обновления"
    assert итог["updated"] == 0, (
        f"отказ базы засчитан как обновление: updated={итог['updated']}")
    assert итог["skipped"] == 2
    assert len(итог["errors"]) == 2, "об отказе не сказано ни слова"
    assert "it" in итог["errors"][0], "в ошибке не названо слово"


@pytest.mark.asyncio
async def test_успешное_обновление_считается_как_прежде():
    """Опора против перегиба: удачное обновление должно остаться удачным."""

    class Удача(ОтказВОбновлении):
        async def update_word(self, word_id, data):
            self.попыток += 1
            return {"id": word_id}

    служба = Удача()
    excel = ExcelService(word_service=служба)

    итог = await excel.process_excel_file(
        contents=_файл_с_двумя_словами(), language_id="l1",
        column_word=0, column_translation=1, column_transcription=2,
        column_radicals=3, column_references=4, column_tones=5,
        column_sounds=6, column_number=None, start_row=1)

    assert итог["updated"] == 2
    assert итог["skipped"] == 0
    assert итог["errors"] == []
