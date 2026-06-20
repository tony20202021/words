"""
Settings business logic — no aiogram dependencies.
"""

from typing import Dict, Any, Optional
from app.logger import setup_logger

logger = setup_logger(__name__)

DEFAULT_SETTINGS: Dict[str, Any] = {
    "start_word": 1,
    "skip_marked": True,
    "use_check_date": True,
    "show_check_date": True,
    "show_debug": False,
    "show_charts": False,
    "show_hint_meaning": False,
    "show_hint_phoneticassociation": False,
    "show_hint_phoneticsound": False,
    "show_hint_writing": False,
    "show_big": True,
    "show_short_captions": True,
    "show_writing_images": False,
    "show_radicals": True,
    "show_references": True,
    "show_tones": True,
    "show_sounds": True,
    "show_skip_button": True,
    "random_foreign": True,
    "random_transcription": True,
    "random_sound": False,
    "receive_messages": True,
    "reset_same_day_hours": 16,
    "reset_cross_midnight_hours": 6,
    "unknown_limit_new_words": 10,
    "max_check_interval": 32,
}

DEFAULT_HINT_SETTINGS: Dict[str, bool] = {
    "show_hint_meaning": True,
    "show_hint_phoneticassociation": True,
    "show_hint_phoneticsound": True,
    "show_hint_writing": True,
}


async def get_settings(user_id: str, language_id: str, api_client) -> Dict[str, Any]:
    """Return user settings for a language, falling back to defaults."""
    if not user_id or not language_id:
        return DEFAULT_SETTINGS.copy()

    response = await api_client.get_user_language_settings(user_id, language_id)
    if response["success"] and response["result"]:
        settings = response["result"]
        for key, default in DEFAULT_SETTINGS.items():
            settings.setdefault(key, default)
        return settings

    return DEFAULT_SETTINGS.copy()


async def save_settings(
    user_id: str, language_id: str, settings: Dict[str, Any], api_client
) -> bool:
    """Persist settings via backend API."""
    if not user_id or not language_id:
        return False
    response = await api_client.update_user_language_settings(user_id, language_id, settings)
    if not response["success"]:
        logger.error(f"Failed to save settings user={user_id} lang={language_id}: {response.get('error')}")
    return response["success"]


async def toggle_setting(
    user_id: str, language_id: str, key: str, api_client
) -> Dict[str, Any]:
    """Toggle a boolean setting; return updated settings dict."""
    settings = await get_settings(user_id, language_id, api_client)
    current = settings.get(key, DEFAULT_SETTINGS.get(key, False))
    settings[key] = not current
    await save_settings(user_id, language_id, settings, api_client)
    return settings


async def get_hint_settings(user_id: str, language_id: str, api_client) -> Dict[str, bool]:
    """Return only the hint-related settings."""
    from app.hint_constants import HINT_SETTING_KEYS
    settings = await get_settings(user_id, language_id, api_client)
    return {k: settings.get(k, DEFAULT_HINT_SETTINGS.get(k, True)) for k in HINT_SETTING_KEYS}


async def toggle_hint(
    user_id: str, language_id: str, hint_key: str, api_client
) -> Dict[str, bool]:
    """Toggle a specific hint setting; return updated hint settings."""
    settings = await toggle_setting(user_id, language_id, hint_key, api_client)
    from app.hint_constants import HINT_SETTING_KEYS
    return {k: settings.get(k, True) for k in HINT_SETTING_KEYS}
