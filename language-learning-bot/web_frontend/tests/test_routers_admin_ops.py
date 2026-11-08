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


# ── рассылка: кому и с чьего согласия ────────────────────────────────────────

def _bls_for_consent(согласие):
    """
    согласие: {(user_id, language_id): bool} — «Получать сообщения».

    Языков два, чтобы было видно разницу между «про язык» и «независимо».
    Получателей тоже два: с одним проверка «письмо одному» проходила бы и на
    прежнем коде, где рассылка шла всем, — отличить «всем» от «одному» было
    бы не на чем.
    """
    bls = _bls_with_users()
    bls.admin_list_users = AsyncMock(return_value={
        "users": [
            {"id": "admin-1", "first_name": "Admin", "telegram_id": 1, "is_admin": True},
            {"id": "u1", "first_name": "Alice", "telegram_id": 111, "is_admin": False},
            {"id": "u3", "first_name": "Carol", "telegram_id": 333, "is_admin": False},
            {"id": "u2", "first_name": "Bob", "telegram_id": None, "is_admin": False},
        ],
        "page": 1, "per_page": 20, "total": 4, "total_pages": 1,
    })
    bls.get_languages = AsyncMock(return_value=[
        {"id": "lang1", "name_ru": "Английский", "name_foreign": "English"},
        {"id": "lang2", "name_ru": "Иврит", "name_foreign": "עברית"},
    ])

    async def settings(user_id, language_id):
        return {"receive_messages": согласие.get((user_id, language_id), True)}

    bls.get_settings = AsyncMock(side_effect=settings)
    return bls


def test_a_message_can_go_to_one_person(telegram):
    """
    Просьба владельца: «нужно сказать одному человеку про его настройку».
    Раньше рассылка умела только «всем», и ради одного письма пришлось бы
    написать всем двадцати.
    """
    bls = _bls_for_consent({})
    r, _ = _post(ADMIN_SESSION, "/admin/broadcast/send", bls=bls,
                 data={"text": "включите звук", "recipient": "u1",
                       "language_id": "any"})

    assert r.status_code == 200
    assert telegram.chat_ids == [111], "письмо ушло не только выбранному"
    assert 333 not in telegram.chat_ids, "второй получатель тоже получил письмо"
    assert telegram.texts == ["включите звук"]


def test_someone_who_switched_messages_off_is_not_written_to(telegram):
    """
    Настройка «Получать сообщения» показывается человеку и хранится по языку,
    но при отправке её НЕ ЧИТАЛИ: рассылка шла всем подряд. Настройка была
    обещанием, которого код не выполнял.
    """
    bls = _bls_for_consent({("u1", "lang1"): False})
    r, _ = _post(ADMIN_SESSION, "/admin/broadcast/send", bls=bls,
                 data={"text": "привет", "recipient": "all", "language_id": "lang1"})

    assert 111 not in telegram.chat_ids, "письмо ушло тому, кто от них отказался"
    assert "Не отправлено по их же настройке" in r.text, \
        "пропуск промолчал — «отправлено 0» выглядит поломкой"


def test_consent_is_asked_for_the_language_the_message_is_about(telegram):
    """
    Разрешение несоответствия, которое заметил владелец: настройка живёт по
    языку, а рассылка языка может и не касаться. Если язык выбран — спрашиваем
    настройку именно этого языка.
    """
    bls = _bls_for_consent({("u1", "lang1"): False, ("u1", "lang2"): True})

    r, _ = _post(ADMIN_SESSION, "/admin/broadcast/send", bls=bls,
                 data={"text": "про английский", "recipient": "all",
                       "language_id": "lang1"})
    assert 111 not in telegram.chat_ids, "выключено для этого языка, а письмо ушло"

    r, _ = _post(ADMIN_SESSION, "/admin/broadcast/send", bls=bls,
                 data={"text": "про иврит", "recipient": "all",
                       "language_id": "lang2"})
    assert 111 in telegram.chat_ids, "включено для этого языка, а письма нет"


