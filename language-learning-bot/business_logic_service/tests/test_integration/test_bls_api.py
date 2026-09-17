"""
Integration tests: BLS FastAPI app with a fully mocked api_client.
Tests exercise the real HTTP layer (TestClient) + real service logic,
but the backend (MongoDB API) is mocked at the api_client level.
"""

import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.api.client import get_api_client


# ── Mock api_client factory ───────────────────────────────────────────────────

def make_api_client(words=None, user_id="user-1"):
    api = AsyncMock()

    api.get_user_by_telegram_id.return_value = {
        "success": True,
        "result": [{"id": user_id, "first_name": "Test", "telegram_id": 123}],
    }
    api.create_user.return_value = {
        "success": True,
        "result": {"id": user_id, "first_name": "Test"},
    }
    api.get_users.return_value = {
        "success": True,
        "result": [{"id": user_id, "first_name": "Test", "telegram_id": 123, "username": "Test"}],
    }
    api.get_user_language_settings.return_value = {"success": True, "result": {}}
    api.get_study_words.return_value = {
        "success": True,
        "result": words or [_make_word(i) for i in range(1, 4)],
    }
    api.get_user_word_data.return_value = {"success": True, "result": None}
    api.create_user_word_data.return_value = {
        "success": True,
        "result": {"score": 1, "check_interval": 1, "next_check_date": "2026-06-01", "is_skipped": False},
    }
    api.update_user_word_data.return_value = {
        "success": True,
        "result": {"score": 1, "check_interval": 1, "next_check_date": "2026-06-01", "is_skipped": False},
    }
    api.get_languages.return_value = {
        "success": True,
        "result": [{"id": "lang1", "name_ru": "Китайский", "name_foreign": "中文"}],
    }
    api.get_user_progress.return_value = {"success": True, "result": {}}
    api.get_daily_first_finish_statistics.return_value = {
        "success": True, "status": 404, "result": None,
    }
    return api


def _make_word(n: int) -> dict:
    return {
        "_id": f"word-{n}", "word_number": n,
        "word_foreign": f"word{n}", "translation": f"слово{n}",
        "transcription": f"[w{n}]", "language_id": "lang1", "sounds": None,
    }


@pytest.fixture
def api():
    return make_api_client()


@pytest.fixture(autouse=True)
def override_api_client(api):
    app.dependency_overrides[get_api_client] = lambda: api
    yield
    app.dependency_overrides.pop(get_api_client, None)


@pytest.fixture
def client():
    return TestClient(app)


# ── User endpoint ─────────────────────────────────────────────────────────────

class TestUserEndpoint:
    def test_get_or_create_user(self, client, api):
        resp = client.post("/user/get_or_create", json={
            "telegram_id": 123, "first_name": "Test"
        })
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "user-1"

    def test_user_not_found_returns_404(self, client, api):
        api.get_user_by_telegram_id.return_value = {"success": True, "result": []}
        api.create_user.return_value = {"success": False, "result": None, "error": "not found"}
        resp = client.post("/user/get_or_create", json={
            "telegram_id": 999, "first_name": "Ghost"
        })
        assert resp.status_code == 404


# ── Session endpoints ─────────────────────────────────────────────────────────

