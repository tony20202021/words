"""
API routes for language operations.
This module contains all the API endpoints for managing languages in the system.
"""

from typing import List, Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST, HTTP_201_CREATED

from app.api.schemas.language import LanguageCreate, LanguageResponse, LanguageUpdate
from app.api.schemas.word import WordResponse
from app.services.language_service import LanguageService
from app.services.excel_service import ExcelService
from app.core.dependencies import get_language_service, get_excel_service
from app.utils.logger import setup_logger

# Create router for language operations
router = APIRouter(prefix="/languages", tags=["languages"])

# Configure logger
logger = setup_logger(__name__)


@router.get("/", response_model=List[LanguageResponse])
async def get_languages(
    skip: int = 0,
    limit: int = 100,
    language_service: LanguageService = Depends(get_language_service)
):
    """
    Get all languages with pagination.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        language_service: Language service dependency
        
    Returns:
        List of language objects
    """
    logger.info(f"Getting languages with skip={skip}, limit={limit}")
    languages = await language_service.get_languages(skip=skip, limit=limit)
    return languages


@router.get("/{language_id}", response_model=LanguageResponse)
async def get_language(
    language_id: str,
    language_service: LanguageService = Depends(get_language_service)
):
    """
    Get a language by ID.
    
    Args:
        language_id: ID of the language to retrieve
        language_service: Language service dependency
        
    Returns:
        Language object
        
    Raises:
        HTTPException: If language not found
    """
    logger.info(f"Getting language with id={language_id}")
    language = await language_service.get_language(language_id)
    if not language:
        logger.warning(f"Language with id={language_id} not found")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Language with ID {language_id} not found"
        )
    return language


@router.post("/", response_model=LanguageResponse, status_code=HTTP_201_CREATED)
async def create_language(
    language: LanguageCreate,
    language_service: LanguageService = Depends(get_language_service)
):
    """
    Create a new language.
    
    Args:
        language: Language data
        language_service: Language service dependency
        
    Returns:
        Created language object
    """
    logger.info(f"Creating language with data={language}")
    return await language_service.create_language(language)


@router.put("/{language_id}", response_model=LanguageResponse)
async def update_language(
    language_id: str,
    language: LanguageUpdate,
    language_service: LanguageService = Depends(get_language_service)
):
    """
    Update a language by ID.
    
    Args:
        language_id: ID of the language to update
        language: Updated language data
        language_service: Language service dependency
        
    Returns:
        Updated language object
        
    Raises:
        HTTPException: If language not found
    """
    logger.info(f"Updating language with id={language_id}, data={language}")
    updated_language = await language_service.update_language(language_id, language)
    if not updated_language:
        logger.warning(f"Language with id={language_id} not found for update")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Language with ID {language_id} not found"
        )
    return updated_language


@router.delete("/{language_id}")
async def delete_language(
    language_id: str,
    language_service: LanguageService = Depends(get_language_service)
):
    """
    Delete a language by ID.
    
    Args:
        language_id: ID of the language to delete
        language_service: Language service dependency
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If language not found
    """
    logger.info(f"Deleting language with id={language_id}")
    result = await language_service.delete_language(language_id)
    if not result:
        logger.warning(f"Language with id={language_id} not found for deletion")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Language with ID {language_id} not found"
        )
    return {"message": f"Language with ID {language_id} deleted successfully"}


@router.get("/{language_id}/words", response_model=List[WordResponse])
async def get_language_words(
    language_id: str,
    skip: int = 0,
    limit: int = 100,
    word_number: Optional[int] = None,
    language_service: LanguageService = Depends(get_language_service)
):
    """
    Get words for a specific language with pagination.
    
    Args:
        language_id: ID of the language
        skip: Number of records to skip
        limit: Maximum number of records to return
        word_number: Optional word number to filter by
        language_service: Language service dependency
        
    Returns:
        List of word objects
        
    Raises:
        HTTPException: If language not found
    """
    logger.info(f"Getting words for language id={language_id}, skip={skip}, limit={limit}, word_number={word_number}")
    
    # First check if language exists
    language = await language_service.get_language(language_id)
    if not language:
        logger.warning(f"Language with id={language_id} not found when getting words")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Language with ID {language_id} not found"
        )
    
    # If word_number is provided, try to get that specific word
    if word_number is not None:
        logger.info(f"Filtering for word_number={word_number}")
        words = await language_service.get_words_by_language(
            language_id=language_id,
            skip=0,
            limit=1,
            word_number=word_number
        )
        return words
    
    # Otherwise, get words with pagination
    words = await language_service.get_words_by_language(
        language_id=language_id,
        skip=skip,
        limit=limit
    )
    return words


