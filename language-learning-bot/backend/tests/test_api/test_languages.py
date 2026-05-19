"""
Tests for languages API routes.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from tests.conftest import make_language, make_word


class TestGetLanguages:
    def test_get_languages_empty(self, client):
        response = client.get("/api/languages/")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_languages_returns_list(self, client, mock_language_repo):
        lang = make_language()
        mock_language_repo.get_all.return_value = [lang]
        response = client.get("/api/languages/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name_ru"] == lang.name_ru

    def test_get_languages_multiple(self, client, mock_language_repo):
        langs = [
            make_language(id="507f1f77bcf86cd799439011", name_ru="Китайский"),
            make_language(id="507f1f77bcf86cd799439012", name_ru="Японский", name_foreign="日本語"),
        ]
        mock_language_repo.get_all.return_value = langs
        response = client.get("/api/languages/")
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestGetLanguageById:
    def test_get_existing_language(self, client, mock_language_repo):
        lang = make_language()
        mock_language_repo.get_by_id.return_value = lang
        response = client.get(f"/api/languages/{lang.id}")
        assert response.status_code == 200
        assert response.json()["id"] == lang.id

    def test_get_nonexistent_language_returns_404(self, client, mock_language_repo):
        mock_language_repo.get_by_id.return_value = None
        response = client.get("/api/languages/000000000000000000000000")
        assert response.status_code == 404

    def test_get_language_name_fields(self, client, mock_language_repo):
        lang = make_language(name_ru="Корейский", name_foreign="한국어")
        mock_language_repo.get_by_id.return_value = lang
        response = client.get(f"/api/languages/{lang.id}")
        data = response.json()
        assert data["name_ru"] == "Корейский"
        assert data["name_foreign"] == "한국어"


class TestCreateLanguage:
    def test_create_language_success(self, client, mock_language_repo):
        new_lang = make_language(name_ru="Английский", name_foreign="English")
        mock_language_repo.get_by_name_ru.return_value = None
        mock_language_repo.create.return_value = new_lang
        response = client.post("/api/languages/", json={
            "name_ru": "Английский",
            "name_foreign": "English",
        })
        assert response.status_code == 201
        assert response.json()["name_ru"] == "Английский"

    def test_create_language_missing_field_returns_422(self, client):
        response = client.post("/api/languages/", json={"name_ru": "Английский"})
        assert response.status_code == 422

    def test_create_duplicate_language_returns_400(self, client, mock_language_repo):
        existing = make_language()
        mock_language_repo.get_by_name_ru.return_value = existing
        response = client.post("/api/languages/", json={
            "name_ru": existing.name_ru,
            "name_foreign": existing.name_foreign,
        })
        assert response.status_code == 400


class TestUpdateLanguage:
    def test_update_language_success(self, client, mock_language_repo):
        lang = make_language()
        updated = make_language(name_ru="Обновлённый")
        mock_language_repo.get_by_id.return_value = lang
        mock_language_repo.update.return_value = updated
        response = client.put(f"/api/languages/{lang.id}", json={"name_ru": "Обновлённый"})
        assert response.status_code == 200
        assert response.json()["name_ru"] == "Обновлённый"

    def test_update_nonexistent_language_returns_404(self, client, mock_language_repo):
        mock_language_repo.get_by_id.return_value = None
        response = client.put("/api/languages/000000000000000000000000", json={"name_ru": "X"})
        assert response.status_code == 404


class TestDeleteLanguage:
    def test_delete_existing_language(self, client, mock_language_repo):
        lang = make_language()
        mock_language_repo.get_by_id.return_value = lang
        mock_language_repo.delete.return_value = True
        response = client.delete(f"/api/languages/{lang.id}")
        assert response.status_code == 200

    def test_delete_nonexistent_language_returns_404(self, client, mock_language_repo):
        mock_language_repo.get_by_id.return_value = None
        response = client.delete("/api/languages/000000000000000000000000")
        assert response.status_code == 404