class TestSessionEndpoints:
    def _start(self, client, user_id="user-1", language_id="lang1"):
        return client.post("/session/start", json={
            "user_id": user_id, "language_id": language_id
        })

    def test_start_session_returns_card(self, client, api):
        resp = self._start(client)
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["card"] is not None
        assert data["card"]["meta"]["word_number"] == 1

    def test_start_session_no_words_returns_400(self, client, api):
        api.get_study_words.return_value = {"success": True, "result": []}
        resp = self._start(client)
        assert resp.status_code == 400

    def test_know_word_sets_score_changed(self, client, api):
        resp = self._start(client)
        session_id = resp.json()["session_id"]
        know_resp = client.post(f"/session/{session_id}/know")
        assert know_resp.status_code == 200
        card = know_resp.json()["card"]
        assert card["show_answer"] is True
        button_ids = [b["id"] for b in card["buttons"]]
        assert "rate" in button_ids
        assert "reconsider" in button_ids

    def test_show_answer_marks_incorrect(self, client, api):
        api.create_user_word_data.return_value = {
            "success": True,
            "result": {"score": 0, "check_interval": 0, "next_check_date": "2026-06-01", "is_skipped": False},
        }
        resp = self._start(client)
        session_id = resp.json()["session_id"]
        sa_resp = client.post(f"/session/{session_id}/show_answer")
        assert sa_resp.status_code == 200
        card = sa_resp.json()["card"]
        assert card["show_answer"] is True
        assert card["meta"]["incorrect_count"] == 1

    def test_rate_word_advances_index(self, client, api):
        resp = self._start(client)
        session_id = resp.json()["session_id"]
        client.post(f"/session/{session_id}/know")
        rate_resp = client.post(f"/session/{session_id}/rate", json={"rating": "know"})
        assert rate_resp.status_code == 200
        card = rate_resp.json()["card"]
        assert card["meta"]["word_number"] == 2

    def test_batch_exhausted_when_all_rated(self, client, api):
        api.get_study_words.return_value = {"success": True, "result": [_make_word(1)]}
        resp = self._start(client)
        session_id = resp.json()["session_id"]
        client.post(f"/session/{session_id}/know")
        rate_resp = client.post(f"/session/{session_id}/rate", json={"rating": "know"})
        assert rate_resp.json().get("batch_exhausted") is True

    def test_reconsider_flips_score(self, client, api):
        resp = self._start(client)
        session_id = resp.json()["session_id"]
        client.post(f"/session/{session_id}/know")
        recon_resp = client.post(f"/session/{session_id}/reconsider")
        assert recon_resp.status_code == 200
        card = recon_resp.json()["card"]
        assert card["meta"]["correct_count"] == 0
        assert card["meta"]["incorrect_count"] == 1

    # ── остальные маршруты роутера сессии ────────────────────────────────────
    # Их не дёргали по HTTP, поэтому коллизия /session/{sid}/progress с
    # /session/{uid}/{lid} прожила незамеченной: сервис тестировался напрямую,
    # минуя роутинг. Ниже — вызовы именно через HTTP.

    def test_progress_endpoint_answers_by_session_id(self, client, api):
        resp = self._start(client)
        session_id = resp.json()["session_id"]
        prog = client.get(f"/session/{session_id}/progress")
        assert prog.status_code == 200
        body = prog.json()
        # session_id в ответе доказывает, что отработал обработчик прогресса,
        # а не маршрут /{user_id}/{language_id}, который вернул бы карточку.
        assert body["session_id"] == session_id
        assert body["batch_size"] == 3
        assert body["total_words_processed"] == 0

    def test_progress_endpoint_404_for_unknown_session(self, client, api):
        resp = client.get("/session/no-such-session/progress")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Session not found"

    def test_next_batch_returns_new_card(self, client, api):
        session_id = self._start(client).json()["session_id"]
        resp = client.post(f"/session/{session_id}/next_batch")
        assert resp.status_code == 200
        body = resp.json()
        assert body["loaded"] is True
        assert body["card"] is not None

    def test_next_batch_reports_when_nothing_loaded(self, client, api):
        session_id = self._start(client).json()["session_id"]
        api.get_study_words.return_value = {"success": False, "result": None}
        resp = client.post(f"/session/{session_id}/next_batch")
        assert resp.status_code == 200
        assert resp.json() == {"loaded": False, "session_id": session_id, "card": None}

    def test_toggle_skip_marks_current_word(self, client, api):
        session_id = self._start(client).json()["session_id"]
        resp = client.post(f"/session/{session_id}/toggle_skip")
        assert resp.status_code == 200
        assert resp.json()["card"]["meta"]["is_skipped"] is True
        payload = api.create_user_word_data.call_args[0][1]
        assert payload["is_skipped"] is True

    def test_toggle_skip_404_for_unknown_session(self, client, api):
        resp = client.post("/session/no-such-session/toggle_skip")
        assert resp.status_code == 404

    def test_add_forbidden_pair_saves_and_shows_the_pair(self, client, api):
        session_id = self._start(client).json()["session_id"]
        client.post(f"/session/{session_id}/show_answer")
        resp = client.post(f"/session/{session_id}/add_forbidden_pair",
                           json={"bad_word_id": "word-2"})
        assert resp.status_code == 200
        # записи user_word_data ещё нет, поэтому список уходит в create
        saved = api.create_user_word_data.call_args[0][1]
        assert saved["forbidden_quiz_pairs"] == ["word-2"]
        groups = [e for e in resp.json()["card"]["extra_content"]
                  if e["type"] == "forbidden_quiz_pairs"]
        assert groups and groups[0]["word_ids"] == ["word-2"]

    def test_clear_forbidden_pairs_empties_the_list(self, client, api):
        session_id = self._start(client).json()["session_id"]
        client.post(f"/session/{session_id}/show_answer")
        client.post(f"/session/{session_id}/add_forbidden_pair",
                    json={"bad_word_id": "word-2"})
        resp = client.post(f"/session/{session_id}/clear_forbidden_pairs")
        assert resp.status_code == 200
        saved = api.create_user_word_data.call_args[0][1]
        assert saved["forbidden_quiz_pairs"] == []
        assert not [e for e in resp.json()["card"]["extra_content"]
                    if e["type"] == "forbidden_quiz_pairs"]

    def test_forbidden_pair_routes_404_for_unknown_session(self, client, api):
        assert client.post("/session/nope/add_forbidden_pair",
                           json={"bad_word_id": "word-2"}).status_code == 404
        assert client.post("/session/nope/clear_forbidden_pairs").status_code == 404


