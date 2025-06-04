"""
Utilities for admin rights checking and management.
Переиспользует существующую логику из AuthMiddleware и admin handlers.
"""

from typing import Union, Optional, Tuple
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def is_user_admin(
    message_or_callback: Union[Message, CallbackQuery], 
    state: FSMContext
) -> bool:
    """
    Проверяет, является ли пользователь администратором.
    Переиспользует логику из AuthMiddleware и admin_basic_handlers.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM state context
        
    Returns:
        bool: True если пользователь админ, False иначе
    """
    try:
        # Сначала проверяем данные состояния (быстрая проверка)
        state_data = await state.get_data()
        is_admin_cached = state_data.get("is_admin")

        logger.info(f"is_admin_cached={is_admin_cached}")

        if is_admin_cached is not None:
            logger.debug(f"Admin status from state cache: {is_admin_cached}")
            return is_admin_cached
        
        # Если в состоянии нет данных - проверяем через API
        user_id = message_or_callback.from_user.id
        is_admin = await get_user_admin_status(message_or_callback.bot, user_id)
        logger.info(f"user_id={user_id}")
        logger.info(f"is_admin={is_admin}")
        
        # Сохраняем результат в состоянии для кэширования
        await state.update_data(is_admin=is_admin)
        
        return is_admin
        
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False


async def get_user_admin_status(bot, telegram_id: int) -> bool:
    """
    Получает статус администратора пользователя через API.
    
    Args:
        bot: Bot instance
        telegram_id: Telegram ID пользователя
        
    Returns:
        bool: True если пользователь админ, False иначе
    """
    try:
        # Получаем API клиент
        api_client = get_api_client_from_bot(bot)
        if not api_client:
            logger.error("API client not available for admin check")
            return False
        
        # Получаем пользователя из API 
        user_response = await api_client.get_user_by_telegram_id(telegram_id)
        
        if not user_response["success"]:
            logger.warning(f"Failed to get user data for admin check: {user_response.get('error')}")
            return False
        
        users = user_response["result"]
        user = users[0] if users and isinstance(users, list) and len(users) > 0 else None
        
        if not user:
            logger.debug(f"User {telegram_id} not found in database")
            return False
        
        is_admin = user.get("is_admin", False)
        logger.debug(f"User {telegram_id} admin status: {is_admin}")
        
        return is_admin
        
    except Exception as e:
        logger.error(f"Error getting user admin status: {e}")
        return False


# Экспорт основных функций
__all__ = [
    'is_user_admin',
    'get_user_admin_status', 
]
