"""
Admin business logic — stats, user management, language/word CRUD, export/import.
All functions delegate to the backend API client; no DB access here.
"""

from typing import Dict, Any, List, Optional
from app.logger import setup_logger

logger = setup_logger(__name__)

PER_PAGE = 20


# ── Global stats ──────────────────────────────────────────────────────────────

async def get_global_stats(api_client) -> Dict[str, Any]:
    """Return bot-wide statistics: user count, per-language word/user counts."""
    users_resp = await api_client.get_users_count()
    total_users = (users_resp.get("result") or {}).get("count", 0) if users_resp.get("success") else 0

    langs_resp = await api_client.get_languages()
    languages = langs_resp.get("result") or [] if langs_resp.get("success") else []

    lang_stats = []
    for lang in languages:
        lang_id = lang.get("id")
        wc_resp = await api_client.get_word_count_by_language(lang_id)
        word_count = (wc_resp.get("result") or {}).get("count", 0) if wc_resp.get("success") else 0
        au_resp = await api_client.get_language_active_users(lang_id)
        active_users = (au_resp.get("result") or {}).get("count", 0) if au_resp.get("success") else 0
        lang_stats.append({
            "id": lang_id,
            "name_ru": lang.get("name_ru", ""),
            "name_foreign": lang.get("name_foreign", ""),
            "word_count": word_count,
            "active_users": active_users,
        })

    return {"total_users": total_users, "languages": lang_stats}


# ── User management ───────────────────────────────────────────────────────────

async def get_users_page(page: int, api_client) -> Dict[str, Any]:
    """Return a page of users with pagination metadata."""
    skip = (page - 1) * PER_PAGE
    resp = await api_client.get_users(skip=skip, limit=PER_PAGE)
    users = resp.get("result") or [] if resp.get("success") else []

    count_resp = await api_client.get_users_count()
    total = (count_resp.get("result") or {}).get("count", 0) if count_resp.get("success") else 0

    return {
        "users": users,
        "page": page,
        "per_page": PER_PAGE,
        "total": total,
        "total_pages": max(1, (total + PER_PAGE - 1) // PER_PAGE),
    }


async def get_user_details(user_id: str, api_client) -> Dict[str, Any]:
    """Return user info + their progress across all languages."""
    langs_resp = await api_client.get_languages()
    languages = langs_resp.get("result") or [] if langs_resp.get("success") else []

    progress_list = []
    for lang in languages:
        lang_id = lang.get("id")
        prog_resp = await api_client.get_user_progress(user_id, lang_id)
        if prog_resp.get("success") and prog_resp.get("result"):
            p = prog_resp["result"]
            if p.get("words_studied", 0) > 0:
                progress_list.append({
                    "language_id": lang_id,
                    "name_ru": lang.get("name_ru", ""),
                    "name_foreign": lang.get("name_foreign", ""),
                    **p,
                })

    return {"user_id": user_id, "progress": progress_list}


async def toggle_admin(user_id: str, current_is_admin: bool, api_client) -> bool:
    """Toggle admin rights for a user. Returns new value."""
    new_value = not current_is_admin
    resp = await api_client.update_user(user_id, {"is_admin": new_value})
    return resp.get("success", False)


# ── Language management ───────────────────────────────────────────────────────

async def create_language(name_ru: str, name_foreign: str, api_client) -> Dict[str, Any]:
    resp = await api_client.create_language({"name_ru": name_ru, "name_foreign": name_foreign})
    return {"ok": resp.get("success", False), "result": resp.get("result")}


async def update_language(language_id: str, name_ru: str, name_foreign: str, api_client) -> bool:
    resp = await api_client.update_language(language_id, {"name_ru": name_ru, "name_foreign": name_foreign})
    return resp.get("success", False)


async def delete_language(language_id: str, api_client) -> bool:
    resp = await api_client.delete_language(language_id)
    return resp.get("success", False)


async def get_language_with_stats(language_id: str, api_client) -> Optional[Dict[str, Any]]:
    lang_resp = await api_client.get_language(language_id)
    if not lang_resp.get("success"):
        return None
    lang = lang_resp["result"]
    wc_resp = await api_client.get_word_count_by_language(language_id)
    lang["word_count"] = (wc_resp.get("result") or {}).get("count", 0) if wc_resp.get("success") else 0
    return lang


# ── Word management ───────────────────────────────────────────────────────────

async def get_words_page(language_id: str, page: int, api_client) -> Dict[str, Any]:
    skip = (page - 1) * PER_PAGE
    resp = await api_client.get_words_by_language(language_id, skip=skip, limit=PER_PAGE)
    words = resp.get("result") or [] if resp.get("success") else []
    wc_resp = await api_client.get_word_count_by_language(language_id)
    total = (wc_resp.get("result") or {}).get("count", 0) if wc_resp.get("success") else 0
    return {
        "words": words,
        "page": page,
        "per_page": PER_PAGE,
        "total": total,
        "total_pages": max(1, (total + PER_PAGE - 1) // PER_PAGE),
    }


async def get_word_by_number(language_id: str, number: int, api_client) -> Optional[Dict[str, Any]]:
    resp = await api_client.get_word_by_number(language_id, number)
    if not resp.get("success"):
        return None
    result = resp.get("result")
    if isinstance(result, list):
        return result[0] if result else None
    return result


async def update_word_field(word_id: str, field: str, value: str, api_client) -> bool:
    resp = await api_client.update_word(word_id, {field: value})
    return resp.get("success", False)


async def delete_word(word_id: str, api_client) -> bool:
    resp = await api_client.delete_word(word_id)
    return resp.get("success", False)


# ── Export ────────────────────────────────────────────────────────────────────

async def export_words(
    language_id: str,
    fmt: str,
    start_word: Optional[int],
    end_word: Optional[int],
    api_client,
) -> Optional[bytes]:
    resp = await api_client.export_words_by_language(
        language_id, format=fmt, start_word=start_word, end_word=end_word
    )
    if resp.get("success") and resp.get("result"):
        return resp["result"]
    return None


# ── Import ────────────────────────────────────────────────────────────────────

async def import_words(
    language_id: str,
    file_data: bytes,
    file_name: str,
    params: Dict[str, Any],
    api_client,
) -> Dict[str, Any]:
    resp = await api_client.upload_words_file(language_id, file_data, file_name, params)
    return {"ok": resp.get("success", False), "result": resp.get("result"), "error": resp.get("error")}