# ── Auth endpoints ────────────────────────────────────────────────────────────

class TestAuthEndpoints:
    def test_lookup_telegram_found(self, client, api):
        resp = client.post("/auth/lookup", json={"mode": "telegram", "telegram_id": 123})
        assert resp.status_code == 200
        assert resp.json()["found"] is True

    def test_lookup_telegram_not_found(self, client, api):
        api.get_user_by_telegram_id.return_value = {"success": True, "result": []}
        resp = client.post("/auth/lookup", json={"mode": "telegram", "telegram_id": 999})
        assert resp.status_code == 200
        assert resp.json()["found"] is False

    def test_lookup_name_found(self, client, api):
        resp = client.post("/auth/lookup", json={"mode": "name", "name": "Test"})
        assert resp.status_code == 200
        assert resp.json()["found"] is True

    def test_lookup_name_not_found(self, client, api):
        api.get_users.return_value = {"success": True, "result": []}
        resp = client.post("/auth/lookup", json={"mode": "name", "name": "NoOne"})
        assert resp.status_code == 200
        assert resp.json()["found"] is False

    def test_confirm_deny_token_flow(self, client, api):
        lookup = client.post("/auth/lookup", json={"mode": "telegram", "telegram_id": 123})
        token = lookup.json()["token"]

        status = client.get(f"/auth/status/{token}")
        assert status.json()["status"] == "pending"

        confirm = client.post(f"/auth/confirm/{token}")
        assert confirm.json()["ok"] is True

        status2 = client.get(f"/auth/status/{token}")
        assert status2.json()["status"] == "confirmed"
        assert status2.json()["user_id"] == "user-1"

    def test_deny_token(self, client, api):
        lookup = client.post("/auth/lookup", json={"mode": "telegram", "telegram_id": 123})
        token = lookup.json()["token"]

        client.post(f"/auth/deny/{token}")
        status = client.get(f"/auth/status/{token}")
        assert status.json()["status"] == "denied"

    def test_status_not_found(self, client):
        resp = client.get("/auth/status/nonexistent-token")
        assert resp.json()["status"] == "not_found"


# ── Finish stats trigger ──────────────────────────────────────────────────────

