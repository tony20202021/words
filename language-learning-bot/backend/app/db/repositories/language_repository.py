"""
Repository for language operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from bson.objectid import ObjectId

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.models.language import LanguageCreate, LanguageUpdate, Language, LanguageInDB

class LanguageRepository:
    """Repository for language operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize repository.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection = db.languages
    
    async def create(self, language: LanguageCreate) -> LanguageInDB:
        """
        Create a new language.
        
        Args:
            language: Language data
            
        Returns:
            Created language
        """
        language_dict = language.dict()
        language_dict["created_at"] = datetime.utcnow()
        language_dict["updated_at"] = language_dict["created_at"]
        
        result = await self.collection.insert_one(language_dict)
        
        created_language = await self.collection.find_one({"_id": result.inserted_id})
        created_language["id"] = str(created_language.pop("_id"))
        
        return LanguageInDB(**created_language)
    
    async def get_by_id(self, id: str) -> Optional[LanguageInDB]:
        """
        Get language by ID.
        
        Args:
            id: Language ID
            
        Returns:
            Language or None if not found
        """
        try:
            language = await self.collection.find_one({"_id": ObjectId(id)})
            if language:
                language["id"] = str(language.pop("_id"))
                return LanguageInDB(**language)
        except Exception:
            return None
        
        return None
    
    async def get_by_name_ru(self, name_ru: str) -> Optional[LanguageInDB]:
        """
        Get language by Russian name.
        
        Args:
            name_ru: Russian name of the language
            
        Returns:
            Language or None if not found
        """
        language = await self.collection.find_one({"name_ru": name_ru})
        if language:
            language["id"] = str(language.pop("_id"))
            return LanguageInDB(**language)
        
        return None
    
    async def get_all(self) -> List[LanguageInDB]:
        """
        Get all languages.
        
        Returns:
            List of languages
        """
        languages = []
        cursor = self.collection.find()
        
        async for language in cursor:
            language["id"] = str(language.pop("_id"))
            languages.append(LanguageInDB(**language))
        
        return languages
    
    async def get_languages_with_word_count(self) -> List[Language]:
        """
        Get all languages with word count.
        
        Returns:
            List of languages with word count
        """
        pipeline = [
            {
                "$lookup": {
                    "from": "words",
                    "localField": "_id",
                    "foreignField": "language_id",
                    "as": "words"
                }
            },
            {
                "$addFields": {
                    "word_count": {"$size": "$words"}
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "name_ru": 1,
                    "name_foreign": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "word_count": 1
                }
            }
        ]
        
        languages = []
        cursor = self.collection.aggregate(pipeline)
        
        async for language in cursor:
            language["id"] = str(language.pop("_id"))
            languages.append(Language(**language))
        
        return languages
    
    async def update(self, id: str, language: LanguageUpdate) -> Optional[LanguageInDB]:
        """
        Update language.
        
        Args:
            id: Language ID
            language: Updated language data
            
        Returns:
            Updated language or None if not found
        """
        language_dict = {k: v for k, v in language.dict().items() if v is not None}
        if not language_dict:
            # Nothing to update
            return await self.get_by_id(id)
        
        language_dict["updated_at"] = datetime.utcnow()
        
        try:
            await self.collection.update_one(
                {"_id": ObjectId(id)},
                {"$set": language_dict}
            )
            
            return await self.get_by_id(id)
        except Exception:
            return None
    
    async def delete(self, id: str) -> bool:
        """
        Delete language.
        
        Args:
            id: Language ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await self.collection.delete_one({"_id": ObjectId(id)})
            return result.deleted_count > 0
        except Exception:
            return False