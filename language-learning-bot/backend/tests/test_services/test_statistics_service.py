"""
Tests for StatisticsService.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.services.statistics_service import StatisticsService
from tests.conftest import make_user


@pytest.fixture
def service(mock_statistics_repo, mock_word_repo):
    return StatisticsService(mock_statistics_repo, mock_word_repo)


class TestGetUserStatistics:
    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_stats(self, service, mock_statistics_repo):
        mock_statistics_repo.get_by_user_id.return_value = []
        result = await service.get_user_statistics("user_id")
        assert result == []

    @pytest.mark.asyncio
    async def test_calls_repo_with_correct_args(self, service, mock_statistics_repo):
        mock_statistics_repo.get_by_user_id.return_value = []
        await service.get_user_statistics("uid", language_id="lid", skip=2, limit=5)
        mock_statistics_repo.get_by_user_id.assert_called_once_with(
            user_id="uid",
            language_id="lid",
            skip=2,
            limit=5,
            validate_words=False,
        )

    @pytest.mark.asyncio
    async def test_returns_stats_list(self, service, mock_statistics_repo):
        stats = [MagicMock(), MagicMock()]
        mock_statistics_repo.get_by_user_id.return_value = stats
        result = await service.get_user_statistics("uid")
        assert len(result) == 2


class TestCreateUserWordStatistics:
    @pytest.mark.asyncio
    async def test_create_calls_repo(self, service, mock_statistics_repo):
        stat = MagicMock()
        mock_statistics_repo.create.return_value = stat
        stat_data = MagicMock()
        result = await service.create_user_word_statistics("user_id", stat_data)
        assert result is stat
        mock_statistics_repo.create.assert_called_once_with("user_id", stat_data)


class TestDeleteUserWordStatistics:
    @pytest.mark.asyncio
    async def test_delete_existing_stat(self, service, mock_statistics_repo):
        mock_statistics_repo.delete.return_value = True
        result = await service.delete_user_word_statistics("uid", "wid")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_stat(self, service, mock_statistics_repo):
        mock_statistics_repo.delete.return_value = False
        result = await service.delete_user_word_statistics("uid", "wid")
        assert result is False