def test_a_system_wide_message_reaches_everyone(telegram):
    """
    «Независимо от языка» значит именно независимо — решение владельца:
    «в этом режиме вообще не проверять языки, рассылать всегда, это будут
    какие-нибудь общесистемные сообщения».

    Сторож стоит на том, что настройка про ЯЗЫК не должна отвечать за
    сообщение о самой службе. Здесь человек отказался от писем по всем
    языкам до единого — и всё равно обязан получить общесистемное.
    """
    bls = _bls_for_consent({("u1", "lang1"): False, ("u1", "lang2"): False})
    r, _ = _post(ADMIN_SESSION, "/admin/broadcast/send", bls=bls,
                 data={"text": "общее", "recipient": "all", "language_id": "any"})

    assert 111 in telegram.chat_ids, \
        "общесистемное письмо не дошло из-за настройки про язык"
    assert 333 in telegram.chat_ids


# ── История рассылок ────────────────────────────────────────────────────────

def test_a_sent_broadcast_is_written_to_history(telegram):
    """
    Рассылка уходит в телеграм и нигде не остаётся. 08.11.2026 владелец
    отправил четыре сообщения, и восстановить их тексты было уже неоткуда:
    отчёт об отправке живёт одну страницу и исчезает с перезагрузкой.
    """
    bls = _make_bls()
    r, _ = _post(ADMIN_SESSION, "/admin/broadcast/send", bls=bls,
                 data={"text": "привет", "recipient": "all", "language_id": "any"})

    assert r.status_code == 200
    bls.add_broadcast.assert_awaited_once()
    (переданный_админ, запись), _ = bls.add_broadcast.await_args
    assert переданный_админ == "admin-1"
    assert запись["text"] == "привет"
    assert запись["recipient"] == "all"
    assert "sent_count" in запись


def test_history_is_written_even_when_nothing_was_sent(telegram):
    """
    Самый нужный случай. «Отправлено 0» выглядит поломкой, а причина — отказ
    человека от сообщений — видна только в записи. Если не писать историю при
    нуле, разбираться будет не с чем.
    """
    # Нужна заглушка с живыми получателями: без них рассылка не дойдёт до
    # проверки настройки, и пропускать будет некого.
    bls = _bls_with_users()
    bls.get_settings = AsyncMock(return_value={"receive_messages": False})
    r, _ = _post(ADMIN_SESSION, "/admin/broadcast/send", bls=bls,
                 data={"text": "текст", "recipient": "all", "language_id": "lang1"})

    assert r.status_code == 200
    bls.add_broadcast.assert_awaited_once()
    (_, запись), _ = bls.add_broadcast.await_args
    assert запись["sent_count"] == 0
    assert запись["skipped"], "пропуски не записаны — разбираться будет не с чем"


def test_a_broken_history_does_not_break_the_broadcast(telegram):
    """
    Опора: запись в историю второстепенна. Если она не удалась, сообщения уже
    ушли людям, и падать страницей поздно — надо сказать об этом и показать
    отчёт.
    """
    bls = _make_bls()
    bls.add_broadcast = AsyncMock(side_effect=RuntimeError("база недоступна"))
    r, _ = _post(ADMIN_SESSION, "/admin/broadcast/send", bls=bls,
                 data={"text": "привет", "recipient": "all", "language_id": "any"})

    assert r.status_code == 200, "падение истории уронило страницу рассылки"
    assert "в историю не записалась" in r.text


def test_the_history_page_shows_what_was_sent():
    bls = _make_bls()
    bls.get_broadcasts = AsyncMock(return_value=[{
        "id": "b1", "text": "вышла версия 6", "sent_at": "2026-11-08 09:56",
        "recipient_name": "всем", "language_name": "независимо от языка",
        "sent_count": 3, "skipped": [], "errors": [],
    }])
    r, _ = _get(ADMIN_SESSION, "/admin/broadcasts", bls=bls)

    assert r.status_code == 200, r.text[:300]
    assert "вышла версия 6" in r.text
    assert "всем" in r.text
    bls.get_broadcasts.assert_awaited_once_with("admin-1", limit=100)


def test_the_empty_history_explains_itself():
    """
    Пустая история — не поломка: до 08.11.2026 рассылки не сохранялись вовсе.
    Человек должен прочесть это, а не гадать, куда делись отправленные письма.
    """
    bls = _make_bls()
    r, _ = _get(ADMIN_SESSION, "/admin/broadcasts", bls=bls)

    assert r.status_code == 200
    assert "нигде не сохранялись" in r.text


def test_the_history_is_closed_to_non_admins():
    bls = _make_bls()
    r, _ = _get(USER_SESSION, "/admin/broadcasts", bls=bls, follow_redirects=False)
    assert r.status_code in (302, 303, 307), "история открыта не админу"
