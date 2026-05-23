"""
Service for user operations.
"""

import logging
from typing import List, Optional

from app.db.repositories.user_repository import UserRepository
from app.api.models.user import UserCreate, UserUpdate, User, UserInDB, UserLanguage

logger = logging.getLogger(__name__)


class UserService:
    """Service for handling user operations."""
    
    def __init__(self, repository: UserRepository):
        """
        Initialize the user service.
        
        Args:
            repository: User repository instance
        """
        self.repository = repository
    
    async def get_users(self, skip: int = 0, limit: int = 100) -> List[UserInDB]:
        """
        Get all users with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of user objects
        """
        return await self.repository.get_all(skip=skip, limit=limit)
    
    async def get_user(self, user_id: str) -> Optional[UserInDB]:
        """
        Get a user by ID.
        
        Args:
            user_id: ID of the user to retrieve
            
        Returns:
            User object or None if not found
        """
        return await self.repository.get_by_id(user_id)
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[UserInDB]:
        """
        Get a user by Telegram ID.
        
        Args:
            telegram_id: Telegram ID of the user
            
        Returns:
            User object or None if not found
        """
        return await self.repository.get_by_telegram_id(telegram_id)
    
    async def create_user(self, user: UserCreate) -> UserInDB:
        existing = await self.repository.get_by_telegram_id(user.telegram_id)
        if existing:
            raise ValueError(f"User with telegram_id {user.telegram_id} already exists")
        return await self.repository.create(user)
    
    async def update_user(self, user_id: str, user: UserUpdate) -> Optional[UserInDB]:
        existing = await self.repository.get_by_id(user_id)
        if not existing:
            return None
        return await self.repository.update(user_id, user)

    async def delete_user(self, user_id: str) -> bool:
        existing = await self.repository.get_by_id(user_id)
        if not existing:
            return False
        return await self.repository.delete(user_id)
    
    async def get_user_languages(self, user_id: str) -> List[UserLanguage]:
        """
        Get all languages that the user has statistics for.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of languages with progress
        """
        return await self.repository.get_user_languages(user_id)
    
    async def get_admins(self) -> List[UserInDB]:
        """
        Get all admin users.
        
        Returns:
            List of admin users
        """
        return await self.repository.get_admins()
    
    """
    Метод get_users_count для UserService
    """

    async def get_users_count(self) -> int:
        return await self.repository.count({})