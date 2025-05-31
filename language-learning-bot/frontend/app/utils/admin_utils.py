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
    Переиспользует логику из handle_admin_mode.
    
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
        
        # Получаем пользователя из API (используем ту же логику что в handle_admin_mode)
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


async def ensure_user_admin_rights(
    message_or_callback: Union[Message, CallbackQuery],
    state: FSMContext,
    error_message: str = "У вас нет прав администратора."
) -> bool:
    """
    Проверяет права администратора и отправляет ошибку если прав нет.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM state context
        error_message: Сообщение об ошибке для отправки пользователю
        
    Returns:
        bool: True если пользователь админ, False иначе
    """
    is_admin = await is_user_admin(message_or_callback, state)
    
    if not is_admin:
        # Отправляем сообщение об ошибке
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.answer("❌ Недостаточно прав", show_alert=True)
            await message_or_callback.message.answer(error_message)
        else:
            await message_or_callback.answer(error_message)
        
        # Логируем попытку несанкционированного доступа
        user = message_or_callback.from_user
        logger.warning(
            f"Unauthorized admin access attempt by user {user.id} "
            f"({user.username or user.full_name})"
        )
    
    return is_admin


async def get_user_and_admin_info(
    message_or_callback: Union[Message, CallbackQuery],
    state: FSMContext
) -> Tuple[Optional[str], bool]:
    """
    Получает ID пользователя в БД и статус администратора.
    Полезно когда нужны оба значения одновременно.
    
    Args:
        message_or_callback: Message or CallbackQuery object
        state: FSM state context
        
    Returns:
        Tuple[Optional[str], bool]: (db_user_id, is_admin)
    """
    try:
        state_data = await state.get_data()
        db_user_id = state_data.get("db_user_id")
        is_admin = state_data.get("is_admin")
        
        # Если есть кэшированные данные - используем их
        if db_user_id is not None and is_admin is not None:
            return db_user_id, is_admin
        
        # Иначе получаем через API
        telegram_id = message_or_callback.from_user.id
        api_client = get_api_client_from_bot(message_or_callback.bot)
        
        if not api_client:
            return None, False
        
        user_response = await api_client.get_user_by_telegram_id(telegram_id)
        
        if not user_response["success"] or not user_response["result"]:
            return None, False
        
        users = user_response["result"]
        user = users[0] if users and len(users) > 0 else None
        
        if not user:
            return None, False
        
        db_user_id = user.get("id")
        is_admin = user.get("is_admin", False)
        
        # Обновляем кэш в состоянии
        await state.update_data(
            db_user_id=db_user_id,
            is_admin=is_admin
        )
        
        return db_user_id, is_admin
        
    except Exception as e:
        logger.error(f"Error getting user and admin info: {e}")
        return None, False


# Декоратор для обработчиков, требующих прав администратора
def admin_required(error_message: str = "Требуются права администратора"):
    """
    Декоратор для проверки прав администратора в обработчиках.
    
    Args:
        error_message: Сообщение об ошибке при отсутствии прав
    """
    def decorator(handler_func):
        async def wrapper(message_or_callback, state: FSMContext, *args, **kwargs):
            if not await ensure_user_admin_rights(message_or_callback, state, error_message):
                return  # Прерываем выполнение если не админ
            
            return await handler_func(message_or_callback, state, *args, **kwargs)
        
        return wrapper
    return decorator


# Экспорт основных функций
__all__ = [
    'is_user_admin',
    'get_user_admin_status', 
    'ensure_user_admin_rights',
    'get_user_and_admin_info',
    'admin_required'
]
