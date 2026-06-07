"""
Tests for StatisticsRepository.
"""

import pytest
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, call
from bson import ObjectId
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.db.repositories.statistics_repository import StatisticsRepository
from app.api.models.statistics import (
    UserStatisticsCreate, UserStatisticsInDB,
    UserDailyStatsUpdate,
)


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


# ── create_or_update_daily_stats ──────────────────────────────────────────────

TODAY = date(2026, 6, 7)
TODAY_DT = datetime(2026, 6, 7, 0, 0, 0)


def make_daily_doc(max_word_number=None):
    doc = {
        "_id": ObjectId(STAT_ID),
        "user_id": USER_ID,
        "language_id": LANG_ID,
        "date": TODAY_DT,
        "words_studied": 50,
        "words_known": 40,
        "words_skipped": 0,
        "words_for_today": 20,
        "type": "daily",
        "created_at": datetime(2026, 6, 7),
        "updated_at": datetime(2026, 6, 7),
    }
    if max_word_number is not None:
        doc["max_word_number"] = max_word_number
    return doc


class TestCreateOrUpdateDailyStats:
    @pytest.mark.asyncio
    async def test_creates_new_record_when_none_exists(self, repo, mock_db):
        mock_db.user_daily_statistics.find_one.return_value = None
        insert_result = MagicMock()
        insert_result.inserted_id = ObjectId(STAT_ID)
        mock_db.user_daily_statistics.insert_one.return_value = insert_result
        mock_db.user_daily_statistics.find_one.side_effect = [None, make_daily_doc()]

        stats = UserDailyStatsUpdate(words_known=40, words_skipped=0, words_for_today=20)
        result = await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats)

        mock_db.user_daily_statistics.insert_one.assert_called_once()
        assert result.words_known == 40

    @pytest.mark.asyncio
    async def test_updates_existing_record_with_set(self, repo, mock_db):
        existing = make_daily_doc()
        mock_db.user_daily_statistics.find_one.return_value = existing

        stats = UserDailyStatsUpdate(words_known=45, words_skipped=0, words_for_today=15)
        await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats)

        update_call = mock_db.user_daily_statistics.update_one.call_args
        update_ops = update_call.args[1]
        assert "$set" in update_ops
        assert update_ops["$set"].get("words_known") == 45

    @pytest.mark.asyncio
    async def test_max_word_number_uses_dollar_max_operator(self, repo, mock_db):
        """$max ensures only a higher value overwrites the stored max_word_number."""
        existing = make_daily_doc(max_word_number=300)
        mock_db.user_daily_statistics.find_one.return_value = existing

        stats = UserDailyStatsUpdate(
            words_known=40, words_skipped=0, words_for_today=20,
            max_word_number=750,
        )
        await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats)

        update_call = mock_db.user_daily_statistics.update_one.call_args
        update_ops = update_call.args[1]
        assert "$max" in update_ops
        assert update_ops["$max"]["max_word_number"] == 750

    @pytest.mark.asyncio
    async def test_max_word_number_not_in_set_operator(self, repo, mock_db):
        """max_word_number must not appear in $set — only in $max."""
        existing = make_daily_doc(max_word_number=100)
        mock_db.user_daily_statistics.find_one.return_value = existing

        stats = UserDailyStatsUpdate(
            words_known=40, words_skipped=0, words_for_today=20,
            max_word_number=500,
        )
        await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats)

        update_call = mock_db.user_daily_statistics.update_one.call_args
        update_ops = update_call.args[1]
        assert "max_word_number" not in update_ops.get("$set", {})

    @pytest.mark.asyncio
    async def test_no_max_operator_when_max_word_number_is_none(self, repo, mock_db):
        """When max_word_number is not provided, $max must not appear in update."""
        existing = make_daily_doc()
        mock_db.user_daily_statistics.find_one.return_value = existing

        stats = UserDailyStatsUpdate(words_known=40, words_skipped=0, words_for_today=20)
        await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats)

        update_call = mock_db.user_daily_statistics.update_one.call_args
        update_ops = update_call.args[1]
        assert "$max" not in update_ops

    @pytest.mark.asyncio
    async def test_max_word_number_stored_on_new_record(self, repo, mock_db):
        """When creating a new record, max_word_number is included in the document."""
        mock_db.user_daily_statistics.find_one.side_effect = [
            None,
            make_daily_doc(max_word_number=450),
        ]
        insert_result = MagicMock()
        insert_result.inserted_id = ObjectId(STAT_ID)
        mock_db.user_daily_statistics.insert_one.return_value = insert_result

        stats = UserDailyStatsUpdate(
            words_known=40, words_skipped=0, words_for_today=20,
            max_word_number=450,
        )
        result = await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats)

        inserted_doc = mock_db.user_daily_statistics.insert_one.call_args.args[0]
        assert inserted_doc.get("max_word_number") == 450
