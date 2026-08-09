"""Unit tests for admin_service — all calls to api_client are mocked."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services import admin_service


def _ok(result):
    return {"success": True, "result": result}

def _fail():
    return {"success": False, "result": None}


# ── get_global_stats ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_global_stats_returns_counts():
    api = MagicMock()
    api.get_users_count = AsyncMock(return_value=_ok({"count": 42}))
    api.get_languages = AsyncMock(return_value=_ok([
        {"id": "lang1", "name_ru": "Китайский", "name_foreign": "中文"},
    ]))
    api.get_word_count_by_language = AsyncMock(return_value=_ok({"count": 100}))
    api.get_language_active_users = AsyncMock(return_value=_ok({"count": 5}))

    stats = await admin_service.get_global_stats(api)

    assert stats["total_users"] == 42
    assert len(stats["languages"]) == 1
    assert stats["languages"][0]["word_count"] == 100
    assert stats["languages"][0]["active_users"] == 5


@pytest.mark.asyncio
async def test_get_global_stats_api_failure_returns_zeros():
    api = MagicMock()
    api.get_users_count = AsyncMock(return_value=_fail())
    api.get_languages = AsyncMock(return_value=_fail())

    stats = await admin_service.get_global_stats(api)
    assert stats["total_users"] == 0
    assert stats["languages"] == []


# ── get_users_page ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_users_page_pagination():
    users = [{"id": f"u{i}"} for i in range(5)]
    api = MagicMock()
    api.get_users = AsyncMock(return_value=_ok(users))
    api.get_users_count = AsyncMock(return_value=_ok({"count": 45}))

    result = await admin_service.get_users_page(page=1, api_client=api)

    assert result["users"] == users
    assert result["page"] == 1
    assert result["total"] == 45
    assert result["total_pages"] == 3   # ceil(45/20)
    api.get_users.assert_called_once_with(skip=0, limit=20)


@pytest.mark.asyncio
async def test_get_users_page_second_page_skip():
    api = MagicMock()
    api.get_users = AsyncMock(return_value=_ok([]))
    api.get_users_count = AsyncMock(return_value=_ok({"count": 0}))

    await admin_service.get_users_page(page=3, api_client=api)
    api.get_users.assert_called_once_with(skip=40, limit=20)


# ── get_user_details ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_user_details_includes_languages_with_progress():
    api = MagicMock()
    api.get_languages = AsyncMock(return_value=_ok([
        {"id": "lang1", "name_ru": "Китайский", "name_foreign": "中文"},
        {"id": "lang2", "name_ru": "Японский",  "name_foreign": "日本語"},
    ]))
    api.get_user_progress = AsyncMock(side_effect=[
        _ok({"words_studied": 10, "words_known": 5}),
        _ok({"words_studied": 0,  "words_known": 0}),
    ])
    api.get_user = AsyncMock(return_value={"id": "user1", "is_admin": False})

    result = await admin_service.get_user_details("user1", api)
    # Only lang1 has words_studied > 0
    assert len(result["progress"]) == 1
    assert result["progress"][0]["language_id"] == "lang1"


# ── права администратора ──────────────────────────────────────────────────────
# Прежние два теста здесь закрепляли ошибку: они требовали, чтобы функция писала
# ОТРИЦАНИЕ присланного значения. Именно из-за этого переключатель работал
# наоборот, а тесты были зелёными — они проверяли реализацию, а не контракт.

@pytest.mark.asyncio
async def test_set_admin_api_failure_returns_false():
    api = MagicMock()
    api.update_user = AsyncMock(return_value=_fail())
    ok = await admin_service.set_admin("u1", True, api)
    assert ok is False


# ── Language CRUD ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_language_success():
    api = MagicMock()
    api.create_language = AsyncMock(return_value=_ok({"id": "new_lang"}))
    result = await admin_service.create_language("Китайский", "中文", api)
    assert result["ok"] is True
    api.create_language.assert_called_once_with({"name_ru": "Китайский", "name_foreign": "中文"})


@pytest.mark.asyncio
async def test_delete_language_failure():
    api = MagicMock()
    api.delete_language = AsyncMock(return_value=_fail())
    ok = await admin_service.delete_language("lang1", api)
    assert ok is False


# ── Word management ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_words_page():
    words = [{"id": f"w{i}", "number": i} for i in range(1, 6)]
    api = MagicMock()
    api.get_words_by_language = AsyncMock(return_value=_ok(words))
    api.get_word_count_by_language = AsyncMock(return_value=_ok({"count": 5}))

    result = await admin_service.get_words_page("lang1", page=1, api_client=api)
    assert len(result["words"]) == 5
    assert result["total"] == 5
    assert result["total_pages"] == 1


@pytest.mark.asyncio
async def test_get_word_by_number_list_result():
    api = MagicMock()
    api.get_word_by_number = AsyncMock(return_value=_ok([{"id": "w1", "number": 1}]))
    word = await admin_service.get_word_by_number("lang1", 1, api)
    assert word["id"] == "w1"


@pytest.mark.asyncio
async def test_get_word_by_number_dict_result():
    api = MagicMock()
    api.get_word_by_number = AsyncMock(return_value=_ok({"id": "w1", "number": 1}))
    word = await admin_service.get_word_by_number("lang1", 1, api)
    assert word["id"] == "w1"


@pytest.mark.asyncio
async def test_get_word_by_number_not_found():
    api = MagicMock()
    api.get_word_by_number = AsyncMock(return_value=_fail())
    word = await admin_service.get_word_by_number("lang1", 999, api)
    assert word is None


@pytest.mark.asyncio
async def test_update_word_field():
    api = MagicMock()
    api.update_word = AsyncMock(return_value=_ok({"id": "w1"}))
    ok = await admin_service.update_word_field("w1", "translation", "новый перевод", api)
    assert ok is True
    api.update_word.assert_called_once_with("w1", {"translation": "новый перевод"})


@pytest.mark.asyncio
async def test_delete_word():
    api = MagicMock()
    api.delete_word = AsyncMock(return_value=_ok({}))
    ok = await admin_service.delete_word("w1", api)
    assert ok is True


# ── Export / Import ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_words_success():
    api = MagicMock()
    api.export_words_by_language = AsyncMock(return_value=_ok(b"BINARY"))
    result = await admin_service.export_words("lang1", "xlsx", 1, 100, api)
    assert result == b"BINARY"


@pytest.mark.asyncio
async def test_export_words_failure_returns_none():
    api = MagicMock()
    api.export_words_by_language = AsyncMock(return_value=_fail())
    result = await admin_service.export_words("lang1", "xlsx", None, None, api)
    assert result is None


@pytest.mark.asyncio
async def test_import_words_success():
    api = MagicMock()
    api.upload_words_file = AsyncMock(return_value=_ok({"imported": 50}))
    result = await admin_service.import_words("lang1", b"DATA", "file.xlsx", {}, api)
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_import_words_failure():
    api = MagicMock()
    api.upload_words_file = AsyncMock(return_value={**_fail(), "error": "bad file"})
    result = await admin_service.import_words("lang1", b"DATA", "file.xlsx", {}, api)
    assert result["ok"] is False
    assert result["error"] == "bad file"

# ── права администратора ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_admin_writes_the_value_it_is_given():
    """
    Раньше функция звалась toggle_admin и писала ОТРИЦАНИЕ присланного, считая
    его текущим состоянием. Но поле запроса называется is_admin, и оба клиента
    слали в нём желаемое значение — переключатель работал наоборот: «дать права»
    снимало их. В вебе это выглядело как «права можно только снять».
    """
    from app.services import admin_service

    api = MagicMock()
    api.update_user = AsyncMock(return_value={"success": True})

    assert await admin_service.set_admin("u1", True, api) is True
    assert api.update_user.call_args.args == ("u1", {"is_admin": True})

    await admin_service.set_admin("u1", False, api)
    assert api.update_user.call_args.args == ("u1", {"is_admin": False})


@pytest.mark.asyncio
async def test_user_details_report_admin_flag():
    """Странице пользователя нужен фактический флаг, чтобы нарисовать верную кнопку."""
    from app.services import admin_service

    api = MagicMock()
    api.get_languages = AsyncMock(return_value={"success": True, "result": []})
    api.get_user = AsyncMock(return_value={"id": "u1", "is_admin": True})

    detail = await admin_service.get_user_details("u1", api)
    assert detail["is_admin"] is True
    assert detail["user_id"] == "u1"


@pytest.mark.asyncio
async def test_user_details_survive_a_missing_user():
    from app.services import admin_service

    api = MagicMock()
    api.get_languages = AsyncMock(return_value={"success": True, "result": []})
    api.get_user = AsyncMock(return_value=None)

    detail = await admin_service.get_user_details("u1", api)
    assert detail["is_admin"] is False

