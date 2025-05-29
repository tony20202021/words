"""
API routes for user language settings operations.
This module contains all the API endpoints for managing user language settings in the system.
"""

from typing import List, Optional, Dict, Any
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.status import HTTP_404_NOT_FOUND, HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from pydantic import BaseModel

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


class HintSettingRequest(BaseModel):
    """Request model for toggling hint settings."""
    enabled: bool


class HintSettingsResponse(BaseModel):
    """Response model for hint settings."""
    phoneticsound: bool
    phoneticassociation: bool
    meaning: bool
    writing: bool


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
    
    # If settings not found, create default settings
    if not settings:
        logger.info(f"No settings found for user id={user_id}, language id={language_id}, creating defaults")
        default_settings_data = UserLanguageSettingsCreate()
        settings = await settings_service.create_settings(user_id, language_id, default_settings_data)
        
        # Если создание не удалось (например, из-за гонки условий), пробуем получить еще раз
        if not settings:
            logger.warning(f"Failed to create settings, trying to get again")
            settings = await settings_service.get_settings(user_id, language_id)
            
            # Если снова не удалось получить, выбрасываем исключение
            if not settings:
                logger.error(f"Failed to get or create settings")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to get or create settings"
                )
    
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


# НОВЫЕ ЭНДПОИНТЫ ДЛЯ РАБОТЫ С ИНДИВИДУАЛЬНЫМИ НАСТРОЙКАМИ ПОДСКАЗОК

@router.patch("/users/{user_id}/languages/{language_id}/settings/hints/{hint_type}")
async def toggle_hint_setting(
    user_id: str,
    language_id: str,
    hint_type: str,
    request: HintSettingRequest,
    settings_service: UserLanguageSettingsService = Depends(get_user_language_settings_service)
) -> Dict[str, Any]:
    """
    Toggle a specific hint setting for a user and language.
    
    Args:
        user_id: ID of the user
        language_id: ID of the language  
        hint_type: Type of hint ('syllables', 'association', 'meaning', 'writing')
        request: Request containing the enabled status
        settings_service: Settings service dependency
        
    Returns:
        Response with updated settings
        
    Raises:
        HTTPException: If user/language not found or invalid hint type
    """
    logger.info(f"Toggling hint setting: user_id={user_id}, language_id={language_id}, "
                f"hint_type={hint_type}, enabled={request.enabled}")
    
    try:
        # Toggle the specific hint setting
        settings = await settings_service.toggle_hint_setting(
            user_id, language_id, hint_type, request.enabled
        )
        
        if not settings:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"User or language not found, or invalid hint type: {hint_type}"
            )
        
        return {
            "success": True,
            "status": 200,
            "result": settings.dict(),
            "error": None
        }
        
    except ValueError as e:
        logger.error(f"Invalid hint type: {hint_type}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error toggling hint setting: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while updating hint setting"
        )


@router.get("/users/{user_id}/languages/{language_id}/settings/hints", response_model=HintSettingsResponse)
async def get_hint_settings(
    user_id: str,
    language_id: str,
    settings_service: UserLanguageSettingsService = Depends(get_user_language_settings_service)
):
    """
    Get hint settings for a specific user and language.
    
    Args:
        user_id: ID of the user
        language_id: ID of the language
        settings_service: Settings service dependency
        
    Returns:
        Dictionary with hint settings
        
    Raises:
        HTTPException: If user or language not found
    """
    logger.info(f"Getting hint settings for user_id={user_id}, language_id={language_id}")
    
    try:
        hint_settings = await settings_service.get_hint_settings(user_id, language_id)
        
        return HintSettingsResponse(
            syllables=hint_settings['syllables'],
            association=hint_settings['association'],
            meaning=hint_settings['meaning'],
            writing=hint_settings['writing']
        )
        
    except Exception as e:
        logger.error(f"Error getting hint settings: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while getting hint settings"
        )


@router.post("/users/{user_id}/languages/{language_id}/settings/hints/bulk")
async def update_multiple_hint_settings(
    user_id: str,
    language_id: str,
    hint_settings: HintSettingsResponse,
    settings_service: UserLanguageSettingsService = Depends(get_user_language_settings_service)
) -> Dict[str, Any]:
    """
    Update multiple hint settings at once for a user and language.
    
    Args:
        user_id: ID of the user
        language_id: ID of the language
        hint_settings: Dictionary with hint settings to update
        settings_service: Settings service dependency
        
    Returns:
        Response with updated settings
        
    Raises:
        HTTPException: If user or language not found
    """
    logger.info(f"Updating multiple hint settings for user_id={user_id}, language_id={language_id}, "
                f"settings={hint_settings}")
    
    try:
        # Create update data with all hint settings
        update_data = UserLanguageSettingsUpdate(
            show_hint_phoneticsound=hint_settings.phoneticsound,
            show_hint_phoneticassociation=hint_settings.phoneticassociation,
            show_hint_meaning=hint_settings.meaning,
            show_hint_writing=hint_settings.writing
        )
        
        # Update settings
        updated_settings = await settings_service.update_settings(user_id, language_id, update_data)
        
        if not updated_settings:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="User or language not found"
            )
        
        return {
            "success": True,
            "status": 200,
            "result": updated_settings.dict(),
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Error updating multiple hint settings: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while updating hint settings"
        )


@router.post("/admin/migrate-hint-settings")
async def migrate_hint_settings(
    settings_service: UserLanguageSettingsService = Depends(get_user_language_settings_service)
) -> Dict[str, Any]:
    """
    Migrate existing user language settings to include individual hint flags.
    This endpoint is for administrative use only.
    
    Args:
        settings_service: Settings service dependency
        
    Returns:
        Response with migration results
    """
    logger.info("Starting migration of user language settings")
    
    try:
        count = await settings_service.migrate_existing_settings()
        
        return {
            "success": True,
            "status": 200,
            "result": {
                "message": "Migration completed successfully",
                "updated_count": count
            },
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Migration failed: {str(e)}"
        )
    