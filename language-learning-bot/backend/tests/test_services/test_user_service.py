"""
Tests for UserService.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.services.user_service import UserService
from app.api.models.user import UserCreate, UserUpdate
from tests.conftest import make_user


@pytest.fixture
def service(mock_user_repo):
    return UserService(mock_user_repo)


class TestGetUsers:
    @pytest.mark.asyncio
    async def test_get_users_empty(self, service, mock_user_repo):
        mock_user_repo.get_all.return_value = []
        result = await service.get_users()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_users_returns_list(self, service, mock_user_repo):
        users = [make_user(id="aaa"), make_user(id="bbb", telegram_id=111)]
        mock_user_repo.get_all.return_value = users
        result = await service.get_users()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_users_calls_repo(self, service, mock_user_repo):
        mock_user_repo.get_all.return_value = []
        await service.get_users(skip=5, limit=10)
        mock_user_repo.get_all.assert_called_once_with(skip=5, limit=10)


class TestGetUser:
    @pytest.mark.asyncio
    async def test_get_existing_user(self, service, mock_user_repo):
        user = make_user()
        mock_user_repo.get_by_id.return_value = user
        result = await service.get_user(user.id)
        assert result is not None
        assert result.telegram_id == user.telegram_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_user_returns_none(self, service, mock_user_repo):
        mock_user_repo.get_by_id.return_value = None
        result = await service.get_user("000")
        assert result is None


class TestGetUserByTelegramId:
    @pytest.mark.asyncio
    async def test_get_by_telegram_id_found(self, service, mock_user_repo):
        user = make_user(telegram_id=42)
        mock_user_repo.get_by_telegram_id.return_value = user
        result = await service.get_user_by_telegram_id(42)
        assert result.telegram_id == 42

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_not_found(self, service, mock_user_repo):
        mock_user_repo.get_by_telegram_id.return_value = None
        result = await service.get_user_by_telegram_id(0)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_calls_repo(self, service, mock_user_repo):
        mock_user_repo.get_by_telegram_id.return_value = None
        await service.get_user_by_telegram_id(999)
        mock_user_repo.get_by_telegram_id.assert_called_once_with(999)


class TestCreateUser:
    @pytest.mark.asyncio
    async def test_create_user_success(self, service, mock_user_repo):
        created = make_user()
        mock_user_repo.create.return_value = created
        user_data = UserCreate(
            telegram_id=123456789,
            first_name="Test",
            username="testuser",
            is_admin=False,
        )
        result = await service.create_user(user_data)
        assert result.telegram_id == created.telegram_id
        mock_user_repo.create.assert_called_once_with(user_data)


class TestUpdateUser:
    @pytest.mark.asyncio
    async def test_update_user_success(self, service, mock_user_repo):
        updated = make_user(username="new_name")
        mock_user_repo.update.return_value = updated
        result = await service.update_user("abc", UserUpdate(username="new_name"))
        assert result.username == "new_name"

    @pytest.mark.asyncio
    async def test_update_nonexistent_user_returns_none(self, service, mock_user_repo):
        mock_user_repo.update.return_value = None
        result = await service.update_user("000", UserUpdate(username="x"))
        assert result is None


class TestDeleteUser:
    @pytest.mark.asyncio
    async def test_delete_user_success(self, service, mock_user_repo):
        mock_user_repo.delete.return_value = True
        result = await service.delete_user("abc")
        assert result is True
        mock_user_repo.delete.assert_called_once_with("abc")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, service, mock_user_repo):
        mock_user_repo.delete.return_value = False
        result = await service.delete_user("000")
        assert result is False
