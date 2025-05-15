"""
Service for language operations.
"""

import logging
from typing import List, Optional
from bson import ObjectId
from app.db.repositories.language_repository import LanguageRepository
from app.db.repositories.word_repository import WordRepository
from app.db.repositories.statistics_repository import StatisticsRepository
from app.api.models.language import LanguageCreate, LanguageUpdate, Language, LanguageInDB
from app.api.models.word import WordInDB

logger = logging.getLogger(__name__)


class LanguageService:
    """Service for handling language operations."""

    def __init__(
        self,
        language_repository: LanguageRepository,
        word_repository: WordRepository,
        statistics_repository: StatisticsRepository
    ):
        """
        Initialize the language service.
        
        Args:
            language_repository: Repository for language operations
            word_repository: Repository for word operations
            statistics_repository: Repository for statistics operations
        """
        self.language_repository = language_repository
        self.word_repository = word_repository
        self.statistics_repository = statistics_repository
    
    async def get_languages(self, skip: int = 0, limit: int = 100) -> List[LanguageInDB]:
        """
        Get all languages with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of language objects
        """
        return await self.language_repository.get_all()
    
    async def get_languages_with_word_count(self) -> List[Language]:
        """
        Get all languages with word count.
        
        Returns:
            List of languages with word count
        """
        return await self.language_repository.get_languages_with_word_count()
    
    async def get_language(self, language_id: str) -> Optional[LanguageInDB]:
        """
        Get a language by ID.
        
        Args:
            language_id: ID of the language to retrieve
            
        Returns:
            Language object or None if not found
        """
        return await self.language_repository.get_by_id(language_id)
    
    async def create_language(self, language: LanguageCreate) -> LanguageInDB:
        """
        Create a new language.
        
        Args:
            language: Language data
            
        Returns:
            Created language object
        """
        return await self.language_repository.create(language)
    
    async def update_language(self, language_id: str, language: LanguageUpdate) -> Optional[LanguageInDB]:
        """
        Update a language by ID.
        
        Args:
            language_id: ID of the language to update
            language: Updated language data
            
        Returns:
            Updated language object or None if not found
        """
        return await self.language_repository.update(language_id, language)
    
    async def delete_language(self, language_id: str) -> bool:
        """
        Delete a language by ID.
        
        Args:
            language_id: ID of the language to delete
            
        Returns:
            True if deleted, False if not found
        """
        return await self.language_repository.delete(language_id)
    
    async def delete_all_words_for_language(self, language_id: str) -> int:
        """
        Delete all words for a specific language.
        
        Args:
            language_id: ID of the language
            
        Returns:
            Number of deleted words
        """
        logger.info(f"Deleting all words for language id={language_id}")
        
        try:
            # Try with string ID first (this is how API client expects it)
            result = await self.word_repository.collection.delete_many({"language_id": language_id})
            deleted_count = result.deleted_count
            
            # If no results, try with ObjectId conversion (backward compatibility)
            if deleted_count == 0:
                try:
                    result = await self.word_repository.collection.delete_many({"language_id": ObjectId(language_id)})
                    deleted_count = result.deleted_count
                except Exception:
                    # If ObjectId conversion fails, return 0
                    pass
                    
            logger.info(f"Deleted {deleted_count} words for language id={language_id}")
            return deleted_count
        except Exception as e:
            logger.error(f"Error deleting words for language id={language_id}: {str(e)}")
            return 0
    
    async def get_words_by_language(
        self, 
        language_id: str, 
        skip: int = 0, 
        limit: int = 100,
        word_number: Optional[int] = None
    ) -> List[WordInDB]:
        """
        Get words for a specific language with pagination.
        
        Args:
            language_id: ID of the language
            skip: Number of records to skip
            limit: Maximum number of records to return
            word_number: Optional word number to filter by
            
        Returns:
            List of word objects
        """
        return await self.word_repository.get_by_language(
            language_id=language_id,
            skip=skip,
            limit=limit,
            word_number=word_number
        )
    
    async def get_language_with_word_count(self, language_id: str) -> Optional[Language]:
        """
        Get a language by ID with word count.
        
        Args:
            language_id: ID of the language to retrieve
            
        Returns:
            Language object with word count or None if not found
        """
        language = await self.language_repository.get_by_id(language_id)
        if not language:
            return None
        
        # Get the language with word count using aggregation
        pipeline = [
            {"$match": {"_id": language_id}},
            {
                "$lookup": {
                    "from": "words",
                    "localField": "_id",
                    "foreignField": "language_id",
                    "as": "words"
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "name_ru": 1,
                    "name_foreign": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "word_count": {"$size": "$words"}
                }
            }
        ]
        
        # Convert language to Language model with word_count
        language_dict = language.dict()
        language_dict["word_count"] = await self.word_repository.collection.count_documents({"language_id": language_id})
        
        return Language(**language_dict)
        
    async def get_word_count_by_language(self, language_id: str) -> int:
        """
        Get the count of words for a specific language.
        
        Args:
            language_id: ID of the language
                
        Returns:
            Number of words for the language
        """
        logger.info(f"Getting word count for language id={language_id}")
        
        # Use the count_documents method from the word repository
        try:
            # Try with string ID first (this is how API client expects it)
            count = await self.word_repository.collection.count_documents({"language_id": language_id})
            
            # If no results, try with ObjectId conversion (backward compatibility)
            if count == 0:
                try:
                    count = await self.word_repository.collection.count_documents({"language_id": ObjectId(language_id)})
                except Exception:
                    # If ObjectId conversion fails, return 0
                    pass
                    
            logger.debug(f"Found {count} words for language id={language_id}")
            return count
        except Exception as e:
            logger.error(f"Error getting word count: {str(e)}")
            return 0
    
    async def get_language_active_users(self, language_id: str) -> int:
        """
        Get the count of active users for a specific language.
        Active users are defined as users who have any word statistics for the given language.
        
        Args:
            language_id: ID of the language
            
        Returns:
            Count of active users
        """
        # Get user IDs from statistics where language_id matches
        # We can use user_statistics collection to find all unique user_ids where language_id matches
        pipeline = [
            {"$match": {"language_id": language_id}},
            {"$group": {"_id": "$user_id"}},
            {"$count": "count"}
        ]
        
        # aggregate возвращает курсор, который нельзя awaited напрямую
        cursor = self.statistics_repository.collection.aggregate(pipeline)
        
        # Convert cursor to list to get the first document
        documents = await cursor.to_list(length=1)
        
        # If there are no active users, return 0
        if not documents:
            return 0
        
        # Otherwise, return the count
        return documents[0].get("count", 0)
