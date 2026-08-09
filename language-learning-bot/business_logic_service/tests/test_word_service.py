"""
Тесты word_service: сколько запросов уходит на одну оценку слова и как
выбирается create/update.

update_word_score сам читает user_word_data, чтобы посчитать новый интервал,
и раньше передавал в ensure_user_word_data только результат расчёта — та
читала тот же документ повторно. На одну оценку выходило два одинаковых
GET /users/{u}/word_data/{w} плюс запись, а кнопки know / show_answer /
reconsider / rate дают до трёх таких циклов на слово.
"""

import pytest
from unittest.mock import AsyncMock

from app.services.word_service import ensure_user_word_data, update_word_score


WORD = {"_id": "w1", "language_id": "lang1"}


def make_api(existing=None):
    api = AsyncMock()
    api.get_user_word_data.return_value = {"success": True, "result": existing}
    api.update_user_word_data.return_value = {"success": True, "result": {"score": 1}}
    api.create_user_word_data.return_value = {"success": True, "result": {"score": 1}}
    return api


class TestUpdateWordScore:
    @pytest.mark.asyncio
    async def test_reads_user_word_data_once_per_rating(self):
        api = make_api(existing={"score": 0, "check_interval": 0})
        ok, _ = await update_word_score(api, "u1", "w1", 1, WORD)
        assert ok is True
        api.get_user_word_data.assert_called_once_with("u1", "w1")

    @pytest.mark.asyncio
    async def test_existing_record_is_updated_not_recreated(self):
        api = make_api(existing={"score": 0, "check_interval": 0})
        await update_word_score(api, "u1", "w1", 1, WORD)
        api.update_user_word_data.assert_called_once()
        api.create_user_word_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_record_is_created_with_one_read(self):
        api = make_api(existing=None)
        ok, _ = await update_word_score(api, "u1", "w1", 0, WORD)
        assert ok is True
        api.get_user_word_data.assert_called_once_with("u1", "w1")
        api.create_user_word_data.assert_called_once()
        payload = api.create_user_word_data.call_args[0][1]
        assert payload["word_id"] == "w1"
        assert payload["language_id"] == "lang1"
        assert payload["score"] == 0

    @pytest.mark.asyncio
    async def test_new_interval_is_computed_from_the_read_document(self):
        """Прочитанный документ идёт и в расчёт, и в выбор create/update."""
        api = make_api(existing={"score": 1, "check_interval": 4})
        await update_word_score(api, "u1", "w1", 1, WORD, max_interval=32)
        saved = api.update_user_word_data.call_args[0][2]
        assert saved["check_interval"] == 8

    @pytest.mark.asyncio
    async def test_failed_read_does_not_write(self):
        api = make_api()
        api.get_user_word_data.return_value = {"success": False, "result": None}
        ok, result = await update_word_score(api, "u1", "w1", 1, WORD)
        assert (ok, result) == (False, None)
        api.update_user_word_data.assert_not_called()
        api.create_user_word_data.assert_not_called()


class TestEnsureUserWordData:
    @pytest.mark.asyncio
    async def test_reads_when_document_was_not_passed(self):
        """Вызовы без готового документа (toggle_skip, forbidden pairs) читают сами."""
        api = make_api(existing={"score": 1})
        await ensure_user_word_data(api, "u1", "w1", {"is_skipped": True}, word=WORD)
        api.get_user_word_data.assert_called_once_with("u1", "w1")
        api.update_user_word_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_passed_document_replaces_the_read(self):
        api = make_api(existing={"score": 1})
        await ensure_user_word_data(api, "u1", "w1", {"is_skipped": True},
                                    word=WORD, existing={"score": 1})
        api.get_user_word_data.assert_not_called()
        api.update_user_word_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_passed_none_means_record_is_absent(self):
        """None — это «документа нет», а не «не читали»: создаём, но не перечитываем."""
        api = make_api(existing={"score": 1})
        await ensure_user_word_data(api, "u1", "w1", {"is_skipped": True},
                                    word=WORD, existing=None)
        api.get_user_word_data.assert_not_called()
        api.create_user_word_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_needs_language_id(self):
        api = make_api(existing=None)
        ok, result = await ensure_user_word_data(api, "u1", "w1", {"score": 0}, word={})
        assert (ok, result) == (False, None)
        api.create_user_word_data.assert_not_called()