@router.post("/{language_id}/upload")
async def upload_words_file(
    language_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    column_word: int = Form(0),
    column_translation: int = Form(1),
    column_transcription: int = Form(2),
    column_number: Optional[int] = Form(None),
    start_row: int = Form(1),
    clear_existing: bool = Form(False),
    language_service: LanguageService = Depends(get_language_service),
    excel_service: ExcelService = Depends(get_excel_service)
):
    """
    Upload an Excel file with words for a language.
    
    Args:
        language_id: ID of the language
        background_tasks: FastAPI background tasks
        file: Uploaded Excel file
        column_word: Column index for foreign words (0-based)
        column_translation: Column index for translations (0-based)
        column_transcription: Column index for transcriptions (0-based)
        column_number: Optional column index for word numbers (0-based)
        start_row: Row index to start processing from (0 if no headers, 1 if headers)
        clear_existing: Whether to clear existing words before importing
        language_service: Language service dependency
        excel_service: Excel service dependency
        
    Returns:
        Upload summary info
        
    Raises:
        HTTPException: If language not found or file format is invalid
    """
    logger.info(f"Uploading words file for language id={language_id}")
    
    # Check if language exists
    language = await language_service.get_language(language_id)
    if not language:
        logger.warning(f"Language with id={language_id} not found when uploading file")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Language with ID {language_id} not found"
        )
    
    # Check file extension
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        logger.warning(f"Invalid file format: {file.filename}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Only Excel files (.xlsx, .xls) are supported"
        )
    
    try:
        # Read file content
        contents = await file.read()
        
        # If clear_existing is true, delete existing words for this language first
        if clear_existing:
            logger.info(f"Clearing existing words for language id={language_id}")
            await language_service.delete_all_words_for_language(language_id)
        
        # Parse Excel file
        logger.info(f"Parsing Excel file with columns: word={column_word}, "
                   f"translation={column_translation}, transcription={column_transcription}, "
                   f"number={column_number}, starting from row={start_row}, clear_existing={clear_existing}")
        
        # Process file in background to avoid blocking
        process_result = await excel_service.process_excel_file(
            contents=contents,
            language_id=language_id,
            column_word=column_word,
            column_translation=column_translation,
            column_transcription=column_transcription,
            column_number=column_number,
            start_row=start_row  # Already 0-based (0 if no headers, 1 if headers)
        )

        return {
            "success": True,
            "filename": file.filename,
            "language_id": language_id,
            "language_name": language.dict().get("name_ru", "") if hasattr(language, 'dict') else getattr(language, 'name_ru', ""),
            "total_words_processed": process_result["total_processed"],
            "words_added": process_result["added"],
            "words_updated": process_result["updated"],
            "words_skipped": process_result["skipped"],
            "errors": process_result["errors"]
        }
        
    except Exception as e:
        logger.error(f"Error processing Excel file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Error processing file: {str(e)}"
        )


@router.get("/{language_id}/count")
async def get_language_word_count(
    language_id: str,
    language_service: LanguageService = Depends(get_language_service)
):
    """
    Get the count of words for a specific language.
    
    Args:
        language_id: ID of the language
        language_service: Language service dependency
        
    Returns:
        Dictionary with count information
        
    Raises:
        HTTPException: If language not found
    """
    logger.info(f"Getting word count for language id={language_id}")
    
    # First check if language exists
    language = await language_service.get_language(language_id)
    if not language:
        logger.warning(f"Language with id={language_id} not found when getting word count")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Language with ID {language_id} not found"
        )
    
    # Get the count of words for this language
    count = await language_service.get_word_count_by_language(language_id)
    
    return {"count": count}

"""
Обновленный эндпоинт /languages/{language_id}/users/count для подсчета активных пользователей языка
"""

@router.get("/{language_id}/users/count")
async def get_language_active_users(
    language_id: str,
    language_service: LanguageService = Depends(get_language_service)
):
    """
    Get the count of active users for a specific language.
    
    Args:
        language_id: ID of the language
        language_service: Language service dependency
        
    Returns:
        Dictionary with count of active users
        
    Raises:
        HTTPException: If language not found
    """
    logger.info(f"Getting active users count for language id={language_id}")
    
    # First check if language exists
    language = await language_service.get_language(language_id)
    if not language:
        logger.warning(f"Language with id={language_id} not found")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Language with ID {language_id} not found"
        )
    
    # Get count of active users for this language
    count = await language_service.get_language_active_users(language_id)
    
    return {"count": count}