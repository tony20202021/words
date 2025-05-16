"""
Repository for user language settings operations.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.schemas.user_language_settings import (
    UserLanguageSettingsCreate,
    UserLanguageSettingsUpdate,
    UserLanguageSettingsInDB,
)
from app.utils.logger import setup_logger


logger = setup_logger(__name__)


class UserLanguageSettingsRepository:
    """Repository for handling user language settings operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize the repository.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection = db.user_language_settings

    async def get_by_user_and_language(self, user_id: str, language_id: str) -> Optional[UserLanguageSettingsInDB]:
        """
        Get settings for a specific user and language.
        
        Args:
            user_id: ID of the user
            language_id: ID of the language
            
        Returns:
            Settings object or None if not found
        """
        logger.info(f"Getting settings for user_id={user_id}, language_id={language_id}")

        # Convert string IDs to ObjectId
        user_id_obj = ObjectId(user_id)
        language_id_obj = ObjectId(language_id)

        # Get settings for the user and language
        settings = await self.collection.find_one({
            "user_id": user_id_obj,
            "language_id": language_id_obj
        })

        if not settings:
            logger.info(f"No settings found for user_id={user_id}, language_id={language_id}")
            return None

        # Convert ObjectId to string for API response
        settings["id"] = str(settings["_id"])
        settings["user_id"] = str(settings["user_id"])
        settings["language_id"] = str(settings["language_id"])

        return UserLanguageSettingsInDB(**settings)

    async def create(
        self, user_id: str, language_id: str, settings: UserLanguageSettingsCreate
    ) -> UserLanguageSettingsInDB:
        """
        Create user language settings.
        
        Args:
            user_id: ID of the user
            language_id: ID of the language
            settings: Settings data
            
        Returns:
            Created settings object
        """
        logger.info(f"Creating settings for user_id={user_id}, language_id={language_id}, settings={settings}")

        # Convert string IDs to ObjectId
        user_id_obj = ObjectId(user_id)
        language_id_obj = ObjectId(language_id)

        # Prepare the document for insertion
        now = datetime.now()
        settings_dict = settings.dict()
        
        document = {
            "user_id": user_id_obj,
            "language_id": language_id_obj,
            "start_word": settings_dict.get("start_word", 1),
            "skip_marked": settings_dict.get("skip_marked", False),
            "use_check_date": settings_dict.get("use_check_date", True),
            "show_hints": settings_dict.get("show_hints", True),
            "show_debug": settings_dict.get("show_debug", False),  # Добавлено поле show_debug
            "created_at": now,
            "updated_at": now
        }

        # Insert the document
        result = await self.collection.insert_one(document)
        
        # Get the inserted document ID
        document_id = result.inserted_id
        
        # Return the created document with ID
        created_document = await self.collection.find_one({"_id": document_id})
        
        # Convert ObjectId to string for API response
        created_document["id"] = str(created_document["_id"])
        created_document["user_id"] = str(created_document["user_id"])
        created_document["language_id"] = str(created_document["language_id"])
        
        return UserLanguageSettingsInDB(**created_document)

    async def update(
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
        logger.info(f"Updating settings for user_id={user_id}, language_id={language_id}, settings={settings}")

        # Convert string IDs to ObjectId
        user_id_obj = ObjectId(user_id)
        language_id_obj = ObjectId(language_id)

        # Prepare the update document
        now = datetime.now()
        update_dict = {"updated_at": now}
        
        # Only include specified fields in update
        settings_dict = settings.dict(exclude_unset=True)
        for key, value in settings_dict.items():
            if value is not None:
                update_dict[key] = value

        # Update the document
        result = await self.collection.update_one(
            {"user_id": user_id_obj, "language_id": language_id_obj},
            {"$set": update_dict}
        )

        if result.matched_count == 0:
            # If no document was matched, check if we should create a new one
            # This is a upsert behavior
            logger.info(f"No settings found for update, creating new settings")
            
            # Get default values for fields not specified in update
            default_settings = UserLanguageSettingsCreate()
            default_dict = default_settings.dict()
            
            # Merge default values with update values
            create_dict = {**default_dict, **settings_dict}
            
            # Create new settings with merged values
            return await self.create(
                user_id=user_id,
                language_id=language_id,
                settings=UserLanguageSettingsCreate(**create_dict)
            )

        # Get the updated document
        updated_document = await self.collection.find_one({
            "user_id": user_id_obj,
            "language_id": language_id_obj
        })

        if not updated_document:
            logger.warning(f"Updated document not found after update operation")
            return None

        # Convert ObjectId to string for API response
        updated_document["id"] = str(updated_document["_id"])
        updated_document["user_id"] = str(updated_document["user_id"])
        updated_document["language_id"] = str(updated_document["language_id"])

        return UserLanguageSettingsInDB(**updated_document)

    async def delete(self, user_id: str, language_id: str) -> bool:
        """
        Delete settings for a specific user and language.
        
        Args:
            user_id: ID of the user
            language_id: ID of the language
            
        Returns:
            True if deleted, False if not found
        """
        logger.info(f"Deleting settings for user_id={user_id}, language_id={language_id}")

        # Convert string IDs to ObjectId
        user_id_obj = ObjectId(user_id)
        language_id_obj = ObjectId(language_id)

        # Delete the document
        result = await self.collection.delete_one({
            "user_id": user_id_obj,
            "language_id": language_id_obj
        })

        return result.deleted_count > 0

    async def get_by_user_id(self, user_id: str) -> List[UserLanguageSettingsInDB]:
        """
        Get all settings for a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of settings objects
        """
        logger.info(f"Getting all settings for user_id={user_id}")

        # Convert string ID to ObjectId
        user_id_obj = ObjectId(user_id)

        # Get all settings for the user
        cursor = self.collection.find({"user_id": user_id_obj})
        settings = await cursor.to_list(length=None)

        # Convert ObjectId to string for API response
        for setting in settings:
            setting["id"] = str(setting["_id"])
            setting["user_id"] = str(setting["user_id"])
            setting["language_id"] = str(setting["language_id"])

        return [UserLanguageSettingsInDB(**setting) for setting in settings]
    