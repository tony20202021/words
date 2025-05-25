"""
Enhanced authentication middleware for the Telegram bot.
This middleware handles user authentication, admin rights checking, session management,
and automatic transitions to meta-states for error handling.
"""

import logging
from typing import Any, Awaitable, Callable, Dict, Optional
from datetime import datetime

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject, User
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.bot.states.centralized_states import CommonStates
from app.utils.error_utils import handle_api_error, handle_unknown_command, is_command

logger = setup_logger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Enhanced middleware for user authentication and session management with meta-state support."""
    
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
        Enhanced with meta-state transitions and error recovery.
        
        Args:
            handler: The event handler.
            event: The event to be processed.
            data: Additional data to be passed to the handler.
            
        Returns:
            The result of the handler call.
        """
        # Get user and state from the event
        user = self._extract_user(event)
        state = data.get("state")
        
        if user:
            # Log user activity
            logger.info(f"User {user.full_name} ({user.id}) is using the bot")
            
            # Add user to data
            data["user"] = user
            
            # Handle system health and API connectivity
            api_connectivity_ok = await self._ensure_api_connectivity(event, data, state)
            if not api_connectivity_ok:
                # User has been transitioned to appropriate error state
                return
            
            # Get or create user in database
            db_user = await self._get_or_create_user(user, data.get("api_client"))
            if db_user:
                data["db_user"] = db_user
                data["db_user_id"] = db_user.get("id")
                data["is_admin"] = db_user.get("is_admin", False)
                
                # Update state with user info if state is available
                if state:
                    await state.update_data(
                        db_user_id=db_user.get("id"),
                        is_admin=db_user.get("is_admin", False)
                    )
            else:
                # Failed to get/create user - handle gracefully
                logger.error(f"Failed to get/create user for {user.id}")
                await self._handle_user_creation_failure(event, state)
                return
            
            # Check admin rights for admin callbacks
            if isinstance(event, CallbackQuery) and self._requires_admin_rights(event):
                is_admin = data.get("is_admin", False)
                if not is_admin:
                    await event.answer("❌ Недостаточно прав для выполнения данного действия", show_alert=True)
                    return
            
            # Handle unknown commands for messages
            if isinstance(event, Message) and self._is_unknown_command(event):
                if state:
                    await handle_unknown_command(event, state, event.text)
                return
        
        # Call the next handler
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Error in handler: {e}", exc_info=True)
            await self._handle_handler_error(event, data, e)
    
    async def _ensure_api_connectivity(
        self, 
        event: TelegramObject, 
        data: Dict[str, Any], 
        state: Optional[FSMContext]
    ) -> bool:
        """
        Ensure API connectivity and handle connection issues.
        
        Args:
            event: The telegram event
            data: Additional data
            state: FSM state context
            
        Returns:
            bool: True if API is accessible, False if connection issues
        """
        # Get API client and add to data
        bot = data.get("bot")
        if not bot:
            logger.error("No bot instance in middleware data")
            return False
        
        api_client = get_api_client_from_bot(bot)
        if not api_client:
            logger.error("No API client available")
            await self._handle_no_api_client(event, state)
            return False
        
        data["api_client"] = api_client
        
        # Test API connectivity with a quick health check
        try:
            health_response = await api_client._make_request("GET", "/health")
            if not health_response.get("success"):
                logger.warning("API health check failed")
                await self._handle_api_connectivity_issue(event, state, health_response)
                return False
        except Exception as e:
            logger.error(f"API connectivity test failed: {e}")
            await self._handle_api_connectivity_issue(event, state, {"error": str(e), "status": 0})
            return False
        
        return True
    
    async def _handle_no_api_client(self, event: TelegramObject, state: Optional[FSMContext]):
        """Handle case when no API client is available."""
        error_message = (
            "🔧 Система временно недоступна.\n"
            "Попробуйте позже или обратитесь к администратору."
        )
        
        if isinstance(event, Message):
            await event.answer(error_message)
        elif isinstance(event, CallbackQuery):
            await event.answer("Система недоступна", show_alert=True)
            await event.message.answer(error_message)
        
        if state:
            await state.set_state(CommonStates.connection_lost)
    
    async def _handle_api_connectivity_issue(
        self, 
        event: TelegramObject, 
        state: Optional[FSMContext], 
        error_response: Dict[str, Any]
    ):
        """Handle API connectivity issues."""
        status = error_response.get("status", 0)
        
        if status == 0:
            # Connection error
            error_message = (
                "🔌 Нет соединения с сервером.\n"
                "Проверяю подключение..."
            )
            target_state = CommonStates.connection_lost
        else:
            # API error
            error_message = (
                "🔥 Ошибка сервера.\n"
                "Попробуйте позже."
            )
            target_state = CommonStates.handling_api_error
        
        if isinstance(event, Message):
            await event.answer(error_message)
        elif isinstance(event, CallbackQuery):
            await event.answer("Проблема с соединением", show_alert=True)
            await event.message.answer(error_message)
        
        if state:
            await state.set_state(target_state)
            await state.update_data(
                error_details=error_response.get("error", "Unknown error"),
                error_time=str(datetime.now()),
                error_status=status
            )
    
    async def _handle_user_creation_failure(self, event: TelegramObject, state: Optional[FSMContext]):
        """Handle failure to create/get user from database."""
        error_message = (
            "👤 Ошибка регистрации пользователя.\n"
            "Попробуйте команду /start или обратитесь к администратору."
        )
        
        if isinstance(event, Message):
            await event.answer(error_message)
        elif isinstance(event, CallbackQuery):
            await event.answer("Ошибка регистрации", show_alert=True)
            await event.message.answer(error_message)
        
        if state:
            await state.set_state(CommonStates.handling_api_error)
            await state.update_data(
                error_details="User creation/retrieval failed",
                error_time=str(datetime.now())
            )
    
    async def _handle_handler_error(
        self, 
        event: TelegramObject, 
        data: Dict[str, Any], 
        error: Exception
    ):
        """Handle errors that occur in handlers."""
        state = data.get("state")
        
        error_message = (
            "❌ Произошла внутренняя ошибка.\n"
            "Попробуйте /start или обратитесь к администратору."
        )
        
        if isinstance(event, Message):
            await event.answer(error_message)
        elif isinstance(event, CallbackQuery):
            await event.answer("Внутренняя ошибка", show_alert=True)
            await event.message.answer(error_message)
        
        if state:
            await state.set_state(CommonStates.handling_api_error)
            await state.update_data(
                error_details=f"Handler error: {str(error)}",
                error_time=str(datetime.now()),
                error_type="handler_exception"
            )
    
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
    
    def _is_unknown_command(self, event: Message) -> bool:
        """
        Check if message contains an unknown command.
        
        Args:
            event: The message event
            
        Returns:
            True if message contains unknown command
        """
        if not event.text or not is_command(event.text):
            return False
        
        # List of known commands
        known_commands = [
            "/start", "/help", "/language", "/study", "/settings", 
            "/stats", "/hint", "/admin", "/cancel", "/retry", "/status"
        ]
        
        command = event.text.split()[0].split('@')[0].lower()
        return command not in known_commands
    
    async def _get_or_create_user(self, user: User, api_client) -> Optional[Dict]:
        """
        Get or create user in the database.
        Enhanced with better error handling and retry logic.
        
        Args:
            user: The Telegram user
            api_client: The API client for database operations
            
        Returns:
            User data from database or None if error
        """
        if not api_client:
            logger.error("No API client provided for user creation")
            return None
        
        try:
            # Try to get existing user
            user_response = await api_client.get_user_by_telegram_id(user.id)
            
            if user_response["success"] and user_response["result"]:
                # User exists, return first result
                users = user_response["result"]
                db_user = users[0] if users else None
                
                if db_user:
                    logger.debug(f"Found existing user: {db_user.get('id')}")
                    
                    # Update user info if it has changed
                    await self._update_user_info_if_needed(user, db_user, api_client)
                    
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
    
    async def _update_user_info_if_needed(
        self, 
        telegram_user: User, 
        db_user: Dict, 
        api_client
    ) -> bool:
        """
        Update user info in database if Telegram profile has changed.
        
        Args:
            telegram_user: Current Telegram user object
            db_user: User data from database
            api_client: API client for updates
            
        Returns:
            bool: True if update was performed
        """
        updates = {}
        
        # Check for changes
        if telegram_user.username != db_user.get("username"):
            updates["username"] = telegram_user.username
        
        if telegram_user.first_name != db_user.get("first_name"):
            updates["first_name"] = telegram_user.first_name
        
        if telegram_user.last_name != db_user.get("last_name"):
            updates["last_name"] = telegram_user.last_name
        
        if updates:
            try:
                update_response = await api_client.update_user(db_user.get("id"), updates)
                if update_response["success"]:
                    logger.info(f"Updated user info for {telegram_user.id}: {updates}")
                    return True
                else:
                    logger.warning(f"Failed to update user info: {update_response.get('error')}")
            except Exception as e:
                logger.error(f"Error updating user info: {e}")
        
        return False


