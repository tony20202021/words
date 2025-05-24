"""
Enhanced authentication middleware for the Telegram bot.
This middleware handles user authentication, admin rights checking, and session management.
"""

import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject, User

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Enhanced middleware for user authentication and session management."""
    
    def __init__(self, check_admin_for_patterns: Optional[list] = None):
        """
        Initialize auth middleware.
        
        Args:
            check_admin_for_patterns: List of callback patterns that require admin rights
        """
        self.admin_patterns = check_admin_for_patterns or [
            "admin_",
            "create_language",
            "edit_language_",
            "delete_language_",
            "upload_to_lang_",
            "confirm_delete_",
            "column_template_",
        ]
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Process update before handling it.
        
        Args:
            handler: The event handler.
            event: The event to be processed.
            data: Additional data to be passed to the handler.
            
        Returns:
            The result of the handler call.
        """
        # Get user from the event
        user = self._extract_user(event)
        
        if user:
            # Log user activity
            logger.info(f"User {user.full_name} ({user.id}) is using the bot")
            
            # Add user to data
            data["user"] = user
            
            # Get API client and add to data
            bot = data.get("bot")
            if bot:
                api_client = get_api_client_from_bot(bot)
                if api_client:
                    data["api_client"] = api_client
                    
                    # Get or create user in database
                    db_user = await self._get_or_create_user(user, api_client)
                    if db_user:
                        data["db_user"] = db_user
                        data["db_user_id"] = db_user.get("id")
                        data["is_admin"] = db_user.get("is_admin", False)
            
            # Check admin rights for admin callbacks
            if isinstance(event, CallbackQuery) and self._requires_admin_rights(event):
                is_admin = data.get("is_admin", False)
                if not is_admin:
                    await event.answer("❌ Недостаточно прав для выполнения данного действия", show_alert=True)
                    return
        
        # Call the next handler
        return await handler(event, data)
    
    def _extract_user(self, event: TelegramObject) -> Optional[User]:
        """
        Extract user from event.
        
        Args:
            event: The telegram event
            
        Returns:
            User object or None
        """
        if isinstance(event, (Message, CallbackQuery)):
            return event.from_user
        
        # Try to get user from other event types
        return getattr(event, "from_user", None)
    
    def _requires_admin_rights(self, event: CallbackQuery) -> bool:
        """
        Check if callback requires admin rights.
        
        Args:
            event: The callback query event
            
        Returns:
            True if admin rights are required
        """
        if not event.data:
            return False
        
        # Check if callback data matches any admin pattern
        for pattern in self.admin_patterns:
            if event.data.startswith(pattern):
                return True
        
        return False
    
    async def _get_or_create_user(self, user: User, api_client) -> Optional[Dict]:
        """
        Get or create user in the database.
        
        Args:
            user: The Telegram user
            api_client: The API client for database operations
            
        Returns:
            User data from database or None if error
        """
        try:
            # Try to get existing user
            user_response = await api_client.get_user_by_telegram_id(user.id)
            
            if user_response["success"] and user_response["result"]:
                # User exists, return first result
                users = user_response["result"]
                db_user = users[0] if users else None
                
                if db_user:
                    logger.debug(f"Found existing user: {db_user.get('id')}")
                    return db_user
            
            # User doesn't exist, create new one
            user_data = {
                "telegram_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name
            }
            
            create_response = await api_client.create_user(user_data)
            
            if create_response["success"] and create_response["result"]:
                db_user = create_response["result"]
                logger.info(f"Created new user: {db_user.get('id')} for Telegram ID {user.id}")
                return db_user
            else:
                logger.error(f"Failed to create user: {create_response.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error in _get_or_create_user: {e}", exc_info=True)
            return None


class AdminOnlyMiddleware(BaseMiddleware):
    """Middleware that restricts access to admin-only handlers."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Check if user is admin before allowing access.
        
        Args:
            handler: The event handler
            event: The event to be processed
            data: Additional data passed to the handler
            
        Returns:
            The result of the handler call or None if access denied
        """
        is_admin = data.get("is_admin", False)
        
        if not is_admin:
            # Send appropriate error message
            if isinstance(event, Message):
                await event.answer("❌ Эта команда доступна только администраторам")
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ Недостаточно прав", show_alert=True)
            
            return
        
        # User is admin, proceed with handler
        return await handler(event, data)


class UserRegistrationMiddleware(BaseMiddleware):
    """Middleware that ensures user is registered in the database."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Ensure user is registered before handling the event.
        
        Args:
            handler: The event handler
            event: The event to be processed
            data: Additional data passed to the handler
            
        Returns:
            The result of the handler call
        """
        db_user_id = data.get("db_user_id")
        
        if not db_user_id:
            # User not registered, send error
            if isinstance(event, Message):
                await event.answer(
                    "❌ Ошибка регистрации пользователя. Попробуйте команду /start"
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ Ошибка регистрации", show_alert=True)
            
            return
        
        # User is registered, proceed
        return await handler(event, data)
    