"""
Telegram-based and name-based web auth.

Telegram flow:
  1. Web calls lookup_telegram(telegram_id) → {found, token?, user_id?}
  2. If found: BLS sends Telegram message; web polls status/{token}
  3. Bot calls confirm_token(token) / deny_token(token)

Name flow:
  1. Web calls lookup_name(name) → {found, user_id?, users?}
  2. If found: web logs in directly (no confirmation needed)
"""

import uuid
import time
import random
import os
from typing import Optional, List, Dict, Any
from app.logger import setup_logger

logger = setup_logger(__name__)

TOKEN_TTL = 300  # 5 minutes
MOBILE_TOKEN_TTL = 600  # 10 minutes

# token → {telegram_id, expires_at, status: pending|confirmed|denied|expired, user_id}
_tokens: dict = {}

# 6-char code → {user_id, expires_at}
_mobile_tokens: dict = {}


# ── Mobile token (Android) ────────────────────────────────────────────────────

def create_mobile_token(user_id: str) -> str:
    """Generate a short 6-char alphanumeric code for Android login."""
    _cleanup_expired()
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I to avoid confusion
    code = "".join(random.choices(alphabet, k=6))
    _mobile_tokens[code] = {"user_id": user_id, "expires_at": time.time() + MOBILE_TOKEN_TTL}
    logger.info(f"Mobile token created for user_id={user_id}")
    return code


def activate_mobile_token(code: str) -> Optional[str]:
    """Exchange code for user_id. Single-use."""
    entry = _mobile_tokens.pop(code.upper(), None)
    if not entry:
        return None
    if time.time() > entry["expires_at"]:
        return None
    logger.info(f"Mobile token activated for user_id={entry['user_id']}")
    return entry["user_id"]


# ── Token store ───────────────────────────────────────────────────────────────

def create_token(telegram_id: int, user_id: str, first_name: str = "") -> str:
    _cleanup_expired()
    token = str(uuid.uuid4())
    _tokens[token] = {
        "telegram_id": telegram_id,
        "expires_at": time.time() + TOKEN_TTL,
        "status": "pending",
        "user_id": user_id,
        "first_name": first_name,
    }
    logger.info(f"Auth token created for telegram_id={telegram_id}")
    return token


def confirm_token(token: str) -> bool:
    entry = _tokens.get(token)
    if not entry:
        return False
    if entry["status"] != "pending" or time.time() > entry["expires_at"]:
        entry["status"] = "expired"
        return False
    entry["status"] = "confirmed"
    logger.info(f"Auth token confirmed telegram_id={entry['telegram_id']}")
    return True


def deny_token(token: str) -> bool:
    entry = _tokens.get(token)
    if not entry or entry["status"] != "pending":
        return False
    entry["status"] = "denied"
    logger.info(f"Auth token denied telegram_id={entry['telegram_id']}")
    return True


def get_token_entry(token: str) -> Optional[dict]:
    entry = _tokens.get(token)
    if not entry:
        return None
    if entry["status"] == "pending" and time.time() > entry["expires_at"]:
        entry["status"] = "expired"
    return entry


def _cleanup_expired() -> None:
    now = time.time()
    stale = [t for t, e in _tokens.items() if now > e["expires_at"] + 60]
    for t in stale:
        del _tokens[t]
    stale_m = [c for c, e in _mobile_tokens.items() if now > e["expires_at"] + 60]
    for c in stale_m:
        del _mobile_tokens[c]


# ── Telegram lookup & messaging ───────────────────────────────────────────────

async def lookup_telegram(telegram_id: int, api_client) -> Dict[str, Any]:
    """
    Look up user by telegram_id.
    Returns {found, user_id?, first_name?}.
    """
    response = await api_client.get_user_by_telegram_id(telegram_id)
    if not response or not response.get("success"):
        return {"found": False}
    users = response.get("result") or []
    if isinstance(users, list) and users:
        u = users[0]
        return {"found": True, "user_id": u.get("id"), "first_name": u.get("first_name", "")}
    if isinstance(users, dict) and users.get("id"):
        return {"found": True, "user_id": users.get("id"), "first_name": users.get("first_name", "")}
    return {"found": False}


async def send_auth_request(telegram_id: int, token: str) -> bool:
    """Send confirmation message via Telegram Bot API."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — cannot send auth message")
        return False

    import httpx
    text = (
        "🔐 <b>Запрос авторизации в веб-приложении</b>\n\n"
        "Кто-то пытается войти, используя ваш Telegram ID.\n"
        "Если это вы — нажмите <b>✅ Да</b>.\n"
        "Если нет — нажмите <b>❌ Нет</b>.\n\n"
        "<i>Запрос истекает через 5 минут.</i>"
    )
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Да", "callback_data": f"auth:confirm:{token}"},
            {"text": "❌ Нет", "callback_data": f"auth:deny:{token}"},
        ]]
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": telegram_id, "text": text,
                      "parse_mode": "HTML", "reply_markup": keyboard},
            )
        if resp.is_success and resp.json().get("ok"):
            logger.info(f"Auth message sent to telegram_id={telegram_id}")
            return True
        logger.error(f"Telegram API error: {resp.text}")
        return False
    except Exception as e:
        logger.error(f"Failed to send auth message: {e}")
        return False


# ── Name lookup ───────────────────────────────────────────────────────────────

async def lookup_name(username: str, api_client) -> Dict[str, Any]:
    """
    Search users by Telegram username (case-insensitive, with or without @).
    Returns {found, user_id?, first_name?} or {found: 'multiple', users: [...]}.
    """
    response = await api_client.get_users(limit=1000)
    if not response or not response.get("success"):
        return {"found": False}

    all_users: List[dict] = response.get("result") or []
    query = username.strip().lstrip("@").lower()
    matches = [
        u for u in all_users
        if query == (u.get("username") or "").strip().lstrip("@").lower()
    ]

    if len(matches) == 1:
        u = matches[0]
        return {"found": True, "user_id": u.get("id"), "first_name": u.get("first_name", "")}
    if len(matches) > 1:
        return {
            "found": "multiple",
            "users": [{"id": u.get("id"), "first_name": u.get("first_name", "")} for u in matches],
        }
    return {"found": False}


# ── User creation ─────────────────────────────────────────────────────────────

def _generate_pseudo_telegram_id() -> int:
    """Generate a large random int that won't clash with real Telegram IDs (< ~8B)."""
    return random.randint(10**15, 9 * 10**15)


async def create_user_by_name(username: str, api_client) -> Dict[str, Any]:
    """Create a user with username only (no real Telegram account)."""
    pseudo_id = _generate_pseudo_telegram_id()
    clean_username = username.strip().lstrip("@")
    from app.services.user_service import get_or_create_user
    user_id, user_data = await get_or_create_user(
        pseudo_id, username=clean_username, first_name=clean_username, last_name=None,
        api_client=api_client
    )
    if not user_id:
        return {"ok": False}
    return {"ok": True, "user_id": user_id, "first_name": clean_username}


async def create_user_by_telegram(telegram_id: int, first_name: str, api_client) -> Dict[str, Any]:
    """Create a new user with telegram_id + name, then send auth confirmation."""
    from app.services.user_service import get_or_create_user
    user_id, _ = await get_or_create_user(
        telegram_id, username=None, first_name=first_name, last_name=None, api_client=api_client
    )
    if not user_id:
        return {"ok": False}
    token = create_token(telegram_id, user_id, first_name=first_name)
    message_sent = await send_auth_request(telegram_id, token)
    return {"ok": True, "user_id": user_id, "token": token, "message_sent": message_sent}