class AdminOnlyMiddleware(BaseMiddleware):
    """Middleware that restricts access to admin-only handlers with enhanced error handling."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Check if user is admin before allowing access.
        Enhanced with meta-state transitions for errors.
        
        Args:
            handler: The event handler
            event: The event to be processed
            data: Additional data passed to the handler
            
        Returns:
            The result of the handler call or None if access denied
        """
        is_admin = data.get("is_admin", False)
        state = data.get("state")
        
        if not is_admin:
            # Send appropriate error message
            if isinstance(event, Message):
                await event.answer("❌ Эта команда доступна только администраторам")
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ Недостаточно прав", show_alert=True)
            
            # Log unauthorized access attempt
            user = data.get("user")
            if user:
                logger.warning(f"Unauthorized admin access attempt by user {user.id} ({user.username})")
            
            return
        
        # User is admin, proceed with handler
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Error in admin handler: {e}", exc_info=True)
            
            # Handle admin-specific errors
            error_message = "❌ Ошибка при выполнении административной операции"
            
            if isinstance(event, Message):
                await event.answer(error_message)
            elif isinstance(event, CallbackQuery):
                await event.answer("Ошибка админки", show_alert=True)
                await event.message.answer(error_message)
            
            if state:
                await state.set_state(CommonStates.handling_api_error)
                await state.update_data(
                    error_details=f"Admin handler error: {str(e)}",
                    error_time=str(datetime.now()),
                    error_type="admin_handler_exception"
                )