class TestFinishStatsTrigger:
    """
    «Первый финиш за день» пишется по одному событию — когда пройдена порция
    слов на сегодня, и ровно один раз в сутки.

    Величина отвечает на вопрос «сколько слов я не знаю, дойдя до конца дневной
    порции». Набор слов каждый день почти новый, поэтому число сравнимо изо дня
    в день.

    С 10 июня по 16 сентября 2026 договор был другим: запись шла на КАЖДОЕ
    «не знаю», значением был счётчик ошибок сессии. Тот счётчик считал ответы, а
    не слова, и жил внутри сессии, а сессия за день начинается заново много раз —
    график показывал максимум ошибок одной сессии. Тесты ниже закрепляют именно
    то, что отличает новый договор от старого, поэтому проверяют и обратное:
    «не знаю» само по себе не пишет ничего.
    """

    def _start(self, client):
        resp = client.post("/session/start", json={"user_id": "u1", "language_id": "lang1"})
        assert resp.status_code == 200
        return resp.json()["session_id"]

    def _progress(self, api, words_unknown_now):
        """Состояние базы: столько разных слов сейчас в статусе «не знаю»."""
        api.get_user_progress.return_value = {
            "success": True,
            "result": {"words_studied": 100, "words_known": 93, "words_skipped": 0,
                       "words_unknown_now": words_unknown_now, "words_overdue": 0},
        }

    def _written(self, api):
        """Значение words_unknown из единственного вызова записи финиша."""
        api.update_daily_first_finish_statistics.assert_called_once()
        call = api.update_daily_first_finish_statistics.call_args
        payload = call.args[3] if len(call.args) > 3 else call.kwargs.get("stats_update", {})
        return payload.get("words_unknown")

    def _exhaust(self, client, sid, rating="dont_know", words=3):
        """Пройти порцию до конца; последний ответ обязан вернуть batch_exhausted."""
        last = None
        for _ in range(words):
            last = client.post(f"/session/{sid}/rate", json={"rating": rating})
            assert last.status_code == 200
        assert last.json().get("batch_exhausted") is True
        return last

    def test_dont_know_mid_batch_writes_nothing(self, client, api):
        """Одно «не знаю» посреди порции — не финиш, писать нечего."""
        sid = self._start(client)
        resp = client.post(f"/session/{sid}/rate", json={"rating": "dont_know"})
        assert resp.status_code == 200
        assert resp.json().get("batch_exhausted") is not True
        api.update_daily_first_finish_statistics.assert_not_called()

    def test_reconsider_mid_batch_writes_nothing(self, client, api):
        """«Передумал» — тоже обычный ответ, а не конец порции."""
        sid = self._start(client)
        client.post(f"/session/{sid}/know")
        resp = client.post(f"/session/{sid}/reconsider")
        assert resp.status_code == 200
        api.update_daily_first_finish_statistics.assert_not_called()

    def test_know_and_skip_mid_batch_write_nothing(self, client, api):
        sid = self._start(client)
        client.post(f"/session/{sid}/know")
        client.post(f"/session/{sid}/rate", json={"rating": "know"})
        client.post(f"/session/{sid}/rate", json={"rating": "skip"})
        api.update_daily_first_finish_statistics.assert_not_called()

    def test_exhausted_batch_writes_finish_once(self, client, api):
        """Дошли до конца порции — одна запись за день."""
        self._progress(api, 7)
        sid = self._start(client)
        self._exhaust(client, sid)
        assert self._written(api) == 7

    def test_value_comes_from_database_not_from_session_errors(self, client, api):
        """
        Тот самый дефект: три «не знаю» подряд давали три, хотя в базе незнакомых
        слов семь. Значение обязано приходить из базы, а не из счётчика сессии.
        """
        self._progress(api, 7)
        sid = self._start(client)
        self._exhaust(client, sid, rating="dont_know")
        assert self._written(api) == 7

    def test_batch_finished_without_errors_still_writes(self, client, api):
        """
        Порция, пройденная без единой ошибки, — тоже финиш. Старый договор в этом
        случае не писал ничего, и день просто выпадал из графика.
        """
        self._progress(api, 0)
        sid = self._start(client)
        self._exhaust(client, sid, rating="know")
        assert self._written(api) == 0

    def test_reconsider_on_last_word_writes_finish(self, client, api):
        """Порция может кончиться и на «передумал» — это тот же финиш."""
        self._progress(api, 4)
        sid = self._start(client)
        client.post(f"/session/{sid}/rate", json={"rating": "know"})
        client.post(f"/session/{sid}/rate", json={"rating": "know"})
        client.post(f"/session/{sid}/know")
        resp = client.post(f"/session/{sid}/reconsider")
        assert resp.json().get("batch_exhausted") is True
        assert self._written(api) == 4

    def test_second_finish_of_the_day_writes_nothing(self, client, api):
        """
        За день порция кончается много раз. Записывается ПЕРВЫЙ финиш — значит
        при уже существующей записи за сегодня новая не пишется.
        """
        self._progress(api, 5)
        api.get_daily_first_finish_statistics.return_value = {
            "success": True, "status": 200, "result": {"words_unknown": 9},
        }
        sid = self._start(client)
        self._exhaust(client, sid)
        api.update_daily_first_finish_statistics.assert_not_called()


