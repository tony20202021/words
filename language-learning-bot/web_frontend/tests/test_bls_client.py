"""Unit tests for web_frontend BLS HTTP client."""

import pytest
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from app.bls_client import BLSClient


def make_response(status: int, data: dict):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.is_success = (200 <= status < 300)
    resp.json.return_value = data
    return resp


@pytest.fixture
def client():
    return BLSClient(base_url="http://test-bls")


class TestGetOrCreateUser:
    @pytest.mark.asyncio
    async def test_returns_user_id_on_success(self, client):
        resp = make_response(200, {"user_id": "u1", "user_data": {}})
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.post = AsyncMock(return_value=resp)
            result = await client.get_or_create_user(telegram_id=123, username=None, first_name="Test")
        assert result["user_id"] == "u1"

    @pytest.mark.asyncio
    async def test_returns_empty_on_failure(self, client):
        resp = make_response(500, {})
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.post = AsyncMock(return_value=resp)
            result = await client.get_or_create_user(telegram_id=123, username=None, first_name="Test")
        assert result == {}


class TestAuthLookup:
    @pytest.mark.asyncio
    async def test_telegram_lookup_found(self, client):
        resp = make_response(200, {"found": True, "token": "tok-1", "message_sent": True})
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.post = AsyncMock(return_value=resp)
            result = await client.auth_lookup(mode="telegram", telegram_id=123)
        assert result["found"] is True
        assert result["token"] == "tok-1"

    @pytest.mark.asyncio
    async def test_name_lookup_not_found(self, client):
        resp = make_response(200, {"found": False})
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.post = AsyncMock(return_value=resp)
            result = await client.auth_lookup(mode="name", name="Антон")
        assert result["found"] is False

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self, client):
        resp = make_response(500, {})
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.post = AsyncMock(return_value=resp)
            result = await client.auth_lookup(mode="name", name="Test")
        assert result == {}


class TestAuthStatus:
    @pytest.mark.asyncio
    async def test_pending(self, client):
        resp = make_response(200, {"status": "pending"})
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
            result = await client.auth_status("tok-1")
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_confirmed_returns_user_id(self, client):
        resp = make_response(200, {"status": "confirmed", "user_id": "u1", "telegram_id": 123})
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
            result = await client.auth_status("tok-1")
        assert result["status"] == "confirmed"
        assert result["user_id"] == "u1"


class TestSessionMethods:
    @pytest.mark.asyncio
    async def test_start_session(self, client):
        resp = make_response(200, {"session_id": "s1", "card": {}})
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.post = AsyncMock(return_value=resp)
            result = await client.start_session("u1", "lang1")
        assert result["session_id"] == "s1"

    @pytest.mark.asyncio
    async def test_rate_word(self, client):
        resp = make_response(200, {"session_id": "s1", "card": {}})
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.post = AsyncMock(return_value=resp)
            result = await client.rate_word("s1", "know")
        assert result["session_id"] == "s1"

    @pytest.mark.asyncio
    async def test_reconsider(self, client):
        resp = make_response(200, {"session_id": "s1", "card": {}})
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.post = AsyncMock(return_value=resp)
            result = await client.reconsider("s1")
        assert result["session_id"] == "s1"

    @pytest.mark.asyncio
    async def test_next_batch_not_loaded(self, client):
        resp = make_response(200, {"loaded": False})
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.post = AsyncMock(return_value=resp)
            result = await client.next_batch("s1")
        assert result["loaded"] is False


