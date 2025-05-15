"""
API routes for word operations.
This module contains all the API endpoints for managing words in the system.
"""

from typing import List, Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.status import HTTP_404_NOT_FOUND, HTTP_201_CREATED, HTTP_400_BAD_REQUEST

from app.api.models.word import WordCreate, WordUpdate, Word, WordInDB, WordForReview
from app.services.word_service import WordService
from app.core.dependencies import get_word_service

# Create router for word operations
router = APIRouter(prefix="/words", tags=["words"])

# Configure logger
logger = logging.getLogger(__name__)


@router.get("/{word_id}", response_model=Word)
async def get_word(
    word_id: str,
    word_service: WordService = Depends(get_word_service)
):
    """
    Get a word by ID.
    
    Args:
        word_id: ID of the word to retrieve
        word_service: Word service dependency
        
    Returns:
        Word object
        
    Raises:
        HTTPException: If word not found
    """
    logger.info(f"Getting word with id={word_id}")
    word = await word_service.get_word(word_id)
    if not word:
        logger.warning(f"Word with id={word_id} not found")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Word with ID {word_id} not found"
        )
    return word


@router.post("/", response_model=WordInDB, status_code=HTTP_201_CREATED)
async def create_word(
    word: WordCreate,
    word_service: WordService = Depends(get_word_service)
):
    """
    Create a new word.
    
    Args:
        word: Word data
        word_service: Word service dependency
        
    Returns:
        Created word object
        
    Raises:
        HTTPException: If language not found
    """
    logger.info(f"Creating word with data={word}")
    try:
        return await word_service.create_word(word.dict())
    except ValueError as e:
        logger.warning(f"Error creating word: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{word_id}", response_model=WordInDB)
async def update_word(
    word_id: str,
    word: WordUpdate,
    word_service: WordService = Depends(get_word_service)
):
    """
    Update a word by ID.
    
    Args:
        word_id: ID of the word to update
        word: Updated word data
        word_service: Word service dependency
        
    Returns:
        Updated word object
        
    Raises:
        HTTPException: If word not found
    """
    logger.info(f"Updating word with id={word_id}, data={word}")
    updated_word = await word_service.update_word(word_id, word.dict())
    if not updated_word:
        logger.warning(f"Word with id={word_id} not found for update")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Word with ID {word_id} not found"
        )
    return updated_word


@router.delete("/{word_id}")
async def delete_word(
    word_id: str,
    word_service: WordService = Depends(get_word_service)
):
    """
    Delete a word by ID.
    
    Args:
        word_id: ID of the word to delete
        word_service: Word service dependency
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If word not found
    """
    logger.info(f"Deleting word with id={word_id}")
    result = await word_service.delete_word(word_id)
    if not result:
        logger.warning(f"Word with id={word_id} not found for deletion")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Word with ID {word_id} not found"
        )
    return {"message": f"Word with ID {word_id} deleted successfully"}


@router.get("/next/{user_id}/{language_id}", response_model=List[WordInDB])
async def get_next_words_to_learn(
    user_id: str,
    language_id: str,
    start_from: int = Query(1, description="Word number to start from"),
    skip_learned: bool = Query(True, description="Skip words that already have statistics"),
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Maximum number of records to return"),
    word_service: WordService = Depends(get_word_service)
):
    """
    Get the next words to learn for a specific user and language.
    
    Args:
        user_id: ID of the user
        language_id: ID of the language
        start_from: Word number to start from
        skip_learned: Skip words that already have statistics
        skip: Number of records to skip
        limit: Maximum number of records to return
        word_service: Word service dependency
        
    Returns:
        List of words
    """
    logger.info(f"Getting next words to learn for user id={user_id}, language id={language_id}, "
               f"start_from={start_from}, skip_learned={skip_learned}, skip={skip}, limit={limit}")
    
    words = await word_service.get_next_words_to_learn(
        user_id=user_id,
        language_id=language_id,
        start_from=start_from,
        skip_learned=skip_learned,
        skip=skip,
        limit=limit
    )
    
    return words