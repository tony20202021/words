"""
HTTP client for the Business Logic Service (:8700).
Thin wrapper — all business logic lives in BLS.
All session endpoints return {session_id, card}.
"""

import os
from typing import Dict, Any, Optional
from urllib.parse import quote
import aiohttp

BLS_URL = os.environ.get("BLS_URL", "http://localhost:8700")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8500")


class BLSClient:
    def __init__(self, base_url: str = BLS_URL, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def _get(self, path: str) -> Dict[str, Any]:
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(f"{self.base_url}{path}") as resp:
                return {"status": resp.status, "data": await resp.json() if resp.status < 400 else None}

    async def _post(self, path: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(f"{self.base_url}{path}", json=payload or {}) as resp:
                return {"status": resp.status, "data": await resp.json() if resp.status < 400 else None}

    async def _delete(self, path: str) -> Dict[str, Any]:
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.delete(f"{self.base_url}{path}") as resp:
                return {"status": resp.status, "data": await resp.json() if resp.status < 400 else None}

    async def _put(self, path: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.put(f"{self.base_url}{path}", json=payload or {}) as resp:
                return {"status": resp.status, "data": await resp.json() if resp.status < 400 else None}

    async def _patch(self, path: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.patch(f"{self.base_url}{path}", json=payload or {}) as resp:
                return {"status": resp.status, "data": await resp.json() if resp.status < 400 else None}

    async def _get_bytes(self, path: str) -> Optional[bytes]:
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(f"{self.base_url}{path}") as resp:
                if resp.status < 400:
                    return await resp.read()
                return None

    # ── User ──────────────────────────────────────────────────────────────────

    async def get_or_create_user(
        self, telegram_id: int, username: Optional[str], first_name: str, last_name: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self._post("/user/get_or_create", {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
        })

    async def is_admin(self, user_id: str) -> bool:
        result = await self._get(f"/user/{user_id}/is_admin")
        return (result.get("data") or {}).get("is_admin", False)

    # ── Settings ──────────────────────────────────────────────────────────────

    async def get_settings(self, user_id: str, language_id: str) -> Dict[str, Any]:
        result = await self._get(f"/settings/{user_id}/{language_id}")
        return result.get("data") or {}

    async def toggle_setting(self, user_id: str, language_id: str, key: str) -> Dict[str, Any]:
        result = await self._post(f"/settings/{user_id}/{language_id}/{key}/toggle")
        return result.get("data") or {}

    async def set_setting(self, user_id: str, language_id: str, key: str, value) -> Dict[str, Any]:
        result = await self._put(f"/settings/{user_id}/{language_id}/{key}", {"value": value})
        return result.get("data") or {}

    async def get_hint_settings(self, user_id: str, language_id: str) -> Dict[str, bool]:
        result = await self._get(f"/settings/{user_id}/{language_id}/hints")
        return result.get("data") or {}

    async def toggle_hint(self, user_id: str, language_id: str, hint_key: str) -> Dict[str, bool]:
        result = await self._post(f"/settings/{user_id}/{language_id}/hints/{hint_key}/toggle")
        return result.get("data") or {}

    # ── Session — all return {session_id, card} ───────────────────────────────

    async def start_session(
        self, user_id: str, language_id: str, settings: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {"user_id": user_id, "language_id": language_id}
        if settings:
            payload["settings"] = settings
        result = await self._post("/session/start", payload)
        return result.get("data")

    async def get_session(self, user_id: str, language_id: str) -> Optional[Dict[str, Any]]:
        result = await self._get(f"/session/{user_id}/{language_id}")
        return result.get("data") if result["status"] == 200 else None

    async def show_answer(self, session_id: str) -> Dict[str, Any]:
        result = await self._post(f"/session/{session_id}/show_answer")
        return result.get("data") or {}

    async def know_word(self, session_id: str) -> Dict[str, Any]:
        result = await self._post(f"/session/{session_id}/know")
        return result.get("data") or {}

    async def rate_word(self, session_id: str, rating: str) -> Dict[str, Any]:
        result = await self._post(f"/session/{session_id}/rate", {"rating": rating})
        return result.get("data") or {}

    async def next_batch(self, session_id: str) -> Dict[str, Any]:
        result = await self._post(f"/session/{session_id}/next_batch")
        return result.get("data") or {"loaded": False}

    async def reconsider(self, session_id: str) -> Dict[str, Any]:
        result = await self._post(f"/session/{session_id}/reconsider")
        return result.get("data") or {}

    async def toggle_skip(self, session_id: str) -> Dict[str, Any]:
        result = await self._post(f"/session/{session_id}/toggle_skip")
        return result.get("data") or {}

    async def get_progress(self, session_id: str) -> Dict[str, Any]:
        result = await self._get(f"/session/{session_id}/progress")
        return result.get("data") or {}

    async def end_session(self, user_id: str, language_id: str) -> None:
        await self._delete(f"/session/{user_id}/{language_id}")

    # ── Auth ─────────────────────────────────────────────────────────────────

    async def auth_confirm(self, token: str) -> Dict[str, Any]:
        result = await self._post(f"/auth/confirm/{token}")
        return result.get("data") or {}

    async def auth_deny(self, token: str) -> Dict[str, Any]:
        result = await self._post(f"/auth/deny/{token}")
        return result.get("data") or {}

    # ── Admin ─────────────────────────────────────────────────────────────────

    async def admin_global_stats(self, user_id: str) -> Dict[str, Any]:
        result = await self._get(f"/admin/stats?user_id={user_id}")
        return result.get("data") or {}

    async def admin_list_users(self, user_id: str, page: int = 1) -> Dict[str, Any]:
        result = await self._get(f"/admin/users?user_id={user_id}&page={page}")
        return result.get("data") or {}

    async def admin_toggle_admin(self, user_id: str, target_user_id: str, is_admin: bool) -> Dict[str, Any]:
        result = await self._post(f"/admin/users/{target_user_id}/toggle_admin?user_id={user_id}",
                                  {"is_admin": is_admin})
        return result.get("data") or {}

    async def admin_create_language(self, user_id: str, name_ru: str, name_foreign: str) -> Dict[str, Any]:
        result = await self._post(f"/admin/languages?user_id={user_id}",
                                  {"name_ru": name_ru, "name_foreign": name_foreign})
        return result.get("data") or {}

    async def admin_delete_language(self, user_id: str, language_id: str) -> Dict[str, Any]:
        result = await self._delete(f"/admin/languages/{language_id}?user_id={user_id}")
        return result.get("data") or {}

    async def admin_word_by_number(self, user_id: str, language_id: str, number: int) -> Dict[str, Any]:
        result = await self._get(
            f"/admin/languages/{language_id}/words/by_number/{number}?user_id={user_id}")
        return result.get("data") or {}

    async def admin_get_user_details(self, user_id: str, target_user_id: str) -> Dict[str, Any]:
        result = await self._get(f"/admin/users/{target_user_id}?user_id={user_id}")
        return result.get("data") or {}

    async def admin_update_language(self, user_id: str, language_id: str,
                                    name_ru: str, name_foreign: str) -> bool:
        result = await self._put(f"/admin/languages/{language_id}?user_id={user_id}",
                                 {"name_ru": name_ru, "name_foreign": name_foreign})
        return bool((result.get("data") or {}).get("ok"))

    async def admin_update_word(self, user_id: str, word_id: str, field: str, value: str) -> bool:
        result = await self._patch(f"/admin/words/{word_id}?user_id={user_id}",
                                   {"field": field, "value": value})
        return bool((result.get("data") or {}).get("ok"))

    async def admin_delete_word(self, user_id: str, word_id: str) -> bool:
        result = await self._delete(f"/admin/words/{word_id}?user_id={user_id}")
        return bool((result.get("data") or {}).get("ok"))

    async def admin_export_words(self, user_id: str, language_id: str,
                                 fmt: str = "xlsx",
                                 start: int = None, end: int = None) -> Optional[bytes]:
        params = f"user_id={user_id}&format={fmt}"
        if start is not None:
            params += f"&start={start}"
        if end is not None:
            params += f"&end={end}"
        return await self._get_bytes(f"/admin/languages/{language_id}/export?{params}")

    async def admin_import_words(
        self, user_id: str, language_id: str,
        file_data: bytes, filename: str,
        clear_existing: bool = False,
    ) -> Dict[str, Any]:
        timeout = aiohttp.ClientTimeout(total=120)  # import may take a while
        async with aiohttp.ClientSession(timeout=timeout) as session:
            form = aiohttp.FormData()
            form.add_field(
                "file", file_data,
                filename=filename,
                content_type="application/octet-stream",
            )
            url = (
                f"{self.base_url}/admin/languages/{language_id}/import"
                f"?user_id={user_id}&clear_existing={str(clear_existing).lower()}"
            )
            async with session.post(url, data=form) as resp:
                if resp.status < 400:
                    return await resp.json()
                return {"ok": False, "error": f"HTTP {resp.status}"}

    # ── Languages & Statistics ────────────────────────────────────────────────

    async def get_languages(self) -> list:
        result = await self._get("/languages/")
        return result.get("data") or []

    async def get_statistics(self, user_id: str, language_id: str) -> Dict[str, Any]:
        result = await self._get(f"/statistics/{user_id}/{language_id}")
        return result.get("data") or {}

    async def get_chart(self, user_id: str, language_id: str, chart_name: str) -> Optional[bytes]:
        return await self._get_bytes(f"/statistics/{user_id}/{language_id}/chart/{chart_name}")

    async def get_monthly_chart(self, user_id: str, language_id: str, chart_name: str) -> Optional[bytes]:
        return await self._get_bytes(f"/statistics/{user_id}/{language_id}/monthly-chart/{chart_name}")

    # ── Hints ─────────────────────────────────────────────────────────────────

    async def get_word_hints(self, user_id: str, word_id: str) -> Dict[str, str]:
        result = await self._get(f"/hints/{user_id}/{word_id}")
        return result.get("data") or {}

    async def set_word_hint(
        self, user_id: str, word_id: str,
        hint_type: str, text: str,
        language_id: Optional[str] = None,
    ) -> bool:
        payload: Dict[str, Any] = {"hint_type": hint_type, "text": text}
        if language_id:
            payload["language_id"] = language_id
        result = await self._put(f"/hints/{user_id}/{word_id}", payload)
        return bool((result.get("data") or {}).get("ok"))

    async def delete_word_hint(self, user_id: str, word_id: str, hint_type: str) -> bool:
        result = await self._delete(f"/hints/{user_id}/{word_id}/{hint_type}")
        return bool((result.get("data") or {}).get("ok"))

    # ── Sounds ────────────────────────────────────────────────────────────────

    async def get_help(self) -> Dict[str, Any]:
        result = await self._get("/help")
        return result.get("data") or {}

    async def mobile_create_token(self, user_id: str) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/auth/mobile/create",
                                    json={"user_id": user_id}) as resp:
                return await resp.json() if resp.status == 200 else {}

    async def get_sound(self, path: str) -> Optional[bytes]:
        encoded = quote(path, safe="").replace(".", "%2E")
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{BACKEND_URL}/api/sounds/{encoded}") as resp:
                if resp.status == 200:
                    return await resp.read()
        return None


_client: Optional[BLSClient] = None


def get_bls_client() -> BLSClient:
    global _client
    if _client is None:
        _client = BLSClient(os.environ.get("BLS_URL", "http://localhost:8700"))
    return _client
