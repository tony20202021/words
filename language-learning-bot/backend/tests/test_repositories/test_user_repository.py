"""
Tests for UserRepository.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.db.repositories.user_repository import UserRepository
from app.api.models.user import UserCreate, UserUpdate


USER_ID = "507f1f77bcf86cd799439033"


def make_db_doc(
    id: str = USER_ID,
    telegram_id: int = 123456789,
    username: str = "testuser",
):
    return {
        "_id": ObjectId(id),
        "telegram_id": telegram_id,
        "username": username,
        "first_name": "Test",
        "last_name": "User",
        "is_admin": False,
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
    col.count_documents = AsyncMock(return_value=0)
    mock_db.users = col
    return UserRepository(mock_db)


class TestCreate:
    @pytest.mark.asyncio
    async def test_create_returns_user_in_db(self, repo, mock_db):
        doc = make_db_doc()
        insert_result = MagicMock()
        insert_result.inserted_id = doc["_id"]
        mock_db.users.insert_one.return_value = insert_result
        mock_db.users.find_one.return_value = dict(doc)

        result = await repo.create(UserCreate(
            telegram_id=123456789,
            first_name="Test",
            username="testuser",
            is_admin=False,
        ))
        assert result.telegram_id == 123456789
        assert result.id == USER_ID


class TestGetById:
    @pytest.mark.asyncio
    async def test_get_existing_user(self, repo, mock_db):
        doc = make_db_doc()
        mock_db.users.find_one.return_value = dict(doc)
        result = await repo.get_by_id(USER_ID)
        assert result is not None
        assert result.id == USER_ID

    @pytest.mark.asyncio
    async def test_get_nonexistent_user_returns_none(self, repo, mock_db):
        mock_db.users.find_one.return_value = None
        result = await repo.get_by_id(USER_ID)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_invalid_id_returns_none(self, repo):
        result = await repo.get_by_id("not-valid-objectid")
        assert result is None


class TestGetByTelegramId:
    @pytest.mark.asyncio
    async def test_found(self, repo, mock_db):
        doc = make_db_doc()
        mock_db.users.find_one.return_value = dict(doc)
        result = await repo.get_by_telegram_id(123456789)
        assert result is not None
        assert result.telegram_id == 123456789

    @pytest.mark.asyncio
    async def test_not_found(self, repo, mock_db):
        mock_db.users.find_one.return_value = None
        result = await repo.get_by_telegram_id(0)
        assert result is None

    @pytest.mark.asyncio
    async def test_calls_find_one_with_telegram_id(self, repo, mock_db):
        mock_db.users.find_one.return_value = None
        await repo.get_by_telegram_id(42)
        mock_db.users.find_one.assert_called_with({"telegram_id": 42})


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_existing_user(self, repo, mock_db):
        delete_result = MagicMock()
        delete_result.deleted_count = 1
        mock_db.users.delete_one.return_value = delete_result
        result = await repo.delete(USER_ID)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, repo, mock_db):
        delete_result = MagicMock()
        delete_result.deleted_count = 0
        mock_db.users.delete_one.return_value = delete_result
        result = await repo.delete(USER_ID)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_invalid_id_returns_false(self, repo):
        result = await repo.delete("invalid-id")
        assert result is False
