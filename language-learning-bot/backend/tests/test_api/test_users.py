"""
Tests for users API routes.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from tests.conftest import make_user


class TestGetUsers:
    def test_get_users_empty(self, client):
        response = client.get("/api/users/")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_users_returns_list(self, client, mock_user_repo):
        user = make_user()
        mock_user_repo.get_all.return_value = [user]
        response = client.get("/api/users/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["telegram_id"] == user.telegram_id

    def test_get_users_by_telegram_id(self, client, mock_user_repo):
        user = make_user(telegram_id=99887766)
        mock_user_repo.get_by_telegram_id.return_value = user
        response = client.get("/api/users/?telegram_id=99887766")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["telegram_id"] == 99887766

    def test_get_users_by_unknown_telegram_id_returns_empty(self, client, mock_user_repo):
        mock_user_repo.get_by_telegram_id.return_value = None
        response = client.get("/api/users/?telegram_id=0")
        assert response.status_code == 200
        assert response.json() == []


class TestGetUserById:
    def test_get_existing_user(self, client, mock_user_repo):
        user = make_user()
        mock_user_repo.get_by_id.return_value = user
        response = client.get(f"/api/users/{user.id}")
        assert response.status_code == 200
        assert response.json()["id"] == user.id

    def test_get_nonexistent_user_returns_404(self, client, mock_user_repo):
        mock_user_repo.get_by_id.return_value = None
        response = client.get("/api/users/000000000000000000000000")
        assert response.status_code == 404


class TestCreateUser:
    def test_create_user_success(self, client, mock_user_repo):
        new_user = make_user()
        mock_user_repo.get_by_telegram_id.return_value = None
        mock_user_repo.create.return_value = new_user
        response = client.post("/api/users/", json={
            "telegram_id": 123456789,
            "first_name": "Test",
            "username": "testuser",
            "last_name": "User",
            "is_admin": False,
        })
        assert response.status_code == 201

    def test_create_duplicate_user_returns_400(self, client, mock_user_repo):
        existing = make_user()
        mock_user_repo.get_by_telegram_id.return_value = existing
        response = client.post("/api/users/", json={
            "telegram_id": existing.telegram_id,
            "first_name": "Test",
            "is_admin": False,
        })
        assert response.status_code == 400

    def test_create_user_missing_telegram_id_returns_422(self, client):
        response = client.post("/api/users/", json={"first_name": "Test"})
        assert response.status_code == 422


class TestUpdateUser:
    def test_update_user_success(self, client, mock_user_repo):
        user = make_user()
        updated = make_user(username="updated_user")
        mock_user_repo.get_by_id.return_value = user
        mock_user_repo.update.return_value = updated
        response = client.put(f"/api/users/{user.id}", json={"username": "updated_user"})
        assert response.status_code == 200

    def test_update_nonexistent_user_returns_404(self, client, mock_user_repo):
        mock_user_repo.get_by_id.return_value = None
        response = client.put("/api/users/000000000000000000000000", json={"username": "x"})
        assert response.status_code == 404


class TestDeleteUser:
    def test_delete_existing_user(self, client, mock_user_repo):
        user = make_user()
        mock_user_repo.get_by_id.return_value = user
        mock_user_repo.delete.return_value = True
        response = client.delete(f"/api/users/{user.id}")
        assert response.status_code == 200

    def test_delete_nonexistent_user_returns_404(self, client, mock_user_repo):
        mock_user_repo.get_by_id.return_value = None
        response = client.delete("/api/users/000000000000000000000000")
        assert response.status_code == 404


class TestUsersCount:
    def test_get_users_count(self, client, mock_user_repo):
        mock_user_repo.count.return_value = 42
        response = client.get("/api/users/count")
        assert response.status_code == 200
        assert response.json()["count"] == 42