class TestDailyUpdateEndpoint:
    """
    POST .../daily отвечал {"ok": true} не глядя на результат записи. Неудачная
    запись выглядела как успешная — на этом при проверке выкладки 4.4.0 молча
    не записалось ничего, а ответ был «ок».
    """

    def _url(self):
        return "/statistics/u1/lang1/daily?action_date=2020-01-05"

    def test_success_reports_ok(self, client, api):
        api.get_daily_statistics.return_value = {"success": True, "status": 404, "result": None}
        api.update_daily_statistics.return_value = {"success": True, "result": {}}
        resp = client.post(self._url())
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_failed_write_is_not_reported_as_success(self, client, api):
        api.get_daily_statistics.return_value = {"success": True, "status": 404, "result": None}
        api.update_daily_statistics.return_value = {"success": False, "error": "boom"}
        resp = client.post(self._url())
        assert resp.status_code == 502
        assert resp.json().get("ok") is not True


class TestSettingsReachTheRunningSession:
    """
    Сессия держит снимок настроек, сделанный при старте, а клиент, возвращаясь
    на экран учёбы, сначала просит существующую сессию. Из-за этого переключатель
    не действовал до конца порции: человек выключал «учитывать дату», получал
    слова подряд с первого, возвращал настройку обратно — и продолжал получать
    их подряд. В журнале это видно как сессия на 100 слов, начатая ДО того, как
    настройку вернули.
    """

    def _start(self, client, user):
        resp = client.post("/session/start", json={"user_id": user, "language_id": "lang1"})
        assert resp.status_code == 200
        return resp.json()["session_id"]

    def test_display_setting_reaches_the_session_without_dropping_it(self, client, api):
        """Показ меняется на лету: список слов от него не зависит, терять его незачем."""
        from app.services import session_service
        user = "u-display"
        session_service.end_session(user, "lang1")
        api.get_user_language_settings.return_value = {
            "success": True, "result": {"show_tags": True, "use_check_date": True}}
        self._start(client, user)
        assert session_service.get_session(user, "lang1")["settings"]["show_tags"] is True

        resp = client.post(f"/settings/{user}/lang1/show_tags/toggle")
        assert resp.status_code == 200
        session = session_service.get_session(user, "lang1")
        assert session is not None, "настройка показа не должна ронять сессию"
        assert session["settings"]["show_tags"] is False

    def test_selection_setting_drops_the_session(self, client, api):
        """
        «Учитывать дату» меняет СОСТАВ порции, а она уже набрана. Обновить снимок
        мало — сессию надо завершить, чтобы следующий заход набрал слова заново.
        """
        from app.services import session_service
        user = "u-selection"
        session_service.end_session(user, "lang1")
        api.get_user_language_settings.return_value = {
            "success": True, "result": {"use_check_date": False}}
        self._start(client, user)
        assert session_service.get_session(user, "lang1") is not None

        resp = client.post(f"/settings/{user}/lang1/use_check_date/toggle")
        assert resp.status_code == 200
        assert session_service.get_session(user, "lang1") is None

    def test_every_selection_setting_drops_the_session(self, client, api):
        """Все три настройки отбора — ровно параметры загрузки слов."""
        from app.services import session_service
        for key in sorted(session_service.SELECTION_SETTINGS):
            user = f"u-sel-{key}"
            session_service.end_session(user, "lang1")
            api.get_user_language_settings.return_value = {
                "success": True, "result": {"start_word": 1, "skip_marked": False,
                                            "use_check_date": True}}
            self._start(client, user)
            assert session_service.get_session(user, "lang1") is not None
            value = 7 if key == "start_word" else True
            resp = client.put(f"/settings/{user}/lang1/{key}", json={"value": value})
            assert resp.status_code == 200
            assert session_service.get_session(user, "lang1") is None, key

    def test_change_without_a_session_is_harmless(self, client, api):
        """Настройки меняют и не начав учиться — падать тут нечему."""
        from app.services import session_service
        user = "u-nosession"
        session_service.end_session(user, "lang1")
        resp = client.post(f"/settings/{user}/lang1/use_check_date/toggle")
        assert resp.status_code == 200


