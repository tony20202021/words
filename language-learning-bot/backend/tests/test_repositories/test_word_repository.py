"""
Tests for WordRepository.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.db.repositories.word_repository import WordRepository
from app.api.models.word import WordCreate, WordUpdate


WORD_ID = "507f1f77bcf86cd799439022"
LANG_ID = "507f1f77bcf86cd799439011"


def make_db_doc(
    id: str = WORD_ID,
    language_id: str = LANG_ID,
    word_foreign: str = "学习",
    translation: str = "учёба",
    word_number: int = 1,
):
    return {
        "_id": ObjectId(id),
        "language_id": ObjectId(language_id),
        "word_foreign": word_foreign,
        "translation": translation,
        "transcription": None,
        "word_number": word_number,
        "radicals": None,
        "references": None,
        "tones": None,
        "sounds": None,
        "created_at": datetime(2024, 1, 1),
        "updated_at": datetime(2024, 1, 1),
    }


@pytest.fixture
def repo(mock_db):
    col = MagicMock()
    col.insert_one = AsyncMock()
    col.find_one = AsyncMock(return_value=None)
    col.update_one = AsyncMock()
    col.delete_one = AsyncMock()
    mock_db.words = col
    return WordRepository(mock_db)


class TestCreate:
    @pytest.mark.asyncio
    async def test_create_returns_word_in_db(self, repo, mock_db):
        doc = make_db_doc()
        insert_result = MagicMock()
        insert_result.inserted_id = doc["_id"]
        mock_db.words.insert_one.return_value = insert_result
        mock_db.words.find_one.return_value = dict(doc)

        result = await repo.create(WordCreate(
            language_id=LANG_ID,
            word_foreign="学习",
            translation="учёба",
            word_number=1,
        ))
        assert result.word_foreign == "学习"
        assert result.id == WORD_ID

    @pytest.mark.asyncio
    async def test_create_calls_insert_one(self, repo, mock_db):
        doc = make_db_doc()
        insert_result = MagicMock()
        insert_result.inserted_id = doc["_id"]
        mock_db.words.insert_one.return_value = insert_result
        mock_db.words.find_one.return_value = dict(doc)
        await repo.create(WordCreate(
            language_id=LANG_ID,
            word_foreign="x",
            translation="y",
            word_number=1,
        ))
        mock_db.words.insert_one.assert_called_once()


class TestGetById:
    @pytest.mark.asyncio
    async def test_get_existing_word(self, repo, mock_db):
        doc = make_db_doc()
        mock_db.words.find_one.return_value = dict(doc)
        result = await repo.get_by_id(WORD_ID)
        assert result is not None
        assert result.id == WORD_ID
        assert result.language_id == LANG_ID

    @pytest.mark.asyncio
    async def test_get_nonexistent_word_returns_none(self, repo, mock_db):
        mock_db.words.find_one.return_value = None
        result = await repo.get_by_id(WORD_ID)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_invalid_id_returns_none(self, repo):
        result = await repo.get_by_id("not-valid")
        assert result is None


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_existing_word(self, repo, mock_db):
        delete_result = MagicMock()
        delete_result.deleted_count = 1
        mock_db.words.delete_one.return_value = delete_result
        result = await repo.delete(WORD_ID)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_word(self, repo, mock_db):
        delete_result = MagicMock()
        delete_result.deleted_count = 0
        mock_db.words.delete_one.return_value = delete_result
        result = await repo.delete(WORD_ID)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_invalid_id_returns_false(self, repo):
        result = await repo.delete("bad-id")
        assert result is False
