"""
User business logic — no aiogram dependencies.
"""

from typing import Optional, Tuple, Dict, Any
from app.logger import setup_logger

logger = setup_logger(__name__)


async def get_or_create_user(
    telegram_id: int,
    username: Optional[str],
    first_name: str,
    last_name: Optional[str],
    api_client,
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Get existing user or create a new one.

    Returns:
        (db_user_id, user_data) or (None, None) on failure.
    """
    response = await api_client.get_user_by_telegram_id(telegram_id)
    if not response["success"]:
        logger.error(f"Failed to get user telegram_id={telegram_id}: {response['error']}")
        return None, None

    users = response["result"]
    user_data = users[0] if users and isinstance(users, list) else None

    if user_data:
        return user_data.get("id"), user_data

    create_response = await api_client.create_user({
        "telegram_id": telegram_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
    })
    if not create_response["success"]:
        logger.error(f"Failed to create user telegram_id={telegram_id}: {create_response['error']}")
        return None, None

    user_data = create_response["result"]
    return (user_data.get("id") if user_data else None), user_data


async def is_admin(user_id: str, api_client) -> bool:
    """Check admin status for a db user_id."""
    try:
        response = await api_client.get_user(user_id)
        if not response["success"] or not response["result"]:
            return False
        return response["result"].get("is_admin", False)
    except Exception as e:
        logger.error(f"Error checking admin status user_id={user_id}: {e}")
        return False