# ── Pick answer endpoint ──────────────────────────────────────────────────────

class TestPickAnswerEndpoint:
    """
    Android uses last_wrong_distractor_id from pick_answer response to show a
    result banner: null = correct answer, non-null = wrong answer.
    These tests verify the BLS sets that field correctly for all answer types,
    which is the contract the Android banner logic relies on.
    """

    def _start_with_quiz(self, client):
        """Start a session and inject quiz options directly into session state."""
        resp = client.post("/session/start", json={"user_id": "u1", "language_id": "lang1"})
        assert resp.status_code == 200
        sid = resp.json()["session_id"]
        from app.services import session_service
        session = session_service.get_session_by_id(sid)
        session["pick_mode_active"] = True
        session["quiz_options"] = {
            "options": [
                {"word_id": "word-1", "is_correct": True,  "target_text": "слово1"},
                {"word_id": "word-2", "is_correct": False, "target_text": "слово2"},
                {"word_id": "word-3", "is_correct": False, "target_text": "слово3"},
            ]
        }
        return sid

    def test_correct_answer_returns_200(self, client, api):
        sid = self._start_with_quiz(client)
        resp = client.post(f"/session/{sid}/pick_answer", json={"selected_word_id": "word-1"})
        assert resp.status_code == 200

    def test_correct_answer_sets_last_wrong_distractor_to_null(self, client, api):
        """Correct pick: last_wrong_distractor_id is null → Android shows green banner."""
        sid = self._start_with_quiz(client)
        resp = client.post(f"/session/{sid}/pick_answer", json={"selected_word_id": "word-1"})
        card = resp.json()["card"]
        assert card["last_wrong_distractor_id"] is None

    def test_wrong_answer_sets_last_wrong_distractor_id(self, client, api):
        """Wrong pick: last_wrong_distractor_id equals the selected word_id → Android shows red banner."""
        sid = self._start_with_quiz(client)
        resp = client.post(f"/session/{sid}/pick_answer", json={"selected_word_id": "word-2"})
        card = resp.json()["card"]
        assert card["last_wrong_distractor_id"] == "word-2"

    def test_dont_know_sets_last_wrong_distractor_to_null(self, client, api):
        """dont_know: distractor id is null (Android uses selectedWordId == 'dont_know' to show red banner)."""
        sid = self._start_with_quiz(client)
        resp = client.post(f"/session/{sid}/pick_answer", json={"selected_word_id": "dont_know"})
        assert resp.status_code == 200
        card = resp.json()["card"]
        assert card["last_wrong_distractor_id"] is None

    def test_pick_answer_reveals_word(self, client, api):
        """After any pick answer the word is revealed (show_answer = true)."""
        sid = self._start_with_quiz(client)
        resp = client.post(f"/session/{sid}/pick_answer", json={"selected_word_id": "word-1"})
        assert resp.json()["card"]["show_answer"] is True

    def test_second_wrong_distractor_is_tracked_independently(self, client, api):
        """Wrong pick with word-3 records word-3, not word-2."""
        sid = self._start_with_quiz(client)
        resp = client.post(f"/session/{sid}/pick_answer", json={"selected_word_id": "word-3"})
        assert resp.json()["card"]["last_wrong_distractor_id"] == "word-3"


# ── Set setting endpoint ──────────────────────────────────────────────────────

