"""
Маршруты сессии: порядок объявления значим.

GET /session/{session_id}/progress состоит из двух сегментов, ровно как
GET /session/{user_id}/{language_id}. FastAPI берёт первый подходящий маршрут,
поэтому объявленный раньше шаблон из двух переменных проглатывал «abc/progress»,
разбирая его как user_id=abc, language_id=progress. Ручка прогресса была
недостижима: на экране «Сессия завершена!» пропадала строка «Обработано слов»,
и ни один тест этого не видел, потому что роутер не проверялся по HTTP.
"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import session as sess


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(sess.router)
    return TestClient(app)


def test_progress_route_is_reachable(client):
    seen = []
    with patch.object(sess.session_service, "get_session_by_id",
                      side_effect=lambda sid: (seen.append(sid), {"session_id": sid})[1]), \
         patch.object(sess.session_service, "get_progress",
                      return_value={"total_words_processed": 7}), \
         patch.object(sess.session_service, "get_session",
                      side_effect=AssertionError("сработал маршрут /{user_id}/{language_id}")):
        r = client.get("/session/abc123/progress")

    assert r.status_code == 200
    assert r.json() == {"total_words_processed": 7}
    assert seen == ["abc123"], "прогресс должен искаться по session_id"


def test_progress_route_is_declared_before_the_two_segment_one():
    """
    Проверка на порядок, а не на поведение: перестановка маршрутов ломает первый
    тест неочевидным образом, и без этой проверки причина была бы не видна.
    """
    app = FastAPI()
    app.include_router(sess.router)
    paths = [r.path for r in app.routes if getattr(r, "path", "").startswith("/session")
             and "GET" in getattr(r, "methods", set())]
    assert paths.index("/session/{session_id}/progress") < \
           paths.index("/session/{user_id}/{language_id}"), paths


def test_session_route_still_works(client):
    with patch.object(sess.session_service, "get_session", return_value=None):
        r = client.get("/session/user1/lang1")
    assert r.status_code == 404
    assert r.json()["detail"] == "No active session"
