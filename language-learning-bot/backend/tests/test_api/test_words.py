"""
Tests for words API routes.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from tests.conftest import make_word, make_language


class TestGetWord:
    def test_get_existing_word(self, client, mock_word_repo):
        word = make_word()
        mock_word_repo.get_word_with_language_info.return_value = word
        response = client.get(f"/api/words/{word.id}")
        assert response.status_code == 200
        assert response.json()["id"] == word.id

    def test_get_nonexistent_word_returns_404(self, client, mock_word_repo):
        mock_word_repo.get_word_with_language_info.return_value = None
        response = client.get("/api/words/000000000000000000000000")
        assert response.status_code == 404

    def test_get_word_fields(self, client, mock_word_repo):
        word = make_word(word_foreign="水", translation="вода")
        mock_word_repo.get_word_with_language_info.return_value = word
        response = client.get(f"/api/words/{word.id}")
        data = response.json()
        assert data["word_foreign"] == "水"
        assert data["translation"] == "вода"


class TestCreateWord:
    def test_create_word_success(self, client, mock_word_repo, mock_language_repo):
        lang = make_language()
        new_word = make_word()
        mock_language_repo.get_by_id.return_value = lang
        mock_word_repo.create.return_value = new_word
        response = client.post("/api/words/", json={
            "language_id": lang.id,
            "word_foreign": "学习",
            "translation": "учёба",
            "word_number": 1,
        })
        assert response.status_code == 201

    def test_create_word_invalid_language_returns_400(self, client, mock_language_repo):
        mock_language_repo.get_by_id.return_value = None
        response = client.post("/api/words/", json={
            "language_id": "000000000000000000000000",
            "word_foreign": "学习",
            "translation": "учёба",
            "word_number": 1,
        })
        assert response.status_code == 400

    def test_create_word_missing_field_returns_422(self, client):
        response = client.post("/api/words/", json={
            "word_foreign": "学习",
            "translation": "учёба",
        })
        assert response.status_code == 422


class TestUpdateWord:
    def test_update_word_success(self, client, mock_word_repo):
        word = make_word()
        updated = make_word(translation="обучение")
        mock_word_repo.get_by_id.return_value = word
        mock_word_repo.update.return_value = updated
        response = client.put(f"/api/words/{word.id}", json={"translation": "обучение"})
        assert response.status_code == 200

    def test_update_nonexistent_word_returns_404(self, client, mock_word_repo):
        mock_word_repo.get_by_id.return_value = None
        response = client.put("/api/words/000000000000000000000000", json={"translation": "x"})
        assert response.status_code == 404


class TestDeleteWord:
    def test_delete_existing_word(self, client, mock_word_repo):
        word = make_word()
        mock_word_repo.get_by_id.return_value = word
        mock_word_repo.delete.return_value = True
        response = client.delete(f"/api/words/{word.id}")
        assert response.status_code == 200

    def test_delete_nonexistent_word_returns_404(self, client, mock_word_repo):
        mock_word_repo.get_by_id.return_value = None
        response = client.delete("/api/words/000000000000000000000000")
        assert response.status_code == 404
