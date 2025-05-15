"""
Authentication middleware for the Telegram bot.
This middleware is responsible for user authentication and session management.
"""

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, User

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Middleware for user authentication and session management."""
    
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
        # Получаем пользователя из апдейта
        user = None
        
        # В зависимости от типа события получаем пользователя
        if isinstance(event, Message):
            user = event.from_user
        else:
            # Пытаемся получить пользователя из других типов событий
            # Например, для CallbackQuery
            user_field = getattr(event, "from_user", None)
            if user_field:
                user = user_field
        
        if user:
            # Логгируем информацию о пользователе
            logger.info(f"User {user.full_name} ({user.id}) is using the bot")
            
            # В aiogram 3.x мы можем добавить пользователя в data
            data["user"] = user
            
            # Получаем API-клиент из диспетчера и добавляем его в data
            # Это позволит обработчикам получить доступ к API-клиенту
            dispatcher = data.get("dispatcher")
            if dispatcher and "api_client" in dispatcher:
                # Передаем API-клиент в каждый обработчик
                data["api_client"] = dispatcher["api_client"]
            
            # В реальном приложении здесь будет код для проверки 
            # существования пользователя в БД и его создание при необходимости
            # if "api_client" in data:
            #    await self._get_or_create_user(user, data["api_client"])
            
            # Проверка прав администратора (пример)
            await self._check_admin_rights(user, data)
        
        # Вызываем следующий обработчик
        return await handler(event, data)
    
    async def _check_admin_rights(self, user: User, data: Dict[str, Any]) -> None:
        """
        Check if user has admin rights.
        
        Args:
            user: The Telegram user.
            data: Additional data passed to the handler.
        """
        # Здесь будет код для проверки прав администратора
        # Для простоты используем заглушку
        admin_ids = [12345, 67890]  # ID администраторов
        
        # Устанавливаем флаг is_admin в data
        data["is_admin"] = user.id in admin_ids
    
    async def _get_or_create_user(self, user: User, api_client) -> None:
        """
        Get or create user in the database.
        
        Args:
            user: The Telegram user.
            api_client: The API client for database operations.
        """
        # В реальном приложении здесь будет код для получения 
        # пользователя из БД или его создания
        # Пример:
        # try:
        #     # Проверяем существование пользователя
        #     db_user = await api_client.get_user(user.id)
        # except Exception:
        #     # Если пользователь не найден, создаем его
        #     db_user = await api_client.create_user(
        #         user_id=user.id,
        #         username=user.username,
        #         full_name=user.full_name
        #     )
        
        # Логгируем информацию о пользователе
        logger.info(f"User {user.full_name} ({user.id}) authenticated")