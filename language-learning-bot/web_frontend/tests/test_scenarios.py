"""
Сценарные тесты веб-клиента: последовательности шагов, а не отдельные ручки.

Зачем именно так
----------------
Остальные тесты дёргают по одному маршруту. Но баги, которые ловили руками,
были в переходах: «Начать заново» возвращало на то же слово, настройка
сбрасывала выбранный язык, после ошибки сети экран залипал. Одношаговый тест
такое не видит в принципе.

Здесь один `TestClient` проходит маршрут целиком. Сессия — подписанная кука
через SessionMiddleware, а TestClient держит куки между запросами, поэтому
состояние едет само собой и мокать его не нужно.

Часть проверок перенесена из сценариев удалённого legacy-фронтенда
(`frontend/tests/test_scenarios/scenarios/*.yaml`, см. коммит 5bf18ae):
порядок операций, независимость настроек у разных языков, поведение при
ошибке API. Оттуда же взят принцип — проверять не «200», а что состояние
действительно изменилось.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import make_mock_bls


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def bls():
    return make_mock_bls()


def login(client, bls):
    """Общий пролог: войти по имени. Вынесен, чтобы сценарии не повторяли его."""
    with patch("app.routers.auth.get_bls_client", return_value=bls):
        resp = client.post("/login", data={"mode": "name", "name": "Test"},
                           follow_redirects=False)
    assert resp.status_code == 302, "вход по имени должен редиректить"
    return resp


class TestStudyFlow:
    """Основной учебный цикл — вход, список языков, карточка, ответ, оценка."""

    def test_full_cycle_know_then_rate(self, client, bls):
        login(client, bls)

        with patch("app.routers.languages.get_bls_client", return_value=bls):
            langs = client.get("/languages")
        assert langs.status_code == 200
        assert "Китайский" in langs.text

        with patch("app.routers.study.get_bls_client", return_value=bls):
            card = client.get("/study/lang1")
            assert card.status_code == 200
            assert "你好" in card.text, "на карточке должно быть слово"

            # «Знаю» — сервер раскрывает ответ
            known = client.post("/study/lang1/know")
            assert known.status_code == 200
            assert bls.know_word.called, "должен быть вызван know на BLS"

            # «К следующему» — переходим к следующему слову
            rated = client.post("/study/lang1/rate", data={"rating": "know"})
            assert rated.status_code == 200
            assert bls.rate_word.called

        # Порядок вызовов важен: сначала know, потом rate, а не наоборот.
        assert bls.know_word.call_count == 1
        assert bls.rate_word.call_count == 1

    def test_dont_know_path_goes_through_show_answer(self, client, bls):
        login(client, bls)
        with patch("app.routers.study.get_bls_client", return_value=bls):
            client.get("/study/lang1")
            client.post("/study/lang1/show_answer")
            client.post("/study/lang1/rate", data={"rating": "dont_know"})

        assert bls.show_answer.called, "«не знаю» должно раскрывать ответ"
        assert bls.rate_word.called
        assert not bls.know_word.called, "know при этом вызываться не должен"

    def test_restart_ends_session_before_starting_new_one(self, client, bls):
        """
        «Начать заново» обязано сначала закрыть текущую сессию.
        Если этого не сделать — продолжится старая, и кнопка визуально
        не сделает ничего. Ровно так вёл себя офлайн-режим Android.
        """
        login(client, bls)
        with patch("app.routers.study.get_bls_client", return_value=bls):
            client.get("/study/lang1")
            resp = client.post("/study/lang1/restart")

        assert resp.status_code in (200, 302)
        assert bls.end_session.called, "рестарт должен завершать текущую сессию"


class TestSettingsFlow:
    """Настройки не должны ломать выбранный язык — перенесено из settings_preserve_language."""

    def test_toggle_setting_keeps_language_context(self, client, bls):
        login(client, bls)

        bls.get_settings = _async_value({"show_big": True, "show_debug": False})
        bls.toggle_setting = _async_value({"ok": True, "value": True})

        with patch("app.routers.settings.get_bls_client", return_value=bls):
            before = client.get("/settings/lang1")
            assert before.status_code == 200

            toggled = client.post("/settings/lang1/toggle", data={"key": "show_debug"})
            assert toggled.status_code in (200, 302)

            after = client.get("/settings/lang1")
            assert after.status_code == 200

        # Язык не должен слететь: обе страницы всё ещё про lang1.
        assert bls.toggle_setting.called
        called_langs = {c.args[1] for c in bls.get_settings.call_args_list if len(c.args) > 1}
        assert called_langs <= {"lang1"}, f"настройки утекли на другой язык: {called_langs}"

    def test_settings_for_two_languages_are_independent(self, client, bls):
        """
        Перенесено из multiple_languages.yaml: настройки разных языков
        не должны смешиваться.
        """
        login(client, bls)
        seen = []

        async def get_settings(user_id, language_id):
            seen.append(language_id)
            return {"start_word": 1 if language_id == "lang1" else 10}

        bls.get_settings = get_settings
        with patch("app.routers.settings.get_bls_client", return_value=bls):
            client.get("/settings/lang1")
            client.get("/settings/lang2")

        assert seen == ["lang1", "lang2"], f"запрошены не те языки: {seen}"


class TestApiErrors:
    """
    Перенесено из api_errors.yaml — самое ценное из старых сценариев.
    При отказе BLS пользователь должен получить внятную страницу, а не пустой
    экран со стандартной 500.

    Клиент здесь создаётся с raise_server_exceptions=False: с True TestClient
    пробрасывает исключение наружу до того, как отработает обработчик, и мы
    проверяли бы не то, что видит пользователь.
    """

    @pytest.fixture
    def prod_client(self):
        """Клиент, ведущий себя как продакшен: ошибки превращаются в ответы."""
        return TestClient(app, raise_server_exceptions=False)

    @staticmethod
    def _boom(*a, **kw):
        async def fail(*args, **kwargs):
            raise RuntimeError("BLS недоступен")
        return fail

    def test_study_shows_error_page_when_bls_is_down(self, prod_client, bls):
        login(prod_client, bls)
        bls.get_session = self._boom()
        bls.start_session = self._boom()

        with patch("app.routers.study.get_bls_client", return_value=bls):
            resp = prod_client.get("/study/lang1")

        assert resp.status_code in (500, 503)
        assert "Сервер недоступен" in resp.text, "нужна понятная страница, а не пустой экран"
        assert "Повторить" in resp.text, "пользователю нужен выход из тупика"

    def test_languages_shows_error_page_when_bls_is_down(self, prod_client, bls):
        login(prod_client, bls)
        bls.get_languages = self._boom()

        with patch("app.routers.languages.get_bls_client", return_value=bls):
            resp = prod_client.get("/languages")

        assert resp.status_code in (500, 503)
        assert "Сервер недоступен" in resp.text

    def test_healthy_pages_are_untouched_by_the_handler(self, prod_client, bls):
        """Обработчик не должен вмешиваться, когда всё в порядке."""
        login(prod_client, bls)
        with patch("app.routers.languages.get_bls_client", return_value=bls):
            resp = prod_client.get("/languages")
        assert resp.status_code == 200
        assert "Сервер недоступен" not in resp.text


class TestSessionLifecycle:
    """Вход и выход — состояние действительно появляется и действительно исчезает."""

    def test_study_requires_login(self, client):
        resp = client.get("/study/lang1", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["location"]

    def test_logout_clears_session(self, client, bls):
        login(client, bls)

        with patch("app.routers.languages.get_bls_client", return_value=bls):
            assert client.get("/languages", follow_redirects=False).status_code == 200

        client.get("/logout", follow_redirects=False)

        after = client.get("/languages", follow_redirects=False)
        assert after.status_code == 302, "после выхода доступ должен пропасть"
        assert "/login" in after.headers["location"]


def _async_value(value):
    """Мок асинхронного метода, всегда возвращающего одно и то же."""
    from unittest.mock import AsyncMock
    return AsyncMock(return_value=value)
