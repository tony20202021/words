"""
Service for word operations.
"""

import logging
from typing import List, Optional, Dict, Any

from app.db.repositories.word_repository import WordRepository
from app.db.repositories.language_repository import LanguageRepository
from app.api.models.word import WordCreate, WordUpdate, Word, WordInDB, WordForReview

logger = logging.getLogger(__name__)


class WordService:
    """Service for handling word operations."""
    
    def __init__(self, repository: WordRepository, language_repository: LanguageRepository):
        """
        Initialize the word service.
        
        Args:
            repository: Word repository instance
            language_repository: Language repository instance
        """
        self.repository = repository
        self.language_repository = language_repository
    
    async def get_word(self, word_id: str) -> Optional[Word]:
        """
        Get a word by ID.
        
        Args:
            word_id: ID of the word to retrieve
            
        Returns:
            Word object or None if not found
        """
        return await self.repository.get_word_with_language_info(word_id)
    
    async def get_words_by_filter(
        self, 
        filters: Dict[str, Any], 
        skip: int = 0, 
        limit: int = 100
    ) -> List[WordInDB]:
        """
        Get words by filter.
        
        Args:
            filters: Filter criteria
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of word objects
        """
        # Convert language_id to string if it's in filters
        if "language_id" in filters and isinstance(filters["language_id"], str):
            filters["language_id"] = filters["language_id"]  # Keep as string, will be converted in repository
        
        return await self.repository.get_by_filter(filters, skip, limit)
    
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
            List of words
        """
        return await self.repository.get_by_language(
            language_id=language_id,
            skip=skip,
            limit=limit,
            word_number=word_number
        )
    
    async def get_word_by_number(
        self, 
        language_id: str, 
        word_number: int
    ) -> Optional[WordInDB]:
        """
        Get a word by language ID and word number.
        
        Args:
            language_id: ID of the language
            word_number: Number of the word in frequency list
            
        Returns:
            Word or None if not found
        """
        return await self.repository.get_by_language_and_word_number(language_id, word_number)
    
    async def create_word(self, word_data: Dict[str, Any]) -> WordInDB:
        """
        Create a new word.
        
        Args:
            word_data: Word data
            
        Returns:
            Created word object
        """
        # Verify language exists
        language_id = word_data.get("language_id")
        language = await self.language_repository.get_by_id(language_id)
        if not language:
            raise ValueError(f"Language with ID {language_id} not found")
        
        # Convert Dict to Pydantic model
        word_create = WordCreate(**word_data)
        
        return await self.repository.create(word_create)
    
    async def update_word(self, word_id: str, word_data: Dict[str, Any]) -> Optional[WordInDB]:
        """
        Update a word by ID.
        
        Args:
            word_id: ID of the word to update
            word_data: Updated word data
            
        Returns:
            Updated word object or None if not found
        """
        # Remove language_id from update data if present to prevent changing language
        if "language_id" in word_data:
            del word_data["language_id"]
        
        # Convert Dict to Pydantic model
        word_update = WordUpdate(**word_data)
        
        return await self.repository.update(word_id, word_update)
    
    async def delete_word(self, word_id: str) -> bool:
        """
        Delete a word by ID.
        
        Args:
            word_id: ID of the word to delete
            
        Returns:
            True if deleted, False if not found
        """
        return await self.repository.delete(word_id)
    
    async def get_words_for_review(
        self, 
        user_id: str, 
        language_id: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[WordForReview]:
        """
        Get words due for review today for a specific user and language.
        
        Args:
            user_id: ID of the user
            language_id: ID of the language
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of words for review
        """
        return await self.repository.get_words_for_review(
            user_id=user_id,
            language_id=language_id,
            skip=skip,
            limit=limit
        )
    
    async def get_next_words_to_learn(
        self, 
        user_id: str, 
        language_id: str, 
        start_from: int = 1,
        skip_learned: bool = True,
        skip: int = 0, 
        limit: int = 100
    ) -> List[WordInDB]:
        """
        Get the next words to learn for a specific user and language.
        
        Args:
            user_id: ID of the user
            language_id: ID of the language
            start_from: Word number to start from
            skip_learned: Skip words that already have statistics
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of words
        """
        return await self.repository.get_next_words_to_learn(
            user_id=user_id,
            language_id=language_id,
            start_from=start_from,
            skip_learned=skip_learned,
            skip=skip,
            limit=limit
        )