class UserRegistrationMiddleware(BaseMiddleware):
    """Middleware that ensures user is registered in the database with enhanced error handling."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Ensure user is registered before handling the event.
        Enhanced with meta-state transitions for registration errors.
        
        Args:
            handler: The event handler
            event: The event to be processed
            data: Additional data passed to the handler
            
        Returns:
            The result of the handler call
        """
        db_user_id = data.get("db_user_id")
        state = data.get("state")
        
        if not db_user_id:
            # User not registered, send error with recovery options
            error_message = (
                "❌ Ошибка регистрации пользователя.\n\n"
                "Попробуйте:\n"
                "• /start - перерегистрироваться\n"
                "• /status - проверить состояние системы"
            )
            
            if isinstance(event, Message):
                await event.answer(error_message)
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ Ошибка регистрации", show_alert=True)
                await event.message.answer(error_message)
            
            # Transition to appropriate meta-state
            if state:
                await state.set_state(CommonStates.handling_api_error)
                await state.update_data(
                    error_details="User not registered in database",
                    error_time=str(datetime.now()),
                    error_type="registration_required"
                )
            
            return
        
        # User is registered, proceed
        return await handler(event, data)


class StateValidationMiddleware(BaseMiddleware):
    """
    NEW: Middleware for validating FSM states and handling state-related errors.
    """
    
    def __init__(self, validate_states: bool = True, auto_recover: bool = True):
        """
        Initialize state validation middleware.
        
        Args:
            validate_states: Whether to validate FSM states
            auto_recover: Whether to attempt automatic recovery from invalid states
        """
        self.validate_states = validate_states
        self.auto_recover = auto_recover
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Validate FSM state before processing events.
        
        Args:
            handler: The event handler
            event: The event to be processed
            data: Additional data passed to the handler
            
        Returns:
            The result of the handler call
        """
        if not self.validate_states:
            return await handler(event, data)
        
        state = data.get("state")
        if not state:
            return await handler(event, data)
        
        current_state = await state.get_state()
        
        # Check for corrupted or invalid states
        if await self._is_state_corrupted(state, current_state):
            if self.auto_recover:
                await self._attempt_state_recovery(event, state)
            else:
                await self._handle_corrupted_state(event, state)
            return
        
        return await handler(event, data)
    
    async def _is_state_corrupted(self, state: FSMContext, current_state: str) -> bool:
        """
        Check if current state is corrupted or invalid.
        
        Args:
            state: FSM state context
            current_state: Current state string
            
        Returns:
            bool: True if state is corrupted
        """
        if not current_state:
            return False
        
        # Check if state data is consistent with current state
        state_data = await state.get_data()
        
        # Example validation logic
        if current_state.startswith("StudyStates:"):
            # Study states should have study-related data
            if not state_data.get("study_words") and not state_data.get("current_word"):
                return True
        
        if current_state.startswith("HintStates:"):
            # Hint states should have hint-related data
            if not state_data.get("hint_state"):
                return True
        
        return False
    
    async def _attempt_state_recovery(self, event: TelegramObject, state: FSMContext):
        """
        Attempt to recover from corrupted state.
        
        Args:
            event: The event object
            state: FSM state context
        """
        logger.info("Attempting state recovery")
        
        # Clear corrupted state but preserve important data
        state_data = await state.get_data()
        important_data = {
            "db_user_id": state_data.get("db_user_id"),
            "current_language": state_data.get("current_language"),
            "is_admin": state_data.get("is_admin", False)
        }
        
        await state.clear()
        await state.update_data(**{k: v for k, v in important_data.items() if v is not None})
        
        recovery_message = (
            "🔧 Обнаружена проблема с состоянием сессии.\n"
            "Состояние восстановлено. Основные данные сохранены.\n\n"
            "Можете продолжить работу с ботом."
        )
        
        if isinstance(event, Message):
            await event.answer(recovery_message)
        elif isinstance(event, CallbackQuery):
            await event.answer("Состояние восстановлено")
            await event.message.answer(recovery_message)
    
    async def _handle_corrupted_state(self, event: TelegramObject, state: FSMContext):
        """
        Handle corrupted state without auto-recovery.
        
        Args:
            event: The event object
            state: FSM state context
        """
        await state.set_state(CommonStates.handling_api_error)
        await state.update_data(
            error_details="Corrupted FSM state detected",
            error_time=str(datetime.now()),
            error_type="state_corruption"
        )
        
        error_message = (
            "⚠️ Обнаружена проблема с состоянием сессии.\n"
            "Используйте /start для сброса или /status для диагностики."
        )
        
        if isinstance(event, Message):
            await event.answer(error_message)
        elif isinstance(event, CallbackQuery):
            await event.answer("Проблема с состоянием", show_alert=True)
            await event.message.answer(error_message)
            