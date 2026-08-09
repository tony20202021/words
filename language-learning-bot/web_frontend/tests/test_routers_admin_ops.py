"""
Разрушительные и «тяжёлые» админские операции: экспорт, импорт, рассылка.

Ровно эти ручки не дёргал ни один тест, хотя цена ошибки тут наибольшая: импорт
умеет стереть все слова языка, рассылка уходит всем пользователям в Telegram, а
форма экспорта, как выяснилось, не работала вовсе — она шлёт `format`, `start` и
`end`, а ручка читала `fmt` и падала на пустых числах с 422.
"""

import pytest
from unittest.mock import AsyncMock

from tests.test_routers_admin import ADMIN_SESSION, USER_SESSION, _get, _post, _make_bls


# ── Экспорт: ровно то, что шлёт форма language_detail.html ───────────────────

def test_export_works_with_the_parameters_the_form_sends():
    """
    <select name="format"> и два пустых <input type="number"> — то есть
    ?format=csv&start=&end=. Пустые числа роняли запрос в 422, а имя `format`
    игнорировалось, и вместо CSV всегда скачивался xlsx.
    """
    bls = _make_bls()
    r, _ = _get(ADMIN_SESSION, "/admin/languages/lang1/export?format=csv&start=&end=", bls=bls)

    assert r.status_code == 200, r.text[:300]
    assert r.content == b"BINARY"
    assert r.headers["content-type"].startswith("text/csv")
    bls.admin_export_words.assert_awaited_once_with("admin-1", "lang1", "csv", None, None)


def test_export_passes_the_range_when_the_form_fills_it():
    bls = _make_bls()
    _get(ADMIN_SESSION, "/admin/languages/lang1/export?format=json&start=10&end=20", bls=bls)
    bls.admin_export_words.assert_awaited_once_with("admin-1", "lang1", "json", 10, 20)


def test_export_still_accepts_the_old_fmt_name():
    """Ссылки с ?fmt=… ломать не за что — обе формы имени должны работать."""
    bls = _make_bls()
    r, _ = _get(ADMIN_SESSION, "/admin/languages/lang1/export?fmt=json", bls=bls)
    assert r.status_code == 200
    bls.admin_export_words.assert_awaited_once_with("admin-1", "lang1", "json", None, None)


def test_export_failure_shows_a_message_not_a_blank_500():
    """Страница языка начинается с lang.name_ru: без него падал сам текст ошибки."""
    bls = _make_bls()
    bls.admin_export_words = AsyncMock(return_value=None)
    r, _ = _get(ADMIN_SESSION, "/admin/languages/lang1/export?format=xlsx&start=&end=", bls=bls)

    assert r.status_code == 200, r.text[:300]
    assert "Экспорт не удался" in r.text
    assert "Китайский" in r.text, "должна остаться нормальная страница языка"


def test_export_requires_admin():
    r, _ = _get(USER_SESSION, "/admin/languages/lang1/export?format=csv",
                follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/languages"


# ── Импорт: сюда приезжает файл и флаг «очистить существующие» ───────────────

def test_import_forwards_file_and_does_not_clear_by_default():
    payload = "foreign,translation\n你好,привет\n".encode("utf-8")
    bls = _make_bls()
    r, _ = _post(ADMIN_SESSION, "/admin/languages/lang1/import", bls=bls,
                 files={"file": ("words.csv", payload, "text/csv")})

    assert r.status_code == 200
    assert "Импорт выполнен успешно" in r.text
    args = bls.admin_import_words.await_args.args
    assert args[0] == "admin-1" and args[1] == "lang1"
    assert args[2] == payload
    assert args[3] == "words.csv"
    assert args[4] is False, "без галочки существующие слова стирать нельзя"


def test_import_clear_existing_is_passed_through_only_when_checked():
    bls = _make_bls()
    _post(ADMIN_SESSION, "/admin/languages/lang1/import", bls=bls,
          files={"file": ("words.csv", b"x", "text/csv")},
          data={"clear_existing": "true"})
    assert bls.admin_import_words.await_args.args[4] is True


def test_import_failure_is_reported_to_the_admin():
    bls = _make_bls()
    bls.admin_import_words = AsyncMock(return_value={"ok": False, "error": "плохой файл"})
    r, _ = _post(ADMIN_SESSION, "/admin/languages/lang1/import", bls=bls,
                 files={"file": ("words.csv", b"x", "text/csv")})
    assert r.status_code == 200
    assert "Ошибка импорта: плохой файл" in r.text


def test_import_requires_admin():
    r, bls = _post(USER_SESSION, "/admin/languages/lang1/import",
                   files={"file": ("words.csv", b"x", "text/csv")},
                   follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/languages"
    bls.admin_import_words.assert_not_awaited()


# ── Рассылка: уходит всем в Telegram ─────────────────────────────────────────

class _FakeTelegram:
    """Подменяет httpx.AsyncClient на время теста и записывает, кому ушло."""

    def __init__(self):
        self.chat_ids = []
        self.texts = []

    def __call__(self, *a, **kw):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, **kw):
        self.chat_ids.append(json["chat_id"])
        self.texts.append(json["text"])

        class _R:
            @staticmethod
            def json():
                return {"ok": True}

        return _R()


@pytest.fixture
def telegram(monkeypatch):
    import httpx
    fake = _FakeTelegram()
    monkeypatch.setattr(httpx, "AsyncClient", fake)
    monkeypatch.setenv("BOT_TOKEN", "test-token")
    return fake


def _bls_with_users():
    bls = _make_bls()
    bls.admin_list_users = AsyncMock(return_value={
        "users": [
            {"id": "admin-1", "first_name": "Admin", "telegram_id": 1, "is_admin": True},
            {"id": "u1", "first_name": "Alice", "telegram_id": 111, "is_admin": False},
            {"id": "u2", "first_name": "Bob", "telegram_id": None, "is_admin": False},
        ],
        "page": 1, "per_page": 20, "total": 3, "total_pages": 1,
    })
    return bls


def test_broadcast_skips_the_sender_and_users_without_telegram(telegram):
    bls = _bls_with_users()
    r, _ = _post(ADMIN_SESSION, "/admin/broadcast/send", bls=bls, data={"text": "привет всем"})

    assert r.status_code == 200
    assert telegram.chat_ids == [111], "себе и пользователю без telegram_id слать нечего"
    assert telegram.texts == ["привет всем"]
    assert "Отправлено:" in r.text and ">1<" in r.text


def test_broadcast_without_bot_token_sends_nothing(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    bls = _bls_with_users()
    r, _ = _post(ADMIN_SESSION, "/admin/broadcast/send", bls=bls, data={"text": "привет"})
    assert r.status_code == 200
    assert "Отправлено:" in r.text and ">0<" in r.text


def test_broadcast_requires_admin(telegram):
    bls = _bls_with_users()
    r, _ = _post(USER_SESSION, "/admin/broadcast/send", bls=bls,
                 data={"text": "привет"}, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/languages"
    assert telegram.chat_ids == []


# ── Диагностика ──────────────────────────────────────────────────────────────

def test_diagnostics_requires_admin():
    """Страница показывает список процессов хоста — не для обычного пользователя."""
    r, _ = _get(USER_SESSION, "/admin/diagnostics", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/languages"


def test_diagnostics_without_session_goes_to_login():
    r, _ = _get({}, "/admin/diagnostics", follow_redirects=False)
    assert r.status_code == 302
    assert "/login" in r.headers["location"]