class TestChartMethods:
    @pytest.mark.asyncio
    async def test_get_chart_returns_bytes_on_success(self, client):
        png_data = b"\x89PNG\r\n\x1a\n"
        resp = MagicMock(spec=httpx.Response)
        resp.is_success = True
        resp.content = png_data
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
            result = await client.get_chart("u1", "lang1", "words_for_today")
        assert result == png_data

    @pytest.mark.asyncio
    async def test_get_chart_returns_none_on_failure(self, client):
        resp = MagicMock(spec=httpx.Response)
        resp.is_success = False
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
            result = await client.get_chart("u1", "lang1", "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_monthly_chart_show_all_true(self, client):
        png_data = b"\x89PNG\r\n\x1a\n"
        resp = MagicMock(spec=httpx.Response)
        resp.is_success = True
        resp.content = png_data
        with patch("httpx.AsyncClient") as mock_cls:
            get_mock = AsyncMock(return_value=resp)
            mock_cls.return_value.__aenter__.return_value.get = get_mock
            result = await client.get_monthly_chart("u1", "lang1", "words_studied", show_all=True)
        assert result == png_data
        call_kwargs = get_mock.call_args
        assert call_kwargs.kwargs["params"]["show_all"] == "true"

    @pytest.mark.asyncio
    async def test_get_monthly_chart_show_all_false(self, client):
        png_data = b"\x89PNG\r\n\x1a\n"
        resp = MagicMock(spec=httpx.Response)
        resp.is_success = True
        resp.content = png_data
        with patch("httpx.AsyncClient") as mock_cls:
            get_mock = AsyncMock(return_value=resp)
            mock_cls.return_value.__aenter__.return_value.get = get_mock
            result = await client.get_monthly_chart("u1", "lang1", "words_studied", show_all=False)
        assert result == png_data
        call_kwargs = get_mock.call_args
        assert call_kwargs.kwargs["params"]["show_all"] == "false"

    @pytest.mark.asyncio
    async def test_get_monthly_chart_returns_none_on_failure(self, client):
        resp = MagicMock(spec=httpx.Response)
        resp.is_success = False
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
            result = await client.get_monthly_chart("u1", "lang1", "words_studied")
        assert result is None


class TestWordHints:
    @pytest.mark.asyncio
    async def test_get_word_hints_returns_dict(self, client):
        hints_data = {"meaning": "солнце = тепло", "writing": ""}
        resp = make_response(200, hints_data)
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
            result = await client.get_word_hints("u1", "word-123")
        assert result == hints_data

    @pytest.mark.asyncio
    async def test_get_word_hints_returns_empty_on_failure(self, client):
        resp = make_response(500, {})
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
            result = await client.get_word_hints("u1", "word-123")
        assert result == {}

    @pytest.mark.asyncio
    async def test_set_word_hint_returns_true_on_success(self, client):
        resp = make_response(200, {"ok": True})
        with patch("httpx.AsyncClient") as mock_cls:
            put_mock = AsyncMock(return_value=resp)
            mock_cls.return_value.__aenter__.return_value.put = put_mock
            result = await client.set_word_hint("u1", "word-123", "meaning", "солнце = тепло",
                                                language_id="lang1")
        assert result is True
        call_body = put_mock.call_args.kwargs["json"]
        assert call_body["hint_type"] == "meaning"
        assert call_body["text"] == "солнце = тепло"
        assert call_body["language_id"] == "lang1"

    @pytest.mark.asyncio
    async def test_set_word_hint_returns_false_on_failure(self, client):
        resp = make_response(500, {})
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.put = AsyncMock(return_value=resp)
            result = await client.set_word_hint("u1", "word-123", "meaning", "text")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_word_hint_returns_true_on_success(self, client):
        resp = make_response(200, {"ok": True})
        with patch("httpx.AsyncClient") as mock_cls:
            delete_mock = AsyncMock(return_value=resp)
            mock_cls.return_value.__aenter__.return_value.delete = delete_mock
            result = await client.delete_word_hint("u1", "word-123", "meaning")
        assert result is True
        url = delete_mock.call_args.args[0]
        assert "hints/u1/word-123/meaning" in url

    @pytest.mark.asyncio
    async def test_delete_word_hint_returns_false_on_failure(self, client):
        resp = make_response(404, {})
        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value.delete = AsyncMock(return_value=resp)
            result = await client.delete_word_hint("u1", "word-123", "meaning")
        assert result is False
