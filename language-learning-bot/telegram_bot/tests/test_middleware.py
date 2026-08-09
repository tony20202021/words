"""Unit tests for UserMiddleware."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.bot.middleware import UserMiddleware


def _make_tg_user(tg_id=111, username="testuser", first_name="Test"):
    u = MagicMock()
    u.id = tg_id
    u.username = username
    u.first_name = first_name
    u.last_name = None
    return u


def _make_bls(bls_id="bls-user-1"):
    bls = AsyncMock()
    bls.get_or_create_user = AsyncMock(
        return_value={"status": 200, "data": {"id": bls_id}}
    )
    return bls


async def _invoke(middleware, tg_user, handler=None):
    """Call middleware and return the injected data dict."""
    captured = {}

    async def _handler(event, data):
        captured.update(data)

    data = {"event_from_user": tg_user}
    await middleware(_handler if handler is None else handler, MagicMock(), data)
    return data


@pytest.mark.asyncio
async def test_middleware_injects_bls_user_id():
    bls = _make_bls("bls-123")
    mw = UserMiddleware(bls)
    data = await _invoke(mw, _make_tg_user(tg_id=42))
    assert data["bls_user_id"] == "bls-123"


@pytest.mark.asyncio
async def test_middleware_calls_get_or_create_user():
    bls = _make_bls()
    mw = UserMiddleware(bls)
    await _invoke(mw, _make_tg_user(tg_id=99, username="bob", first_name="Bob"))
    bls.get_or_create_user.assert_called_once()
    call_kwargs = bls.get_or_create_user.call_args
    assert call_kwargs[0][0] == 99  # telegram_id positional


@pytest.mark.asyncio
async def test_middleware_caches_user_id():
    bls = _make_bls("cached-id")
    mw = UserMiddleware(bls)
    user = _make_tg_user(tg_id=7)
    await _invoke(mw, user)
    await _invoke(mw, user)
    # BLS should be called only once; second call uses cache
    assert bls.get_or_create_user.call_count == 1


@pytest.mark.asyncio
async def test_middleware_different_users_resolved_independently():
    bls = AsyncMock()
    bls.get_or_create_user = AsyncMock(side_effect=[
        {"status": 200, "data": {"id": "id-for-1"}},
        {"status": 200, "data": {"id": "id-for-2"}},
    ])
    mw = UserMiddleware(bls)
    d1 = await _invoke(mw, _make_tg_user(tg_id=1))
    d2 = await _invoke(mw, _make_tg_user(tg_id=2))
    assert d1["bls_user_id"] == "id-for-1"
    assert d2["bls_user_id"] == "id-for-2"


@pytest.mark.asyncio
async def test_middleware_fallback_to_telegram_id_on_empty_response():
    bls = AsyncMock()
    bls.get_or_create_user = AsyncMock(return_value={"status": 500, "data": None})
    mw = UserMiddleware(bls)
    data = await _invoke(mw, _make_tg_user(tg_id=55))
    # fallback: str(telegram_id)
    assert data["bls_user_id"] == "55"


@pytest.mark.asyncio
async def test_middleware_no_user_no_injection():
    bls = _make_bls()
    mw = UserMiddleware(bls)
    data = {"event_from_user": None}

    async def _handler(event, data_):
        data.update(data_)

    await mw(_handler, MagicMock(), data)
    assert "bls_user_id" not in data
    bls.get_or_create_user.assert_not_called()


@pytest.mark.asyncio
async def test_middleware_passes_through_to_handler():
    bls = _make_bls()
    mw = UserMiddleware(bls)
    handler_called = []

    async def _handler(event, data):
        handler_called.append(True)

    data = {"event_from_user": _make_tg_user()}
    await mw(_handler, MagicMock(), data)
    assert handler_called == [True]


@pytest.mark.asyncio
async def test_middleware_recovers_after_backend_failure():
    """Раньше при недоступном BLS в кэш оседал telegram_id, повторный запрос уже
    не делался, и человек до перезапуска процесса работал с несуществующим
    аккаунтом: прогресс уходил в никуда, а внешне всё выглядело исправным."""
    bls = AsyncMock()
    bls.get_or_create_user = AsyncMock(side_effect=[
        {"status": 500, "data": None},
        {"status": 200, "data": {"id": "real-id"}},
    ])
    mw = UserMiddleware(bls)
    user = _make_tg_user(tg_id=77)

    first = await _invoke(mw, user)
    assert first["bls_user_id"] == "77"      # аварийный ход на текущий апдейт

    second = await _invoke(mw, user)
    assert second["bls_user_id"] == "real-id"
    assert bls.get_or_create_user.call_count == 2


@pytest.mark.asyncio
async def test_middleware_does_not_cache_failed_lookup():
    bls = AsyncMock()
    bls.get_or_create_user = AsyncMock(return_value={"status": 500, "data": None})
    mw = UserMiddleware(bls)
    user = _make_tg_user(tg_id=88)

    await _invoke(mw, user)
    await _invoke(mw, user)
    assert bls.get_or_create_user.call_count == 2


@pytest.mark.asyncio
async def test_middleware_ignores_200_without_id():
    """Ответ 200 без идентификатора — не повод считать пользователя решённым."""
    bls = AsyncMock()
    bls.get_or_create_user = AsyncMock(side_effect=[
        {"status": 200, "data": {}},
        {"status": 200, "data": {"user_id": "late-id"}},
    ])
    mw = UserMiddleware(bls)
    user = _make_tg_user(tg_id=99)

    assert (await _invoke(mw, user))["bls_user_id"] == "99"
    assert (await _invoke(mw, user))["bls_user_id"] == "late-id"
