"""
Tests for WordService.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.services.word_service import WordService
from app.api.models.word import WordUpdate
from tests.conftest import make_word, make_language


@pytest.fixture
def service(mock_word_repo, mock_language_repo):
    return WordService(mock_word_repo, mock_language_repo)


class TestGetWord:
    @pytest.mark.asyncio
    async def test_get_existing_word(self, service, mock_word_repo):
        word = make_word()
        mock_word_repo.get_word_with_language_info.return_value = word
        result = await service.get_word(word.id)
        assert result is not None
        assert result.id == word.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_word_returns_none(self, service, mock_word_repo):
        mock_word_repo.get_word_with_language_info.return_value = None
        result = await service.get_word("000")
        assert result is None


class TestGetWordsByLanguage:
    @pytest.mark.asyncio
    async def test_get_words_empty(self, service, mock_word_repo):
        mock_word_repo.get_by_language.return_value = []
        result = await service.get_words_by_language("lang_id")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_words_returns_list(self, service, mock_word_repo):
        words = [make_word(id="aaa"), make_word(id="bbb", word_number=2)]
        mock_word_repo.get_by_language.return_value = words
        result = await service.get_words_by_language("lang_id")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_words_calls_repo_with_params(self, service, mock_word_repo):
        mock_word_repo.get_by_language.return_value = []
        await service.get_words_by_language("lang_id", skip=5, limit=20)
        mock_word_repo.get_by_language.assert_called_once_with(
            language_id="lang_id", skip=5, limit=20, word_number=None
        )


class TestCreateWord:
    @pytest.mark.asyncio
    async def test_create_word_success(self, service, mock_word_repo, mock_language_repo):
        lang = make_language()
        new_word = make_word()
        mock_language_repo.get_by_id.return_value = lang
        mock_word_repo.create.return_value = new_word
        result = await service.create_word({
            "language_id": lang.id,
            "word_foreign": "学习",
            "translation": "учёба",
            "word_number": 1,
        })
        assert result.word_foreign == new_word.word_foreign

    @pytest.mark.asyncio
    async def test_create_word_invalid_language_raises(self, service, mock_language_repo):
        mock_language_repo.get_by_id.return_value = None
        with pytest.raises(ValueError, match="Language"):
            await service.create_word({
                "language_id": "000000000000000000000000",
                "word_foreign": "x",
                "translation": "y",
                "word_number": 1,
            })


class TestUpdateWord:
    @pytest.mark.asyncio
    async def test_update_word_success(self, service, mock_word_repo):
        word = make_word()
        updated = make_word(translation="новый перевод")
        mock_word_repo.get_by_id.return_value = word
        mock_word_repo.update.return_value = updated
        result = await service.update_word(word.id, {"translation": "новый перевод"})
        assert result.translation == "новый перевод"

    @pytest.mark.asyncio
    async def test_update_nonexistent_word_returns_none(self, service, mock_word_repo):
        mock_word_repo.get_by_id.return_value = None
        result = await service.update_word("000", {"translation": "x"})
        assert result is None


class TestDeleteWord:
    @pytest.mark.asyncio
    async def test_delete_word_success(self, service, mock_word_repo):
        word = make_word()
        mock_word_repo.get_by_id.return_value = word
        mock_word_repo.delete.return_value = True
        result = await service.delete_word(word.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_word_returns_false(self, service, mock_word_repo):
        mock_word_repo.get_by_id.return_value = None
        result = await service.delete_word("000")
        assert result is False
