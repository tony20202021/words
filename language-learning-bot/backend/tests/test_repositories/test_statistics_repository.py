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


def make_daily_doc(max_word_number=None, words_studied=50, words_known=40, words_skipped=0,
                   type="daily", words_unknown=None):
    doc = {
        "_id": ObjectId(STAT_ID),
        "user_id": USER_ID,
        "language_id": LANG_ID,
        "date": TODAY_DT,
        "words_studied": words_studied,
        "words_known": words_known,
        "words_skipped": words_skipped,
        "words_for_today": 20,
        "type": type,
        "created_at": datetime(2026, 6, 7),
        "updated_at": datetime(2026, 6, 7),
    }
    if max_word_number is not None:
        doc["max_word_number"] = max_word_number
    if words_unknown is not None:
        doc["words_unknown"] = words_unknown
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
    async def test_updates_existing_record_uses_max_for_snapshot_fields(self, repo, mock_db):
        """words_known and words_for_today use $max, not $set, on update."""
        existing = make_daily_doc()
        mock_db.user_daily_statistics.find_one.return_value = existing

        stats = UserDailyStatsUpdate(words_known=45, words_skipped=0, words_for_today=15)
        await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats)

        update_call = mock_db.user_daily_statistics.update_one.call_args
        update_ops = update_call.args[1]
        assert "$max" in update_ops
        assert update_ops["$max"]["words_known"] == 45
        assert update_ops["$max"]["words_for_today"] == 15
        assert "words_known" not in update_ops.get("$set", {})
        assert "words_for_today" not in update_ops.get("$set", {})

    @pytest.mark.asyncio
    async def test_zero_words_known_cannot_overwrite_existing(self, repo, mock_db):
        """words_known=0 goes to $max, so it never overwrites a stored non-zero value."""
        existing = make_daily_doc()  # has words_known=40
        mock_db.user_daily_statistics.find_one.return_value = existing

        stats = UserDailyStatsUpdate(words_known=0, words_for_today=0)
        await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats)

        update_call = mock_db.user_daily_statistics.update_one.call_args
        update_ops = update_call.args[1]
        # $max with 0 won't overwrite the stored 40
        assert update_ops["$max"]["words_known"] == 0
        assert update_ops["$max"]["words_for_today"] == 0
        # Neither field must appear in $set
        assert "words_known" not in update_ops.get("$set", {})
        assert "words_for_today" not in update_ops.get("$set", {})

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
    async def test_no_max_word_number_in_max_when_not_provided(self, repo, mock_db):
        """When max_word_number is not provided, it must not appear in $max."""
        existing = make_daily_doc()
        mock_db.user_daily_statistics.find_one.return_value = existing

        stats = UserDailyStatsUpdate(words_known=40, words_skipped=0, words_for_today=20)
        await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats)

        update_call = mock_db.user_daily_statistics.update_one.call_args
        update_ops = update_call.args[1]
        assert "max_word_number" not in update_ops.get("$max", {})

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


# ── first_finish max-unknown comparison ───────────────────────────────────────

