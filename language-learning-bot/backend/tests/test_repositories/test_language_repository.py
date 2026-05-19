"""
Tests for LanguageRepository.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.db.repositories.language_repository import LanguageRepository
from app.api.models.language import LanguageCreate, LanguageUpdate


LANG_ID = "507f1f77bcf86cd799439011"


def make_db_doc(
    id: str = LANG_ID,
    name_ru: str = "Китайский",
    name_foreign: str = "中文",
):
    return {
        "_id": ObjectId(id),
        "name_ru": name_ru,
        "name_foreign": name_foreign,
        "created_at": datetime(2024, 1, 1),
        "updated_at": datetime(2024, 1, 1),
    }


def make_mock_collection():
    col = MagicMock()
    col.insert_one = AsyncMock()
    col.find_one = AsyncMock(return_value=None)
    col.update_one = AsyncMock()
    col.delete_one = AsyncMock()
    return col


@pytest.fixture
def repo(mock_db):
    col = make_mock_collection()
    mock_db.languages = col
    return LanguageRepository(mock_db)


class TestCreate:
    @pytest.mark.asyncio
    async def test_create_returns_language_in_db(self, repo, mock_db):
        doc = make_db_doc()
        insert_result = MagicMock()
        insert_result.inserted_id = doc["_id"]
        mock_db.languages.insert_one.return_value = insert_result
        mock_db.languages.find_one.return_value = dict(doc)

        result = await repo.create(LanguageCreate(name_ru="Китайский", name_foreign="中文"))
        assert result.name_ru == "Китайский"
        assert result.id == LANG_ID

    @pytest.mark.asyncio
    async def test_create_calls_insert_one(self, repo, mock_db):
        doc = make_db_doc()
        insert_result = MagicMock()
        insert_result.inserted_id = doc["_id"]
        mock_db.languages.insert_one.return_value = insert_result
        mock_db.languages.find_one.return_value = dict(doc)

        await repo.create(LanguageCreate(name_ru="Китайский", name_foreign="中文"))
        mock_db.languages.insert_one.assert_called_once()


class TestGetById:
    @pytest.mark.asyncio
    async def test_get_existing_language(self, repo, mock_db):
        doc = make_db_doc()
        mock_db.languages.find_one.return_value = dict(doc)
        result = await repo.get_by_id(LANG_ID)
        assert result is not None
        assert result.id == LANG_ID

    @pytest.mark.asyncio
    async def test_get_nonexistent_language_returns_none(self, repo, mock_db):
        mock_db.languages.find_one.return_value = None
        result = await repo.get_by_id(LANG_ID)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_invalid_id_returns_none(self, repo):
        result = await repo.get_by_id("not-a-valid-objectid")
        assert result is None


class TestGetByNameRu:
    @pytest.mark.asyncio
    async def test_get_by_name_ru_found(self, repo, mock_db):
        doc = make_db_doc()
        mock_db.languages.find_one.return_value = dict(doc)
        result = await repo.get_by_name_ru("Китайский")
        assert result is not None
        assert result.name_ru == "Китайский"

    @pytest.mark.asyncio
    async def test_get_by_name_ru_not_found(self, repo, mock_db):
        mock_db.languages.find_one.return_value = None
        result = await repo.get_by_name_ru("Несуществующий")
        assert result is None


class TestUpdate:
    @pytest.mark.asyncio
    async def test_update_calls_update_one(self, repo, mock_db):
        doc = make_db_doc(name_ru="Обновлённый")
        mock_db.languages.update_one.return_value = MagicMock()
        mock_db.languages.find_one.return_value = dict(doc)

        result = await repo.update(LANG_ID, LanguageUpdate(name_ru="Обновлённый"))
        mock_db.languages.update_one.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_invalid_id_returns_none(self, repo):
        result = await repo.update("bad-id", LanguageUpdate(name_ru="X"))
        assert result is None


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_existing_language(self, repo, mock_db):
        delete_result = MagicMock()
        delete_result.deleted_count = 1
        mock_db.languages.delete_one.return_value = delete_result
        result = await repo.delete(LANG_ID)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_language(self, repo, mock_db):
        delete_result = MagicMock()
        delete_result.deleted_count = 0
        mock_db.languages.delete_one.return_value = delete_result
        result = await repo.delete(LANG_ID)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_invalid_id_returns_false(self, repo):
        result = await repo.delete("not-valid")
        assert result is False
