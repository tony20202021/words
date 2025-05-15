"""
API routes for user language settings operations.
This module contains all the API endpoints for managing user language settings in the system.
"""

from typing import List, Optional, Dict, Any
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.status import HTTP_404_NOT_FOUND, HTTP_201_CREATED

from app.api.schemas.user_language_settings import (
    UserLanguageSettingsCreate,
    UserLanguageSettingsUpdate,
    UserLanguageSettings,
    UserLanguageSettingsInDB
)
from app.services.user_language_settings_service import UserLanguageSettingsService
from app.services.user_service import UserService
from app.services.language_service import LanguageService
from app.core.dependencies import get_user_language_settings_service, get_user_service, get_language_service
from app.utils.logger import setup_logger

# Create router for user language settings operations
router = APIRouter(tags=["user_language_settings"])

# Configure logger
logger = setup_logger(__name__)


@router.get("/users/{user_id}/languages/{language_id}/settings", response_model=UserLanguageSettings)
async def get_user_language_settings(
    user_id: str,
    language_id: str,
    settings_service: UserLanguageSettingsService = Depends(get_user_language_settings_service),
    user_service: UserService = Depends(get_user_service),
    language_service: LanguageService = Depends(get_language_service)
):
    """
    Get settings for a specific user and language.
    
    Args:
        user_id: ID of the user
        language_id: ID of the language
        settings_service: User language settings service dependency
        user_service: User service dependency
        language_service: Language service dependency
        
    Returns:
        Settings object or default settings if not found
        
    Raises:
        HTTPException: If user or language not found
    """
    logger.info(f"Getting settings for user id={user_id}, language id={language_id}")
    
    # First check if user exists
    user = await user_service.get_user(user_id)
    if not user:
        logger.warning(f"User with id={user_id} not found when getting settings")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Check if language exists
    language = await language_service.get_language(language_id)
    if not language:
        logger.warning(f"Language with id={language_id} not found when getting settings")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Language with ID {language_id} not found"
        )
    
    # Get settings
    settings = await settings_service.get_settings(user_id, language_id)
    
    # If settings not found, return default settings
    if not settings:
        logger.info(f"No settings found for user id={user_id}, language id={language_id}, returning default values")
        default_settings = await settings_service.get_default_settings()
        return default_settings
    
    return settings


@router.put("/users/{user_id}/languages/{language_id}/settings", response_model=UserLanguageSettingsInDB)
async def update_user_language_settings(
    user_id: str,
    language_id: str,
    settings: UserLanguageSettingsUpdate,
    settings_service: UserLanguageSettingsService = Depends(get_user_language_settings_service),
    user_service: UserService = Depends(get_user_service),
    language_service: LanguageService = Depends(get_language_service)
):
    """
    Update settings for a specific user and language.
    
    Args:
        user_id: ID of the user
        language_id: ID of the language
        settings: Updated settings data
        settings_service: User language settings service dependency
        user_service: User service dependency
        language_service: Language service dependency
        
    Returns:
        Updated settings object
        
    Raises:
        HTTPException: If user or language not found
    """
    logger.info(f"Updating settings for user id={user_id}, language id={language_id}, settings={settings}")
    
    # First check if user exists
    user = await user_service.get_user(user_id)
    if not user:
        logger.warning(f"User with id={user_id} not found when updating settings")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Check if language exists
    language = await language_service.get_language(language_id)
    if not language:
        logger.warning(f"Language with id={language_id} not found when updating settings")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Language with ID {language_id} not found"
        )
    
    # Update settings
    updated_settings = await settings_service.update_settings(user_id, language_id, settings)
    
    if not updated_settings:
        logger.warning(f"Failed to update settings for user id={user_id}, language id={language_id}")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Failed to update settings"
        )
    
    return updated_settings


@router.get("/users/{user_id}/settings", response_model=List[UserLanguageSettingsInDB])
async def get_all_user_settings(
    user_id: str,
    settings_service: UserLanguageSettingsService = Depends(get_user_language_settings_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get all settings for a specific user.
    
    Args:
        user_id: ID of the user
        settings_service: User language settings service dependency
        user_service: User service dependency
        
    Returns:
        List of settings objects
        
    Raises:
        HTTPException: If user not found
    """
    logger.info(f"Getting all settings for user id={user_id}")
    
    # First check if user exists
    user = await user_service.get_user(user_id)
    if not user:
        logger.warning(f"User with id={user_id} not found when getting all settings")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Get all settings for the user
    settings = await settings_service.get_all_settings_for_user(user_id)
    
    return settings