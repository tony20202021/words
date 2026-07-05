"""
HTTP client to Business Logic Service for web_frontend.
All session endpoints return {session_id, card}.
"""

import os
from typing import Dict, Any, Optional
import httpx

BLS_URL = os.environ.get("BLS_URL", "http://localhost:8531")


class BLSClient:
    def __init__(self, base_url: str = BLS_URL):
        self.base_url = base_url.rstrip("/")

    async def get_settings(self, user_id: str, language_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/settings/{user_id}/{language_id}")
            return resp.json() if resp.is_success else {}

    async def get_or_create_user(
        self, telegram_id: int, username: Optional[str], first_name: str
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/user/get_or_create", json={
                "telegram_id": telegram_id,
                "username": username,
                "first_name": first_name,
            })
            return resp.json() if resp.is_success else {}

    # ── Session — all return {session_id, card} ───────────────────────────────

    async def start_session(
        self, user_id: str, language_id: str,
        settings: Optional[Dict[str, Any]] = None,
        session_mode: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {"user_id": user_id, "language_id": language_id}
        if settings:
            payload["settings"] = settings
        if session_mode:
            payload["session_mode"] = session_mode
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/session/start", json=payload)
            return resp.json() if resp.is_success else None

    async def get_session(self, user_id: str, language_id: str) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/session/{user_id}/{language_id}")
            return resp.json() if resp.is_success else None

    async def show_answer(self, session_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/session/{session_id}/show_answer")
            return resp.json() if resp.is_success else {}

    async def rate_word(self, session_id: str, rating: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/session/{session_id}/rate",
                                     json={"rating": rating})
            return resp.json() if resp.is_success else {}

    async def know_word(self, session_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/session/{session_id}/know")
            return resp.json() if resp.is_success else {}

    async def reconsider(self, session_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/session/{session_id}/reconsider")
            return resp.json() if resp.is_success else {}

    async def toggle_skip(self, session_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/session/{session_id}/toggle_skip")
            return resp.json() if resp.is_success else {}

    async def get_progress(self, session_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/session/{session_id}/progress")
            return resp.json() if resp.is_success else {}

    async def next_batch(self, session_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/session/{session_id}/next_batch", json={})
            return resp.json() if resp.is_success else {"loaded": False}

    async def pick_answer(self, session_id: str, selected_word_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/session/{session_id}/pick_answer",
                json={"selected_word_id": selected_word_id},
            )
            return resp.json() if resp.is_success else {}

    async def add_forbidden_pair(self, session_id: str, bad_word_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/session/{session_id}/add_forbidden_pair",
                json={"bad_word_id": bad_word_id},
            )
            return resp.json() if resp.is_success else {}

    async def clear_forbidden_pairs(self, session_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/session/{session_id}/clear_forbidden_pairs",
                json={},
            )
            return resp.json() if resp.is_success else {}

    async def end_session(self, user_id: str, language_id: str) -> None:
        async with httpx.AsyncClient() as client:
            await client.delete(f"{self.base_url}/session/{user_id}/{language_id}")

    # ── Auth ─────────────────────────────────────────────────────────────────

    async def is_admin(self, user_id: str) -> bool:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/user/{user_id}/is_admin")
            return (resp.json() or {}).get("is_admin", False) if resp.is_success else False

    async def auth_lookup(self, mode: str, telegram_id: int = None, name: str = None,
                          direct: bool = False) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"mode": mode}
        if telegram_id is not None:
            payload["telegram_id"] = telegram_id
        if name is not None:
            payload["name"] = name
        if direct:
            payload["direct"] = True
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/auth/lookup", json=payload)
            return resp.json() if resp.is_success else {}

    async def auth_create(self, mode: str, first_name: str, telegram_id: int = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"mode": mode, "first_name": first_name}
        if telegram_id is not None:
            payload["telegram_id"] = telegram_id
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/auth/create", json=payload)
            return resp.json() if resp.is_success else {}

    async def auth_status(self, token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/auth/status/{token}")
            return resp.json() if resp.is_success else {"status": "error"}

    async def get_user_first_name(self, user_id: str) -> str:
        """Return user's first_name by user_id, or empty string if unavailable."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/admin/users/{user_id}",
                                        params={"user_id": user_id})
                if resp.is_success:
                    return resp.json().get("first_name", "") or ""
            except Exception:
                pass
        return ""

    async def mobile_create_token(self, user_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/auth/mobile/create",
                                     json={"user_id": user_id})
            return resp.json() if resp.is_success else {}

    async def mobile_activate_token(self, code: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/auth/mobile/activate",
                                     json={"code": code})
            return resp.json() if resp.is_success else {}

    # ── Admin ─────────────────────────────────────────────────────────────────

    async def admin_global_stats(self, user_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/admin/stats", params={"user_id": user_id})
            return resp.json() if resp.is_success else {}

    async def admin_list_users(self, user_id: str, page: int = 1) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/admin/users",
                                    params={"user_id": user_id, "page": page})
            return resp.json() if resp.is_success else {}

    async def admin_user_details(self, user_id: str, target_user_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/admin/users/{target_user_id}",
                                    params={"user_id": user_id})
            return resp.json() if resp.is_success else {}

    async def admin_toggle_admin(self, user_id: str, target_user_id: str, is_admin: bool) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/admin/users/{target_user_id}/toggle_admin",
                                     params={"user_id": user_id}, json={"is_admin": is_admin})
            return resp.json() if resp.is_success else {}

    async def admin_create_language(self, user_id: str, name_ru: str, name_foreign: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/admin/languages",
                                     params={"user_id": user_id},
                                     json={"name_ru": name_ru, "name_foreign": name_foreign})
            return resp.json() if resp.is_success else {}

    async def admin_update_language(self, user_id: str, language_id: str,
                                    name_ru: str, name_foreign: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.put(f"{self.base_url}/admin/languages/{language_id}",
                                    params={"user_id": user_id},
                                    json={"name_ru": name_ru, "name_foreign": name_foreign})
            return resp.json() if resp.is_success else {}

    async def admin_delete_language(self, user_id: str, language_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.delete(f"{self.base_url}/admin/languages/{language_id}",
                                       params={"user_id": user_id})
            return resp.json() if resp.is_success else {}

    async def admin_language_detail(self, user_id: str, language_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/admin/languages/{language_id}",
                                    params={"user_id": user_id})
            return resp.json() if resp.is_success else {}

    async def admin_list_words(self, user_id: str, language_id: str, page: int = 1) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/admin/languages/{language_id}/words",
                                    params={"user_id": user_id, "page": page})
            return resp.json() if resp.is_success else {}

    async def admin_word_by_number(self, user_id: str, language_id: str, number: int) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/admin/languages/{language_id}/words/by_number/{number}",
                params={"user_id": user_id})
            return resp.json() if resp.is_success else {}

    async def admin_update_word(self, user_id: str, word_id: str, field: str, value: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.patch(f"{self.base_url}/admin/words/{word_id}",
                                      params={"user_id": user_id},
                                      json={"field": field, "value": value})
            return resp.json() if resp.is_success else {}

    async def admin_delete_word(self, user_id: str, word_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.delete(f"{self.base_url}/admin/words/{word_id}",
                                       params={"user_id": user_id})
            return resp.json() if resp.is_success else {}

    async def admin_export_words(self, user_id: str, language_id: str,
                                 fmt: str = "xlsx", start: int = None, end: int = None) -> Optional[bytes]:
        params: Dict[str, Any] = {"user_id": user_id, "format": fmt}
        if start is not None:
            params["start"] = start
        if end is not None:
            params["end"] = end
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(f"{self.base_url}/admin/languages/{language_id}/export",
                                    params=params)
            return resp.content if resp.is_success else None

    async def admin_import_words(self, user_id: str, language_id: str,
                                 file_data: bytes, filename: str,
                                 clear_existing: bool = False) -> Dict[str, Any]:
        params = {"user_id": user_id, "clear_existing": str(clear_existing).lower()}
        files = {"file": (filename, file_data)}
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.base_url}/admin/languages/{language_id}/import",
                                     params=params, files=files)
            return resp.json() if resp.is_success else {"ok": False, "error": resp.text}

    # ── Hints ─────────────────────────────────────────────────────────────────

    async def get_word_hints(self, user_id: str, word_id: str) -> Dict[str, str]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/hints/{user_id}/{word_id}")
            return resp.json() if resp.is_success else {}

    async def set_word_hint(
        self, user_id: str, word_id: str,
        hint_type: str, text: str,
        language_id: Optional[str] = None,
    ) -> bool:
        payload: Dict[str, Any] = {"hint_type": hint_type, "text": text}
        if language_id:
            payload["language_id"] = language_id
        async with httpx.AsyncClient() as client:
            resp = await client.put(f"{self.base_url}/hints/{user_id}/{word_id}", json=payload)
            return bool((resp.json() or {}).get("ok")) if resp.is_success else False

    async def delete_word_hint(self, user_id: str, word_id: str, hint_type: str) -> bool:
        async with httpx.AsyncClient() as client:
            resp = await client.delete(f"{self.base_url}/hints/{user_id}/{word_id}/{hint_type}")
            return bool((resp.json() or {}).get("ok")) if resp.is_success else False

    # ── Settings ─────────────────────────────────────────────────────────────

    async def get_settings(self, user_id: str, language_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/settings/{user_id}/{language_id}")
            return resp.json() if resp.is_success else {}

    async def get_hint_settings(self, user_id: str, language_id: str) -> Dict[str, bool]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/settings/{user_id}/{language_id}/hints")
            return resp.json() if resp.is_success else {}

    async def toggle_setting(self, user_id: str, language_id: str, key: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/settings/{user_id}/{language_id}/{key}/toggle")
            return resp.json() if resp.is_success else {}

    async def set_setting(self, user_id: str, language_id: str, key: str, value) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{self.base_url}/settings/{user_id}/{language_id}/{key}",
                json={"value": value},
            )
            return resp.json() if resp.is_success else {}

    # ── Other ─────────────────────────────────────────────────────────────────

    async def get_languages(self) -> list:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/languages/")
            return resp.json() if resp.is_success else []

    async def get_statistics(self, user_id: str, language_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/statistics/{user_id}/{language_id}")
            return resp.json() if resp.is_success else {}

    async def get_chart_manifest(self) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/statistics/chart_manifest")
            return resp.json() if resp.is_success else {}

    async def get_chart(self, user_id: str, language_id: str, chart_name: str) -> Optional[bytes]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/statistics/{user_id}/{language_id}/chart/{chart_name}"
            )
            return resp.content if resp.is_success else None

    async def get_monthly_chart(self, user_id: str, language_id: str, chart_name: str, show_all: bool = True) -> Optional[bytes]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/statistics/{user_id}/{language_id}/monthly-chart/{chart_name}",
                params={"show_all": str(show_all).lower()},
            )
            return resp.content if resp.is_success else None


_client: Optional[BLSClient] = None


def get_bls_client() -> BLSClient:
    global _client
    if _client is None:
        _client = BLSClient()
    return _client