class TestFirstFinishMaxUnknown:
    """first_finish stores the daily maximum unknown count via words_unknown field.
    Backend only updates when incoming_unknown > existing_unknown."""

    @pytest.mark.asyncio
    async def test_first_finish_updates_when_unknown_increases(self, repo, mock_db):
        """Incoming words_unknown (20) > existing (10) → update proceeds."""
        existing = make_daily_doc(type="first_finish", words_unknown=10)
        updated = make_daily_doc(type="first_finish", words_unknown=20)
        mock_db.user_daily_statistics.find_one.side_effect = [existing, updated]

        stats = UserDailyStatsUpdate(words_unknown=20)
        await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats, type="first_finish")

        mock_db.user_daily_statistics.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_first_finish_skipped_when_unknown_decreases(self, repo, mock_db):
        """Incoming words_unknown (5) < existing (10) → update is skipped."""
        existing = make_daily_doc(type="first_finish", words_unknown=10)
        mock_db.user_daily_statistics.find_one.side_effect = [existing, {**existing, "_id": existing["_id"]}]

        stats = UserDailyStatsUpdate(words_unknown=5)
        await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats, type="first_finish")

        mock_db.user_daily_statistics.update_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_first_finish_skipped_when_unknown_equal(self, repo, mock_db):
        """Incoming words_unknown == existing → skipped (strictly greater required)."""
        existing = make_daily_doc(type="first_finish", words_unknown=10)
        mock_db.user_daily_statistics.find_one.side_effect = [existing, {**existing, "_id": existing["_id"]}]

        stats = UserDailyStatsUpdate(words_unknown=10)
        await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats, type="first_finish")

        mock_db.user_daily_statistics.update_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_first_finish_created_when_no_record(self, repo, mock_db):
        """No existing first_finish record → always insert with words_unknown."""
        mock_db.user_daily_statistics.find_one.side_effect = [
            None,
            make_daily_doc(type="first_finish", words_unknown=7),
        ]
        insert_result = MagicMock()
        insert_result.inserted_id = ObjectId(STAT_ID)
        mock_db.user_daily_statistics.insert_one.return_value = insert_result

        stats = UserDailyStatsUpdate(words_unknown=7)
        await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats, type="first_finish")

        mock_db.user_daily_statistics.insert_one.assert_called_once()
        inserted = mock_db.user_daily_statistics.insert_one.call_args.args[0]
        assert inserted["words_unknown"] == 7

    @pytest.mark.asyncio
    async def test_first_finish_stores_words_unknown_directly(self, repo, mock_db):
        """Update uses $set {words_unknown: N} — no other fields overwritten."""
        existing = make_daily_doc(type="first_finish", words_unknown=10)
        updated = make_daily_doc(type="first_finish", words_unknown=20)
        mock_db.user_daily_statistics.find_one.side_effect = [existing, updated]

        stats = UserDailyStatsUpdate(words_unknown=20)
        await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats, type="first_finish")

        update_ops = mock_db.user_daily_statistics.update_one.call_args.args[1]
        assert update_ops["$set"]["words_unknown"] == 20
        assert "words_known" not in update_ops.get("$set", {})
        assert "words_studied" not in update_ops.get("$set", {})

    @pytest.mark.asyncio
    async def test_first_finish_legacy_fallback_uses_computed_unknown(self, repo, mock_db):
        """Legacy records without words_unknown field use studied-known-skipped computation."""
        # existing has no words_unknown → computed = 50 - 40 - 0 = 10
        existing = make_daily_doc(words_studied=50, words_known=40, words_skipped=0, type="first_finish")
        updated = make_daily_doc(words_studied=50, words_known=40, words_skipped=0, type="first_finish",
                                 words_unknown=20)
        mock_db.user_daily_statistics.find_one.side_effect = [existing, updated]

        # incoming unknown=20 via direct field
        stats = UserDailyStatsUpdate(words_unknown=20)
        await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats, type="first_finish")

        mock_db.user_daily_statistics.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_last_finish_always_updates(self, repo, mock_db):
        """last_finish type always overwrites regardless of unknown count."""
        existing = make_daily_doc(type="last_finish", words_unknown=20)
        updated = make_daily_doc(type="last_finish", words_unknown=5)
        mock_db.user_daily_statistics.find_one.side_effect = [existing, updated]

        stats = UserDailyStatsUpdate(words_unknown=5)
        await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats, type="last_finish")

        mock_db.user_daily_statistics.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_last_finish_stores_words_unknown_directly(self, repo, mock_db):
        """last_finish $set stores words_unknown, no other fields overwritten."""
        existing = make_daily_doc(type="last_finish", words_unknown=20)
        updated = make_daily_doc(type="last_finish", words_unknown=5)
        mock_db.user_daily_statistics.find_one.side_effect = [existing, updated]

        stats = UserDailyStatsUpdate(words_unknown=5)
        await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats, type="last_finish")

        update_ops = mock_db.user_daily_statistics.update_one.call_args.args[1]
        assert update_ops["$set"]["words_unknown"] == 5
        assert "words_known" not in update_ops.get("$set", {})

    @pytest.mark.asyncio
    async def test_daily_type_uses_max_for_words_known(self, repo, mock_db):
        """daily type uses $max for words_known (BLS restart race protection)."""
        existing = make_daily_doc()
        mock_db.user_daily_statistics.find_one.return_value = existing

        stats = UserDailyStatsUpdate(words_known=30, words_for_today=5)
        await repo.create_or_update_daily_stats(USER_ID, LANG_ID, TODAY, stats)

        update_ops = mock_db.user_daily_statistics.update_one.call_args.args[1]
        assert update_ops["$max"]["words_known"] == 30
        assert "words_known" not in update_ops.get("$set", {})
