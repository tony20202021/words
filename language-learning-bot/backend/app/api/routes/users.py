"""
API routes for user operations.
This module contains all the API endpoints for managing users in the system.
"""

from typing import List, Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.status import HTTP_404_NOT_FOUND, HTTP_201_CREATED

from app.api.models.user import UserCreate, UserUpdate, User, UserInDB, UserLanguage
from app.services.user_service import UserService
from app.core.dependencies import get_user_service

# Create router for user operations
router = APIRouter(prefix="/users", tags=["users"])

# Configure logger
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[UserInDB])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    telegram_id: Optional[int] = None,
    user_service: UserService = Depends(get_user_service)
):
    """
    Get all users with pagination or filter by telegram_id.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        telegram_id: Optional Telegram ID to filter by
        user_service: User service dependency
        
    Returns:
        List of user objects
    """
    logger.info(f"Getting users with skip={skip}, limit={limit}, telegram_id={telegram_id}")
    
    if telegram_id:
        # If telegram_id is provided, try to get that specific user
        user = await user_service.get_user_by_telegram_id(telegram_id)
        return [user] if user else []
    
    # Otherwise, get users with pagination
    users = await user_service.get_users(skip=skip, limit=limit)
    return users

@router.get("/count")
async def get_users_count(
    user_service: UserService = Depends(get_user_service)
):
    """
    Get the total count of users in the system.
    
    Args:
        user_service: User service dependency
        
    Returns:
        Dictionary with count of users
    """
    logger.info("Getting total count of users")
    
    # Get total count from service
    count = await user_service.get_users_count()
    
    return {"count": count}

@router.get("/{user_id}", response_model=UserInDB)
async def get_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    """
    Get a user by ID.
    
    Args:
        user_id: ID of the user to retrieve
        user_service: User service dependency
        
    Returns:
        User object
        
    Raises:
        HTTPException: If user not found
    """
    logger.info(f"Getting user with id={user_id}")
    user = await user_service.get_user(user_id)
    if not user:
        logger.warning(f"User with id={user_id} not found")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return user


@router.post("/", response_model=UserInDB, status_code=HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    Create a new user.
    
    Args:
        user: User data
        user_service: User service dependency
        
    Returns:
        Created user object
    """
    logger.info(f"Creating user with data={user}")
    return await user_service.create_user(user)


@router.put("/{user_id}", response_model=UserInDB)
async def update_user(
    user_id: str,
    user: UserUpdate,
    user_service: UserService = Depends(get_user_service)
):
    """
    Update a user by ID.
    
    Args:
        user_id: ID of the user to update
        user: Updated user data
        user_service: User service dependency
        
    Returns:
        Updated user object
        
    Raises:
        HTTPException: If user not found
    """
    logger.info(f"Updating user with id={user_id}, data={user}")
    updated_user = await user_service.update_user(user_id, user)
    if not updated_user:
        logger.warning(f"User with id={user_id} not found for update")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return updated_user


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    """
    Delete a user by ID.
    
    Args:
        user_id: ID of the user to delete
        user_service: User service dependency
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If user not found
    """
    logger.info(f"Deleting user with id={user_id}")
    result = await user_service.delete_user(user_id)
    if not result:
        logger.warning(f"User with id={user_id} not found for deletion")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return {"message": f"User with ID {user_id} deleted successfully"}


@router.get("/{user_id}/languages", response_model=List[UserLanguage])
async def get_user_languages(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    """
    Get all languages that the user has statistics for.
    
    Args:
        user_id: ID of the user
        user_service: User service dependency
        
    Returns:
        List of languages with progress
        
    Raises:
        HTTPException: If user not found
    """
    logger.info(f"Getting languages for user id={user_id}")
    
    # First check if user exists
    user = await user_service.get_user(user_id)
    if not user:
        logger.warning(f"User with id={user_id} not found when getting languages")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Get languages for user
    languages = await user_service.get_user_languages(user_id)
    return languages
