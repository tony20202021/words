"""
API routes for statistics operations.
This module contains all the API endpoints for managing user statistics in the system.
"""

from typing import List, Optional, Dict, Any
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.status import HTTP_404_NOT_FOUND, HTTP_201_CREATED, HTTP_400_BAD_REQUEST

from app.api.models.statistics import (
    UserStatisticsCreate, 
    UserStatisticsUpdate, 
    UserStatistics, 
    UserStatisticsInDB,
    UserProgress
)
from app.services.statistics_service import StatisticsService
from app.services.user_service import UserService
from app.core.dependencies import get_statistics_service, get_user_service
from app.utils.logger import setup_logger

# Create router for statistics operations
router = APIRouter(prefix="/users", tags=["statistics"])

# Configure logger
logger = setup_logger(__name__)


@router.get("/{user_id}/statistics", response_model=List[UserStatisticsInDB])
async def get_user_statistics(
    user_id: str,
    language_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    validate_words: bool = Query(False, description="Only return statistics for existing words"),
    statistics_service: StatisticsService = Depends(get_statistics_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get statistics for a specific user with optional language filter.
    ОБНОВЛЕНО: добавлен параметр validate_words для фильтрации по существующим словам.
    
    Args:
        user_id: ID of the user
        language_id: Optional ID of the language to filter by
        skip: Number of records to skip
        limit: Maximum number of records to return
        validate_words: If True, only return statistics for existing words
        statistics_service: Statistics service dependency
        user_service: User service dependency
        
    Returns:
        List of statistics objects
        
    Raises:
        HTTPException: If user not found
    """
    logger.info(f"Getting statistics for user id={user_id}, language id={language_id}, "
               f"skip={skip}, limit={limit}, validate_words={validate_words}")
    
    # First check if user exists
    user = await user_service.get_user(user_id)
    if not user:
        logger.warning(f"User with id={user_id} not found when getting statistics")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Get statistics for user
    statistics = await statistics_service.get_user_statistics(
        user_id=user_id,
        language_id=language_id,
        skip=skip,
        limit=limit,
        validate_words=validate_words
    )
    
    return statistics


@router.get("/{user_id}/statistics/count", response_model=Dict[str, int])
async def count_user_statistics(
    user_id: str,
    language_id: Optional[str] = Query(None, description="Optional language ID to filter by"),
    validate_words: bool = Query(False, description="Only count statistics for existing words"),
    statistics_service: StatisticsService = Depends(get_statistics_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    НОВЫЙ ЭНДПОИНТ: Подсчет статистики пользователя без получения записей.
    Намного быстрее чем получение всех записей для подсчета.
    
    Args:
        user_id: ID of the user
        language_id: Optional ID of the language to filter by
        validate_words: If True, only count statistics for existing words
        statistics_service: Statistics service dependency
        user_service: User service dependency
        
    Returns:
        Dict with count of statistics records
        
    Raises:
        HTTPException: If user not found
    """
    logger.info(f"Counting statistics for user id={user_id}, language id={language_id}, "
               f"validate_words={validate_words}")
    
    # First check if user exists
    user = await user_service.get_user(user_id)
    if not user:
        logger.warning(f"User with id={user_id} not found when counting statistics")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Count statistics for user
    count = await statistics_service.count_user_statistics(
        user_id=user_id,
        language_id=language_id,
        validate_words=validate_words
    )
    
    return {"count": count}


@router.get("/{user_id}/word_data/{word_id}", response_model=Optional[UserStatistics])
async def get_user_word_data(
    user_id: str,
    word_id: str,
    statistics_service: StatisticsService = Depends(get_statistics_service)
):
    """
    Get user data for a specific word.
    ПРОВЕРЕНО: метод уже использует get_with_word_info с JOIN, корректен.
    """
    statistics = await statistics_service.get_user_word_statistics(user_id, word_id)
    
    # Вместо выбрасывания исключения возвращаем None или пустой объект
    if not statistics:
        return None
    
    return statistics


@router.post("/{user_id}/word_data", response_model=UserStatisticsInDB, status_code=HTTP_201_CREATED)
async def create_user_word_data(
    user_id: str,
    word_data: UserStatisticsCreate,
    statistics_service: StatisticsService = Depends(get_statistics_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Create user word data.
    
    Args:
        user_id: The user ID
        word_data: The word data to create
        statistics_service: Statistics service dependency
        user_service: User service dependency
        
    Returns:
        Dict with created user word data
        
    Raises:
        HTTPException: If user not found
    """
    logger.info(f"Creating word data for user id={user_id}, data={word_data}")
    
    # First check if user exists
    user = await user_service.get_user(user_id)
    if not user:
        logger.warning(f"User with id={user_id} not found when creating word data")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Create statistics
    try:
        return await statistics_service.create_user_word_statistics(user_id, word_data)
    except ValueError as e:
        logger.warning(f"Error creating word data: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{user_id}/word_data/{word_id}", response_model=UserStatisticsInDB)
async def update_user_word_data(
    user_id: str,
    word_id: str,
    word_data: UserStatisticsUpdate,
    statistics_service: StatisticsService = Depends(get_statistics_service)
):
    """
    Update user word data.
    
    Args:
        user_id: The user ID
        word_id: The word ID
        word_data: The word data to update
        statistics_service: Statistics service dependency
        
    Returns:
        Dict with updated user word data
        
    Raises:
        HTTPException: If statistics not found
    """
    logger.info(f"Updating word data for user id={user_id}, word id={word_id}, data={word_data}")
    
    updated_statistics = await statistics_service.update_user_word_statistics(user_id, word_id, word_data)
    
    if not updated_statistics:
        logger.warning(f"Statistics for user id={user_id}, word id={word_id} not found for update")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Statistics for user {user_id} and word {word_id} not found"
        )
    
    return updated_statistics


@router.get("/{user_id}/languages/{language_id}/study", response_model=List[Dict[str, Any]])
async def get_study_words(
    user_id: str,
    language_id: str,
    start_word: int = Query(1, description="Word number to start from"),
    skip_marked: str = Query("false", description="Skip marked words"),
    use_check_date: str = Query("true", description="Consider next check date"),
    limit: int = Query(100, description="Maximum number of words to return"),
    skip: int = Query(0, description="Number of records to skip"),
    statistics_service: StatisticsService = Depends(get_statistics_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get words for study with various filters.
    ПРОВЕРЕНО: service метод уже использует оптимизированную логику с JOIN.
    """
    # Преобразование строковых значений в булевы
    skip_marked_bool = skip_marked.lower() == "true"
    use_check_date_bool = use_check_date.lower() == "true"
    
    logger.info(f"API request: GET study words for user_id={user_id}, language_id={language_id}, "
               f"start_word={start_word}, skip_marked={skip_marked} (parsed to {skip_marked_bool}), "
               f"use_check_date={use_check_date} (parsed to {use_check_date_bool}), limit={limit}, skip={skip}")
    
    # First check if user exists
    user = await user_service.get_user(user_id)
    if not user:
        logger.warning(f"User with id={user_id} not found when getting study words")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Get words for study
    try:
        words = await statistics_service.get_words_for_study(
            user_id=user_id,
            language_id=language_id,
            start_word=start_word,
            skip_marked=skip_marked_bool,
            use_check_date=use_check_date_bool,
            skip=skip,
            limit=limit
        )
        
        logger.info(f"Returning {len(words)} words for study to client")
        return words
    except ValueError as e:
        logger.warning(f"Error getting study words: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{user_id}/statistics/{word_id}/score/{score}", response_model=UserStatisticsInDB)
async def update_score(
    user_id: str,
    word_id: str,
    score: int,
    statistics_service: StatisticsService = Depends(get_statistics_service)
):
    """
    Update score and adjust check interval and next check date based on spaced repetition algorithm.
    
    Args:
        user_id: ID of the user
        word_id: ID of the word
        score: New score (0 or 1)
        statistics_service: Statistics service dependency
        
    Returns:
        Updated statistics object
        
    Raises:
        HTTPException: If statistics not found or score invalid
    """
    logger.info(f"Updating score for user id={user_id}, word id={word_id}, score={score}")
    
    if score not in [0, 1]:
        logger.warning(f"Invalid score: {score}, must be 0 or 1")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Score must be 0 or 1"
        )
    
    updated_statistics = await statistics_service.update_score(user_id, word_id, score)
    
    if not updated_statistics:
        logger.warning(f"Statistics for user id={user_id}, word id={word_id} not found for score update")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Statistics for user {user_id} and word {word_id} not found"
        )
    
    return updated_statistics


@router.get("/{user_id}/languages/{language_id}/progress", response_model=UserProgress)
async def get_user_progress(
    user_id: str,
    language_id: str,
    statistics_service: StatisticsService = Depends(get_statistics_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get user progress for a specific language.
    УЛЬТРА-ОПТИМИЗИРОВАНО: теперь использует исправленный service метод с эффективным подсчетом.
    
    Args:
        user_id: ID of the user
        language_id: ID of the language
        statistics_service: Statistics service dependency
        user_service: User service dependency
        
    Returns:
        User progress object
        
    Raises:
        HTTPException: If user not found
    """
    logger.info(f"Getting progress for user id={user_id}, language id={language_id}")
    
    # First check if user exists
    user = await user_service.get_user(user_id)
    if not user:
        logger.warning(f"User with id={user_id} not found when getting progress")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Get progress - теперь использует ультра-оптимизированную логику
    progress = await statistics_service.get_user_progress(user_id, language_id)
    return progress


@router.get("/{user_id}/languages/{language_id}/review", response_model=List[Dict[str, Any]])
async def get_words_for_review(
    user_id: str,
    language_id: str,
    skip: int = 0,
    limit: int = 100,
    statistics_service: StatisticsService = Depends(get_statistics_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get words due for review today.
    ПРОВЕРЕНО: service метод уже корректно использует JOIN в repository.
    
    Args:
        user_id: ID of the user
        language_id: ID of the language
        skip: Number of records to skip
        limit: Maximum number of records to return
        statistics_service: Statistics service dependency
        user_service: User service dependency
        
    Returns:
        List of words for review
        
    Raises:
        HTTPException: If user not found
    """
    logger.info(f"Getting words for review for user id={user_id}, language id={language_id}, skip={skip}, limit={limit}")
    
    # First check if user exists
    user = await user_service.get_user(user_id)
    if not user:
        logger.warning(f"User with id={user_id} not found when getting words for review")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Get words for review
    words = await statistics_service.get_words_for_review(
        user_id=user_id,
        language_id=language_id,
        skip=skip,
        limit=limit
    )
    
    return words


# ===== НОВЫЕ АДМИНИСТРАТИВНЫЕ ЭНДПОИНТЫ =====

@router.get("/admin/statistics/integrity", response_model=Dict[str, Any])
async def get_statistics_integrity_report(
    statistics_service: StatisticsService = Depends(get_statistics_service)
):
    """
    НОВЫЙ АДМИНИСТРАТИВНЫЙ ЭНДПОИНТ: Получить отчет о целостности данных статистики.
    Показывает количество и процент мертвых ссылок.
    
    Returns:
        Отчет о целостности данных
    """
    logger.info("Getting statistics integrity report")
    
    try:
        report = await statistics_service.get_data_integrity_report()
        return {
            "success": True,
            "report": report
        }
    except Exception as e:
        logger.error(f"Error getting integrity report: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Error generating integrity report: {str(e)}"
        )


@router.post("/admin/statistics/cleanup", response_model=Dict[str, Any])
async def cleanup_orphaned_statistics(
    dry_run: bool = Query(True, description="If true, only count orphaned records without deleting"),
    statistics_service: StatisticsService = Depends(get_statistics_service)
):
    """
    НОВЫЙ АДМИНИСТРАТИВНЫЙ ЭНДПОИНТ: Очистка статистики с мертвыми ссылками.
    
    Args:
        dry_run: Если True, только подсчитывает без удаления
        statistics_service: Statistics service dependency
        
    Returns:
        Отчет об операции очистки
    """
    logger.info(f"Starting cleanup of orphaned statistics, dry_run={dry_run}")
    
    try:
        cleanup_result = await statistics_service.cleanup_orphaned_statistics(dry_run=dry_run)
        return {
            "success": True,
            "cleanup_result": cleanup_result
        }
    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Error during cleanup: {str(e)}"
        )


@router.get("/admin/statistics/health", response_model=Dict[str, Any])
async def get_statistics_health(
    statistics_service: StatisticsService = Depends(get_statistics_service)
):
    """
    НОВЫЙ АДМИНИСТРАТИВНЫЙ ЭНДПОИНТ: Комплексная проверка здоровья системы статистики.
    
    Returns:
        Комплексный отчет о состоянии статистики
    """
    logger.info("Getting comprehensive statistics health report")
    
    try:
        # Получаем отчет о целостности
        integrity_report = await statistics_service.get_data_integrity_report()
        
        # Дополнительные проверки можно добавить здесь
        health_status = "healthy" if integrity_report["orphaned_percentage"] < 5.0 else "degraded"
        
        return {
            "success": True,
            "status": health_status,
            "integrity": integrity_report,
            "recommendations": _get_health_recommendations(integrity_report)
        }
    except Exception as e:
        logger.error(f"Error getting health report: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Error generating health report: {str(e)}"
        )


def _get_health_recommendations(integrity_report: Dict[str, Any]) -> List[str]:
    """
    Генерирует рекомендации на основе отчета о целостности.
    """
    recommendations = []
    
    orphaned_percentage = integrity_report.get("orphaned_percentage", 0)
    
    if orphaned_percentage > 10:
        recommendations.append("CRITICAL: High percentage of orphaned statistics (>10%). Run cleanup immediately.")
    elif orphaned_percentage > 5:
        recommendations.append("WARNING: Moderate percentage of orphaned statistics (>5%). Consider running cleanup.")
    elif orphaned_percentage > 1:
        recommendations.append("INFO: Low percentage of orphaned statistics (>1%). Cleanup can be scheduled.")
    else:
        recommendations.append("GOOD: Very low percentage of orphaned statistics (<1%).")
    
    if integrity_report.get("orphaned_statistics", 0) > 1000:
        recommendations.append("Consider implementing cascade deletion for word removal.")
    
    if not recommendations:
        recommendations.append("Statistics integrity is excellent.")
    
    return recommendations
