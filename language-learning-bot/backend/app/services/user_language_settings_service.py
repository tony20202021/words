"""
Service for user language settings operations.
"""

import logging
from typing import List, Optional, Dict, Any

from app.db.repositories.user_language_settings_repository import UserLanguageSettingsRepository
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.language_repository import LanguageRepository
from app.api.schemas.user_language_settings import (
    UserLanguageSettingsCreate,
    UserLanguageSettingsUpdate,
    UserLanguageSettingsInDB,
    UserLanguageSettings
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class UserLanguageSettingsService:
    """Service for handling user language settings operations."""

    def __init__(
        self,
        repository: UserLanguageSettingsRepository,
        user_repository: UserRepository,
        language_repository: LanguageRepository
    ):
        """
        Initialize the user language settings service.
        
        Args:
            repository: User language settings repository instance
            user_repository: User repository instance
            language_repository: Language repository instance
        """
        self.repository = repository
        self.user_repository = user_repository
        self.language_repository = language_repository

    async def get_settings(self, user_id: str, language_id: str) -> Optional[UserLanguageSettingsInDB]:
        """
        Get settings for a specific user and language.
        
        Args:
            user_id: ID of the user
            language_id: ID of the language
            
        Returns:
            Settings object or None if not found
        """
        # First check if user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.warning(f"User with id={user_id} not found when getting settings")
            return None
            
        # Check if language exists
        language = await self.language_repository.get_by_id(language_id)
        if not language:
            logger.warning(f"Language with id={language_id} not found when getting settings")
            return None
            
        # Get settings for the user and language
        return await self.repository.get_by_user_and_language(user_id, language_id)

    async def create_settings(
        self, user_id: str, language_id: str, settings: UserLanguageSettingsCreate
    ) -> Optional[UserLanguageSettingsInDB]:
        """
        Create settings for a specific user and language.
        
        Args:
            user_id: ID of the user
            language_id: ID of the language
            settings: Settings data
            
        Returns:
            Created settings object
        """
        # First check if user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.warning(f"User with id={user_id} not found when creating settings")
            return None
            
        # Check if language exists
        language = await self.language_repository.get_by_id(language_id)
        if not language:
            logger.warning(f"Language with id={language_id} not found when creating settings")
            return None
            
        # Check if settings already exist
        existing_settings = await self.repository.get_by_user_and_language(user_id, language_id)
        if existing_settings:
            logger.warning(f"Settings already exist for user_id={user_id}, language_id={language_id}")
            return existing_settings
            
        # Create settings
        return await self.repository.create(user_id, language_id, settings)

    async def update_settings(
        self, user_id: str, language_id: str, settings: UserLanguageSettingsUpdate
    ) -> Optional[UserLanguageSettingsInDB]:
        """
        Update settings for a specific user and language.
        
        Args:
            user_id: ID of the user
            language_id: ID of the language
            settings: Updated settings data
            
        Returns:
            Updated settings object or None if not found
        """
        # First check if user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.warning(f"User with id={user_id} not found when updating settings")
            return None
            
        # Check if language exists
        language = await self.language_repository.get_by_id(language_id)
        if not language:
            logger.warning(f"Language with id={language_id} not found when updating settings")
            return None
            
        # Update settings (repository handles upsert logic)
        return await self.repository.update(user_id, language_id, settings)

    async def delete_settings(self, user_id: str, language_id: str) -> bool:
        """
        Delete settings for a specific user and language.
        
        Args:
            user_id: ID of the user
            language_id: ID of the language
            
        Returns:
            True if deleted, False if not found
        """
        return await self.repository.delete(user_id, language_id)

    async def get_all_settings_for_user(self, user_id: str) -> List[UserLanguageSettingsInDB]:
        """
        Get all settings for a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of settings objects
        """
        # First check if user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.warning(f"User with id={user_id} not found when getting all settings")
            return []
            
        # Get all settings for the user
        return await self.repository.get_by_user_id(user_id)

    async def get_default_settings(self) -> Dict[str, Any]:
        """
        Get default settings values.
        
        Returns:
            Dictionary with default settings values
        """
        default_settings = UserLanguageSettingsCreate()
        return default_settings.dict()