"""
«На сегодня всё повторено!», когда впереди тысячи слов.

Владелец прошёл 100 слов из 9995 и дважды за утро получил этот экран. Партия
набирается окном в 100 номеров: утром в первом окне было лишь несколько слов к
повторению, а новые лежали дальше, с №101. Кончилась партия — и сервер отвечал
«слов нет», хотя в ту же минуту, собирая офлайн-партию, сам находил 100 новых.

Здесь словарь устроен ровно так: в окне 1–100 два слова к повторению, дальше
новые. Проверяется, что ни один путь не объявляет «всё», пока слова есть.
"""

import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.api.client import get_api_client
from app.services import session_service


def _word(n):
    return {"_id": f"w{n}", "word_number": n, "word_foreign": f"f{n}",
            "translation": f"t{n}", "transcription": "", "language_id": "lang1",
            "sounds": None}


def _dictionary(total):
    """Окно 1–100: два слова к повторению (2 и 7). С №101 — новые, до total."""
    async def study_words(user_id, language_id, params, limit=100):
        start = params["start_word"]
        if start <= 100:
            return {"success": True, "result": [_word(2), _word(7)]}
        nums = range(start, min(start + limit, total + 1))
        return {"success": True, "result": [_word(n) for n in nums]}
    return study_words


def _make_api(total=9995):
    api = AsyncMock()
    ok = {"success": True, "result": {"score": 1, "check_interval": 1,
          "next_check_date": "2026-06-01", "is_skipped": False}}
    api.get_study_words.side_effect = _dictionary(total)
    api.get_user_language_settings.return_value = {"success": True, "result": {}}
    api.get_user_word_data.return_value = {"success": True, "result": None}
    api.create_user_word_data.return_value = ok
    api.update_user_word_data.return_value = ok
    api.get_user_progress.return_value = {"success": True, "result": {}}
    api.get_daily_first_finish_statistics.return_value = {
        "success": True, "status": 404, "result": None}
    return api


@pytest.fixture
def api():
    return _make_api()


@pytest.fixture(autouse=True)
def _override(api):
    app.dependency_overrides[get_api_client] = lambda: api
    yield
    app.dependency_overrides.pop(get_api_client, None)


@pytest.fixture
def client():
    return TestClient(app)


def _finish_first_batch(client, user):
    session_service.end_session(user, "lang1")
    resp = client.post("/session/start", json={"user_id": user, "language_id": "lang1"})
    assert resp.status_code == 200
    sid = resp.json()["session_id"]
    for _ in range(2):   # два слова к повторению
        last = client.post(f"/session/{sid}/rate", json={"rating": "know"})
    assert last.json().get("batch_exhausted") is True
    return sid


def test_resuming_an_exhausted_session_brings_new_words(client):
    """
    Второй снимок владельца: в 12:03 приложение вернулось к утренней, уже
    пройденной сессии — и получило «слов нет». Слова были: 100 новых с №101.
    """
    _finish_first_batch(client, "u-resume")
    resp = client.get("/session/u-resume/lang1")
    body = resp.json()
    assert body.get("card") is not None, "возобновление объявило «всё», хотя впереди новые слова"
    assert body["card"]["meta"]["word_number"] >= 101


def test_it_really_ends_only_when_words_run_out():
    """«Всё» остаётся правдой там, где оно правда: словарь кончился."""
    small = _make_api(total=100)          # после окна 1–100 слов нет
    app.dependency_overrides[get_api_client] = lambda: small
    client = TestClient(app)
    _finish_first_batch(client, "u-end")
    body = client.get("/session/u-end/lang1").json()
    assert body.get("card") is None and body.get("no_words") is True


def test_offline_bundle_reaches_new_words(client):
    """
    Офлайн-партия брала только первое непустое окно — два слова. Пройдя их без
    сети, человек получал «всё». Теперь она добирается новыми словами до 100.
    """
    session_service.end_session("u-bundle", "lang1")
    resp = client.post("/session/u-bundle/lang1/bundle")
    assert resp.status_code == 200
    numbers = [u["word_number"] for u in resp.json()["words"]]
    assert numbers[:2] == [2, 7], "сначала слова к повторению"
    assert len(numbers) == 100, f"в партии {len(numbers)} слов вместо 100"
    assert all(n >= 101 for n in numbers[2:]), "дальше — новые, с №101"
