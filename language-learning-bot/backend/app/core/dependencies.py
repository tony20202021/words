"""
Dependency injection module for the FastAPI application.
This module provides the dependencies for the API routes.
"""

from fastapi import Depends

from app.db.repositories.language_repository import LanguageRepository
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.word_repository import WordRepository
from app.db.repositories.statistics_repository import StatisticsRepository
from app.services.language_service import LanguageService
from app.services.user_service import UserService
from app.services.word_service import WordService
from app.services.statistics_service import StatisticsService
from app.services.excel_service import ExcelService
from app.db.database import get_db_session
from app.db.repositories.user_language_settings_repository import UserLanguageSettingsRepository
from app.services.user_language_settings_service import UserLanguageSettingsService



# Repository dependencies

async def get_language_repository(db = Depends(get_db_session)) -> LanguageRepository:
    """
    Get language repository instance.
    
    Args:
        db: Database session dependency
    
    Returns:
        LanguageRepository instance
    """
    return LanguageRepository(db)


async def get_user_repository(db = Depends(get_db_session)) -> UserRepository:
    """
    Get user repository instance.
    
    Args:
        db: Database session dependency
    
    Returns:
        UserRepository instance
    """
    return UserRepository(db)


async def get_word_repository(db = Depends(get_db_session)) -> WordRepository:
    """
    Get word repository instance.
    
    Args:
        db: Database session dependency
    
    Returns:
        WordRepository instance
    """
    return WordRepository(db)


async def get_statistics_repository(db = Depends(get_db_session)) -> StatisticsRepository:
    """
    Get statistics repository instance.
    
    Args:
        db: Database session dependency
    
    Returns:
        StatisticsRepository instance
    """
    return StatisticsRepository(db)


# Service dependencies

"""
Обновление зависимости для LanguageService в dependencies.py
"""

# Это содержимое нужно добавить/обновить в файле app/core/dependencies.py

async def get_language_service(
    language_repository: LanguageRepository = Depends(get_language_repository),
    word_repository: WordRepository = Depends(get_word_repository),
    statistics_repository: StatisticsRepository = Depends(get_statistics_repository)
) -> LanguageService:
    """
    Get language service.
    
    Args:
        language_repository: Repository for language operations
        word_repository: Repository for word operations
        statistics_repository: Repository for statistics operations
        
    Returns:
        LanguageService instance
    """
    return LanguageService(
        language_repository=language_repository,
        word_repository=word_repository,
        statistics_repository=statistics_repository
    )

async def get_user_service(
    repo: UserRepository = Depends(get_user_repository)
) -> UserService:
    """
    Get user service instance.
    
    Args:
        repo: User repository dependency
    
    Returns:
        UserService instance
    """
    return UserService(repo)


async def get_word_service(
    repo: WordRepository = Depends(get_word_repository),
    lang_repo: LanguageRepository = Depends(get_language_repository)
) -> WordService:
    """
    Get word service instance.
    
    Args:
        repo: Word repository dependency
        lang_repo: Language repository dependency
    
    Returns:
        WordService instance
    """
    return WordService(repo, lang_repo)


async def get_statistics_service(
    repo: StatisticsRepository = Depends(get_statistics_repository),
    word_repo: WordRepository = Depends(get_word_repository)
) -> StatisticsService:
    """
    Get statistics service instance.
    
    Args:
        repo: Statistics repository dependency
        word_repo: Word repository dependency
    
    Returns:
        StatisticsService instance
    """
    return StatisticsService(repo, word_repo)


async def get_excel_service(
    word_service: WordService = Depends(get_word_service)
) -> ExcelService:
    """
    Get excel service instance.
    
    Args:
        word_service: Word service dependency
    
    Returns:
        ExcelService instance
    """
    return ExcelService(word_service)

# Для добавления в файл app/core/dependencies.py

async def get_user_language_settings_repository(db = Depends(get_db_session)) -> UserLanguageSettingsRepository:
    """
    Get user language settings repository instance.
    
    Args:
        db: Database session dependency
    
    Returns:
        UserLanguageSettingsRepository instance
    """
    return UserLanguageSettingsRepository(db)

async def get_user_language_settings_service(
    repository: UserLanguageSettingsRepository = Depends(get_user_language_settings_repository),
    user_repository: UserRepository = Depends(get_user_repository),
    language_repository: LanguageRepository = Depends(get_language_repository)
) -> UserLanguageSettingsService:
    """
    Get user language settings service instance.
    
    Args:
        repository: User language settings repository instance
        user_repository: User repository instance
        language_repository: Language repository instance
        
    Returns:
        UserLanguageSettingsService instance
    """
    return UserLanguageSettingsService(repository, user_repository, language_repository)