class TestSetSettingEndpoint:
    """
    Android saveNumericSetting calls PUT /settings/{user}/{lang}/{key} with {"value": N}.
    Tests verify the endpoint returns 200 (so resp.isSuccessful is true in Android)
    and reflects the new value in the response body (so loadSettings() shows
    the correct value after the save).
    """

    @pytest.fixture(autouse=True)
    def setup_settings_mock(self, api):
        api.get_user_language_settings.return_value = {
            "success": True,
            "result": {
                "quiz_options_count": 3,
                "start_word": 1,
                "skip_marked": True,
                "use_check_date": True,
            },
        }
        api.update_user_language_settings.return_value = {"success": True, "result": {}}

    def test_set_numeric_setting_returns_200(self, client):
        resp = client.put(
            "/settings/user-1/lang-1/quiz_options_count",
            json={"value": 5},
        )
        assert resp.status_code == 200

    def test_set_numeric_setting_updates_value_in_response(self, client):
        """Response includes the new value so Android loadSettings() shows it immediately."""
        resp = client.put(
            "/settings/user-1/lang-1/quiz_options_count",
            json={"value": 5},
        )
        assert resp.json()["quiz_options_count"] == 5

    def test_set_numeric_setting_calls_backend_save(self, client, api):
        """update_user_language_settings must be called with the updated value."""
        client.put(
            "/settings/user-1/lang-1/quiz_options_count",
            json={"value": 5},
        )
        api.update_user_language_settings.assert_called_once()
        _, _, saved = api.update_user_language_settings.call_args[0]
        assert saved["quiz_options_count"] == 5

    def test_set_different_numeric_key(self, client):
        """The same endpoint handles any numeric key (start_word, max_check_interval, etc.)."""
        resp = client.put(
            "/settings/user-1/lang-1/start_word",
            json={"value": 100},
        )
        assert resp.status_code == 200
        assert resp.json()["start_word"] == 100


# ── Offline endpoints (bundle + batch results) ──────────────────────────────────

class TestOfflineEndpoints:
    def test_bundle_endpoint_pre_renders_and_labels_buttons(self, client, api):
        resp = client.post("/session/user-1/lang1/bundle")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["words"]) >= 1
        w = data["words"][0]
        assert w["card_front"]["show_answer"] is False
        assert w["card_answer"]["show_answer"] is True
        assert "sounds" in w
        effects = {b["id"]: b.get("offline_effect") for b in w["card_front"]["buttons"]}
        assert effects.get("know") == "record_and_reveal"
        assert effects.get("show_answer") == "reveal_answer"
        # Ответная сторона: rate после know только листает, не записывая повторно.
        after = {b["id"]: b.get("offline_effect") for b in w["card_answer"]["buttons"]}
        assert after.get("rate") in ("advance", "submit")

    def test_results_batch_endpoint_validates_and_applies(self, client, api):
        from app.services import session_service
        session_service._processed_event_ids.clear()
        resp = client.post("/results/batch", json={
            "user_id": "user-1", "language_id": "lang1",
            "events": [
                {"event_id": "r1", "word_id": "", "rating": "know", "ts": "001"},
                {"event_id": "r2", "word_id": "word-1", "rating": "know", "ts": "002"},
                {"event_id": "r3", "word_id": "word-2", "rating": "skip", "ts": "003"},
            ],
        })
        assert resp.status_code == 200
        acks = {a["event_id"]: a["status"] for a in resp.json()["acks"]}
        assert acks["r1"] == "invalid"
        assert acks["r2"] == "ok"
        assert acks["r3"] == "ok"

    def test_results_batch_endpoint_is_idempotent(self, client, api):
        from app.services import session_service
        session_service._processed_event_ids.clear()
        body = {
            "user_id": "user-1", "language_id": "lang1",
            "events": [{"event_id": "dup-1", "word_id": "word-1", "rating": "know", "ts": "001"}],
        }
        first = client.post("/results/batch", json=body)
        second = client.post("/results/batch", json=body)
        assert first.json()["acks"][0]["status"] == "ok"
        assert second.json()["acks"][0]["status"] == "duplicate"
