"""
Чтение, не уложившееся в ожидание, повторяется, а не роняет запрос.

Утром 17, 19 и 20.11.2026 первый за день подбор слов шёл дольше пяти
секунд, которые клиент ждёт бэкенд. Повторы в _make_request ловили только
aiohttp.ClientError, а превышение общего ожидания — asyncio.TimeoutError: оно
проскакивало мимо, и служба отвечала приложению 500. Повтор прошёл бы: пока
клиент ждал, бэкенд поднял данные из подкачки, и второй такой же запрос
занимал 0,07 с.

Повторяется только чтение (GET): запись, не дождавшись ответа, могла уже
примениться, и повтор применил бы её дважды.
"""

import asyncio
import os
import sys

import pytest
from aiohttp import web

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.api.client import APIClient  # noqa: E402


async def _serve(slow_first: bool):
    calls = {"n": 0}

    async def handler(request):
        calls["n"] += 1
        if slow_first and calls["n"] == 1:
            await asyncio.sleep(0.6)
        return web.json_response({"ok": True})

    app = web.Application()
    app.router.add_route("*", "/api/thing", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    return runner, f"http://127.0.0.1:{port}", calls


@pytest.mark.asyncio
async def test_a_slow_read_is_retried_instead_of_failing():
    runner, url, calls = await _serve(slow_first=True)
    try:
        client = APIClient(url, timeout=0.3, retry_count=3)
        result = await client._make_request("GET", "/thing")
    finally:
        await runner.cleanup()
    assert result["success"], f"медленное чтение не повторилось: {result}"
    assert result["result"] == {"ok": True}
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_a_slow_write_is_not_repeated():
    runner, url, calls = await _serve(slow_first=True)
    try:
        client = APIClient(url, timeout=0.3, retry_count=3)
        with pytest.raises(asyncio.TimeoutError):
            await client._make_request("POST", "/thing", data={"x": 1})
    finally:
        await runner.cleanup()
    assert calls["n"] == 1, "запись, не дождавшись ответа, отправлена повторно"
