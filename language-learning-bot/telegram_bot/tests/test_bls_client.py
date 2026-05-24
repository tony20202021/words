"""Unit tests for the Telegram bot BLS HTTP client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.bls_client.client import BLSClient


def _mock_resp(status=200, data=None, content=None):
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=data)
    resp.read = AsyncMock(return_value=content or b"")
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=None)
    return resp


def _mock_session(resp):
    sess = MagicMock()
    sess.get = MagicMock(return_value=resp)
    sess.post = MagicMock(return_value=resp)
    sess.put = MagicMock(return_value=resp)
    sess.delete = MagicMock(return_value=resp)
    sess.__aenter__ = AsyncMock(return_value=sess)
    sess.__aexit__ = AsyncMock(return_value=None)
    return sess


@pytest.fixture
def client():
    return BLSClient(base_url="http://test-bls")


# ── settings ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_settings_returns_data(client):
    resp = _mock_resp(200, {"use_check_date": True, "start_word": 1})
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await client.get_settings("u1", "lang1")
    assert result["use_check_date"] is True


@pytest.mark.asyncio
async def test_get_settings_returns_empty_on_error(client):
    resp = _mock_resp(500)
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await client.get_settings("u1", "lang1")
    assert result == {}


@pytest.mark.asyncio
async def test_toggle_setting_posts_and_returns_data(client):
    resp = _mock_resp(200, {"use_check_date": False})
    sess = _mock_session(resp)
    with patch("aiohttp.ClientSession", return_value=sess):
        result = await client.toggle_setting("u1", "lang1", "use_check_date")
    assert result == {"use_check_date": False}
    sess.post.assert_called_once()


@pytest.mark.asyncio
async def test_set_setting_uses_put(client):
    resp = _mock_resp(200, {"start_word": 5})
    sess = _mock_session(resp)
    with patch("aiohttp.ClientSession", return_value=sess):
        result = await client.set_setting("u1", "lang1", "start_word", 5)
    sess.put.assert_called_once()


@pytest.mark.asyncio
async def test_set_setting_returns_empty_on_error(client):
    resp = _mock_resp(400)
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await client.set_setting("u1", "lang1", "start_word", 5)
    assert result == {}


# ── session ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_start_session_returns_card(client):
    resp = _mock_resp(200, {"session_id": "s1", "card": {}})
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await client.start_session("u1", "lang1")
    assert result["session_id"] == "s1"


@pytest.mark.asyncio
async def test_get_session_returns_none_on_404(client):
    resp = _mock_resp(404)
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await client.get_session("u1", "lang1")
    assert result is None


@pytest.mark.asyncio
async def test_get_session_returns_data_on_200(client):
    resp = _mock_resp(200, {"session_id": "s1", "card": {}})
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await client.get_session("u1", "lang1")
    assert result["session_id"] == "s1"


@pytest.mark.asyncio
async def test_know_word_posts(client):
    resp = _mock_resp(200, {"session_id": "s1", "card": {}})
    sess = _mock_session(resp)
    with patch("aiohttp.ClientSession", return_value=sess):
        result = await client.know_word("s1")
    sess.post.assert_called_once()
    assert result["session_id"] == "s1"


@pytest.mark.asyncio
async def test_rate_word_sends_rating(client):
    resp = _mock_resp(200, {"session_id": "s1", "card": {}})
    sess = _mock_session(resp)
    with patch("aiohttp.ClientSession", return_value=sess):
        await client.rate_word("s1", "know")
    _, kwargs = sess.post.call_args
    assert kwargs.get("json", {}).get("rating") == "know"


@pytest.mark.asyncio
async def test_reconsider_posts(client):
    resp = _mock_resp(200, {"session_id": "s1", "card": {}})
    sess = _mock_session(resp)
    with patch("aiohttp.ClientSession", return_value=sess):
        result = await client.reconsider("s1")
    sess.post.assert_called_once()
    assert result["session_id"] == "s1"


@pytest.mark.asyncio
async def test_next_batch_returns_loaded_false_on_error(client):
    resp = _mock_resp(500)
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await client.next_batch("s1")
    assert result.get("loaded") is False


# ── languages & stats ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_languages_returns_list(client):
    resp = _mock_resp(200, [{"id": "l1", "name_ru": "Английский"}])
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await client.get_languages()
    assert result[0]["id"] == "l1"


@pytest.mark.asyncio
async def test_get_languages_returns_empty_on_error(client):
    resp = _mock_resp(500)
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await client.get_languages()
    assert result == []


@pytest.mark.asyncio
async def test_get_statistics_returns_data(client):
    stats = {"total_words": 100, "words_studied": 50}
    resp = _mock_resp(200, stats)
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await client.get_statistics("u1", "lang1")
    assert result["total_words"] == 100


# ── auth ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_is_admin_true(client):
    resp = _mock_resp(200, {"is_admin": True})
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await client.is_admin("u1")
    assert result is True


@pytest.mark.asyncio
async def test_is_admin_false_on_error(client):
    resp = _mock_resp(500)
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await client.is_admin("u1")
    assert result is False


@pytest.mark.asyncio
async def test_auth_confirm_ok(client):
    resp = _mock_resp(200, {"ok": True})
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await client.auth_confirm("tok-1")
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_auth_deny_ok(client):
    resp = _mock_resp(200, {"ok": True})
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await client.auth_deny("tok-1")
    assert result["ok"] is True


# ── sounds ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_sound_returns_bytes(client):
    audio = b"\xff\xfb\x90\x00fake mp3"
    resp = _mock_resp(200, content=audio)
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await client.get_sound("chinese/word1.mp3")
    assert result == audio


@pytest.mark.asyncio
async def test_get_sound_returns_none_on_failure(client):
    resp = _mock_resp(404)
    with patch("aiohttp.ClientSession", return_value=_mock_session(resp)):
        result = await client.get_sound("chinese/missing.mp3")
    assert result is None


@pytest.mark.asyncio
async def test_get_sound_url_encodes_path(client):
    resp = _mock_resp(200, content=b"data")
    sess = _mock_session(resp)
    with patch("aiohttp.ClientSession", return_value=sess):
        await client.get_sound("path/to/word.mp3")
    url = sess.get.call_args[0][0]
    # dots should be encoded as %2E, path separators as %2F
    assert "%2E" in url or "mp3" not in url.split("/api/sounds/")[-1]
