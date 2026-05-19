"""
Tests for StatisticsRepository.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.db.repositories.statistics_repository import StatisticsRepository
from app.api.models.statistics import UserStatisticsCreate, UserStatisticsInDB


STAT_ID = "507f1f77bcf86cd799439044"
USER_ID = "507f1f77bcf86cd799439033"
WORD_ID = "507f1f77bcf86cd799439022"
LANG_ID = "507f1f77bcf86cd799439011"


def make_db_doc(id: str = STAT_ID):
    return {
        "_id": ObjectId(id),
        "user_id": USER_ID,
        "word_id": WORD_ID,
        "language_id": LANG_ID,
        "score": 0,
        "is_skipped": False,
        "check_interval": 0,
        "next_check_date": None,
        "hint_phoneticsound": None,
        "hint_phoneticassociation": None,
        "hint_meaning": None,
        "hint_writing": None,
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

    daily_col = MagicMock()
    daily_col.find_one = AsyncMock(return_value=None)
    daily_col.insert_one = AsyncMock()
    daily_col.update_one = AsyncMock()

    mock_db.user_statistics = col
    mock_db.user_daily_statistics = daily_col
    return StatisticsRepository(mock_db)


class TestCreate:
    @pytest.mark.asyncio
    async def test_create_returns_stat_in_db(self, repo, mock_db):
        doc = make_db_doc()
        insert_result = MagicMock()
        insert_result.inserted_id = doc["_id"]
        mock_db.user_statistics.insert_one.return_value = insert_result
        mock_db.user_statistics.find_one.return_value = dict(doc)

        stat_data = UserStatisticsCreate(
            word_id=WORD_ID,
            language_id=LANG_ID,
            score=0,
            check_interval=0,
        )
        result = await repo.create(USER_ID, stat_data)
        assert result.user_id == USER_ID
        assert result.word_id == WORD_ID

    @pytest.mark.asyncio
    async def test_create_calls_insert_one(self, repo, mock_db):
        doc = make_db_doc()
        insert_result = MagicMock()
        insert_result.inserted_id = doc["_id"]
        mock_db.user_statistics.insert_one.return_value = insert_result
        mock_db.user_statistics.find_one.return_value = dict(doc)

        stat_data = UserStatisticsCreate(
            word_id=WORD_ID,
            language_id=LANG_ID,
        )
        await repo.create(USER_ID, stat_data)
        mock_db.user_statistics.insert_one.assert_called_once()


class TestGetById:
    @pytest.mark.asyncio
    async def test_get_existing_stat(self, repo, mock_db):
        doc = make_db_doc()
        mock_db.user_statistics.find_one.return_value = dict(doc)
        result = await repo.get_by_id(STAT_ID)
        assert result is not None
        assert result.id == STAT_ID

    @pytest.mark.asyncio
    async def test_get_nonexistent_stat_returns_none(self, repo, mock_db):
        mock_db.user_statistics.find_one.return_value = None
        result = await repo.get_by_id(STAT_ID)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_invalid_id_returns_none(self, repo):
        result = await repo.get_by_id("not-valid")
        assert result is None


class TestGetByUserId:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_stats(self, repo, mock_db):
        cursor = MagicMock()
        cursor.__aiter__ = MagicMock(return_value=iter([]))
        mock_db.user_statistics.find.return_value = cursor
        mock_db.user_statistics.find.return_value.__aiter__ = MagicMock(return_value=iter([]))

        async def empty_iter():
            return
            yield

        mock_db.user_statistics.find.return_value = MagicMock()
        mock_db.user_statistics.find.return_value.__aiter__ = lambda s: empty_iter().__aiter__()

        result = await repo.get_by_user_id(USER_ID)
        assert result == []
