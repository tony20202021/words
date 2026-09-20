"""
«На сегодня всё повторено!», когда впереди тысячи слов.

Владелец прошёл 100 слов из 9995 и дважды за утро получил этот экран. Партия
тогда набиралась окном в 100 НОМЕРОВ: утром в первом окне было лишь несколько
слов к повторению, а новые лежали дальше, с №101. Кончилась партия — и сервер
отвечал «слов нет», хотя в ту же минуту, собирая офлайн-партию, сам находил 100
новых.

Окон больше нет: бэкенд отбирает подходящие слова в самом запросе и отдаёт
столько, сколько попросили. Здесь словарь устроен так, что к повторению годятся
только два слова в начале, а дальше идут новые. Проверяется, что ни один путь
не объявляет «всё», пока слова есть, — и что продолжение партии не зависит от
шага в сто номеров: номера идут с пропусками.
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


def _dictionary(total, due=(2, 7), first_new=101, step=1):
    """
    Бэкенд нового образца: отдаёт до `limit` ПОДХОДЯЩИХ слов от номера start_word.

    Годятся два слова к повторению (2 и 7) и всё, что начиная с first_new, —
    там слова, которых человек ещё не видел. `step` задаёт пропуски в нумерации:
    при step=3 существуют номера 101, 104, 107… — так устроены настоящие
    словари (в английском 1534 номера из 10 000 пустые).
    """
    async def study_words(user_id, language_id, params, limit=100):
        start = params["start_word"]
        suitable = [n for n in due if n >= start]
        suitable += [n for n in range(first_new, total + 1, step) if n >= start]
        return {"success": True, "result": [_word(n) for n in sorted(suitable)[:limit]]}
    return study_words


def _make_api(total=9995, **kwargs):
    api = AsyncMock()
    ok = {"success": True, "result": {"score": 1, "check_interval": 1,
          "next_check_date": "2026-06-01", "is_skipped": False}}
    api.get_study_words.side_effect = _dictionary(total, **kwargs)
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


@pytest.fixture(autouse=True)
def _small_batch(monkeypatch):
    """Партия из пяти слов: те же пути, но проходятся пятью ответами, а не ста."""
    monkeypatch.setattr(session_service, "BATCH_SIZE", 5)


@pytest.fixture
def client():
    return TestClient(app)


def _start(client, user):
    session_service.end_session(user, "lang1")
    resp = client.post("/session/start", json={"user_id": user, "language_id": "lang1"})
    assert resp.status_code == 200
    return resp.json()["session_id"]


def _finish_batch(client, sid, count=5):
    last = None
    for _ in range(count):
        last = client.post(f"/session/{sid}/rate", json={"rating": "know"})
    return last


def test_the_batch_is_full_even_when_only_two_words_are_due(client):
    """
    Главная перемена: партия — это сто (здесь пять) подходящих слов, а не
    сколько наскребётся в первой сотне номеров. Двух слов к повторению уже
    недостаточно, чтобы партия кончилась.
    """
    sid = _start(client, "u-full")
    session = session_service.get_session_by_id(sid)
    numbers = [w["word_number"] for w in session["words"]]
    assert len(numbers) == 5, f"в партии {len(numbers)} слов вместо пяти: {numbers}"
    assert numbers[:2] == [2, 7], "сначала слова к повторению"
    assert all(n >= 101 for n in numbers[2:]), "дальше — новые, с №101"


def test_resuming_an_exhausted_session_brings_new_words(client):
    """
    Второй снимок владельца: в 12:03 приложение вернулось к утренней, уже
    пройденной сессии — и получило «слов нет». Слова были.
    """
    sid = _start(client, "u-resume")
    assert _finish_batch(client, sid).json().get("batch_exhausted") is True
    body = client.get("/session/u-resume/lang1").json()
    assert body.get("card") is not None, "возобновление объявило «всё», хотя впереди новые слова"
    assert body["card"]["meta"]["word_number"] >= 101


def test_the_next_batch_continues_after_the_last_word_given(client):
    """
    Продолжение считается от последнего выданного номера, а не «плюс сто».
    Номера идут с пропусками: шаг в сто номеров попадал внутрь уже выданного,
    и слова приходили по второму разу.
    """
    sparse = _make_api(step=3)          # существуют 101, 104, 107, …
    app.dependency_overrides[get_api_client] = lambda: sparse
    client = TestClient(app)
    sid = _start(client, "u-gaps")
    first = [w["word_number"] for w in session_service.get_session_by_id(sid)["words"]]
    _finish_batch(client, sid)

    resp = client.post(f"/session/{sid}/next_batch")
    assert resp.status_code == 200
    second = [w["word_number"] for w in session_service.get_session_by_id(sid)["words"]]
    assert not set(first) & set(second), f"слова пришли по второму разу: {first} → {second}"
    assert min(second) > max(first), "следующая партия начинается после выданного"


def test_it_really_ends_only_when_words_run_out():
    """«Всё» остаётся правдой там, где оно правда: словарь кончился."""
    small = _make_api(total=100)          # кроме двух повторов подходящих нет
    app.dependency_overrides[get_api_client] = lambda: small
    client = TestClient(app)
    sid = _start(client, "u-end")
    _finish_batch(client, sid, count=2)
    body = client.get("/session/u-end/lang1").json()
    assert body.get("card") is None and body.get("no_words") is True


def test_offline_bundle_reaches_new_words(client):
    """
    Офлайн-партия брала только первое непустое окно — два слова. Пройдя их без
    сети, человек получал «всё». Теперь в ней столько слов, сколько попросили.
    """
    session_service.end_session("u-bundle", "lang1")
    resp = client.post("/session/u-bundle/lang1/bundle")
    assert resp.status_code == 200
    numbers = [u["word_number"] for u in resp.json()["words"]]
    assert numbers[:2] == [2, 7], "сначала слова к повторению"
    assert len(numbers) == 5, f"в партии {len(numbers)} слов вместо пяти"
    assert all(n >= 101 for n in numbers[2:]), "дальше — новые, с №101"


def test_offline_bundle_does_not_stop_at_gaps_in_numbering():
    """
    Из-за пропусков в нумерации добор офлайн-партии обрывался на первом же
    шаге: следующее окно попадало внутрь уже прочитанного и приносило одни
    повторы. У живого пользователя в партии оказывалось 13 слов вместо ста.
    """
    sparse = _make_api(step=3)
    app.dependency_overrides[get_api_client] = lambda: sparse
    client = TestClient(app)
    session_service.end_session("u-bundle-gaps", "lang1")
    resp = client.post("/session/u-bundle-gaps/lang1/bundle")
    assert resp.status_code == 200
    numbers = [u["word_number"] for u in resp.json()["words"]]
    assert len(numbers) == 5, f"в партии {len(numbers)} слов вместо пяти: {numbers}"
    assert len(set(numbers)) == len(numbers), f"в партии повторы: {numbers}"
