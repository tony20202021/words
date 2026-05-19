"""
Tests for statistics API routes.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from tests.conftest import make_user


class TestGetUserStatistics:
    def test_get_statistics_user_not_found_returns_404(self, client, mock_user_repo):
        mock_user_repo.get_by_id.return_value = None
        response = client.get("/api/users/000000000000000000000000/statistics")
        assert response.status_code == 404

    def test_get_statistics_empty_for_existing_user(self, client, mock_user_repo, mock_statistics_repo):
        user = make_user()
        mock_user_repo.get_by_id.return_value = user
        mock_statistics_repo.get_by_user_id.return_value = []
        response = client.get(f"/api/users/{user.id}/statistics")
        assert response.status_code == 200
        assert response.json() == []
