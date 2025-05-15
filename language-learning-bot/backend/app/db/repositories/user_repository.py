"""
Repository for user operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from bson.objectid import ObjectId

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.models.user import UserCreate, UserUpdate, User, UserInDB, UserLanguage

class UserRepository:
    """Repository for user operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize repository.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection = db.users
    
    async def create(self, user: UserCreate) -> UserInDB:
        """
        Create a new user.
        
        Args:
            user: User data
            
        Returns:
            Created user
        """
        user_dict = user.dict()
        user_dict["created_at"] = datetime.utcnow()
        user_dict["updated_at"] = user_dict["created_at"]
        
        result = await self.collection.insert_one(user_dict)
        
        created_user = await self.collection.find_one({"_id": result.inserted_id})
        created_user["id"] = str(created_user.pop("_id"))
        
        return UserInDB(**created_user)
    
    async def get_by_id(self, id: str) -> Optional[UserInDB]:
        """
        Get user by ID.
        
        Args:
            id: User ID
            
        Returns:
            User or None if not found
        """
        try:
            user = await self.collection.find_one({"_id": ObjectId(id)})
            if user:
                user["id"] = str(user.pop("_id"))
                return UserInDB(**user)
        except Exception:
            return None
        
        return None
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[UserInDB]:
        """
        Get a user by Telegram ID.
        
        Args:
            telegram_id: Telegram ID of the user
            
        Returns:
            User or None if not found
        """
        user = await self.collection.find_one({"telegram_id": telegram_id})
        if user:
            user["id"] = str(user.pop("_id"))
            return UserInDB(**user)
        
        return None
    
    async def get_by_username(self, username: str) -> Optional[UserInDB]:
        """
        Get a user by username.
        
        Args:
            username: Username of the user
            
        Returns:
            User or None if not found
        """
        user = await self.collection.find_one({"username": username})
        if user:
            user["id"] = str(user.pop("_id"))
            return UserInDB(**user)
        
        return None
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[UserInDB]:
        """
        Get all users with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of users
        """
        users = []
        cursor = self.collection.find().skip(skip).limit(limit)
        
        async for user in cursor:
            user["id"] = str(user.pop("_id"))
            users.append(UserInDB(**user))
        
        return users
    
    async def get_admins(self) -> List[UserInDB]:
        """
        Get all admin users.
        
        Returns:
            List of admin users
        """
        users = []
        cursor = self.collection.find({"is_admin": True})
        
        async for user in cursor:
            user["id"] = str(user.pop("_id"))
            users.append(UserInDB(**user))
        
        return users
    
    async def update(self, id: str, user: UserUpdate) -> Optional[UserInDB]:
        """
        Update user.
        
        Args:
            id: User ID
            user: Updated user data
            
        Returns:
            Updated user or None if not found
        """
        user_dict = {k: v for k, v in user.dict().items() if v is not None}
        if not user_dict:
            # Nothing to update
            return await self.get_by_id(id)
        
        user_dict["updated_at"] = datetime.utcnow()
        
        try:
            await self.collection.update_one(
                {"_id": ObjectId(id)},
                {"$set": user_dict}
            )
            
            return await self.get_by_id(id)
        except Exception:
            return None
    
    async def delete(self, id: str) -> bool:
        """
        Delete user.
        
        Args:
            id: User ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await self.collection.delete_one({"_id": ObjectId(id)})
            return result.deleted_count > 0
        except Exception:
            return False
    
    async def get_user_languages(self, user_id: str) -> List[UserLanguage]:
        """
        Get all languages that the user has statistics for.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of languages with progress
        """
        try:
            # Aggregation pipeline to get unique language_ids
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {"_id": "$language_id", "count": {"$sum": 1}}},
                {
                    "$lookup": {
                        "from": "languages",
                        "localField": "_id",
                        "foreignField": "_id",
                        "as": "language"
                    }
                },
                {"$unwind": "$language"},
                {
                    "$project": {
                        "_id": 0,
                        "id": {"$toString": "$language._id"},
                        "name_ru": "$language.name_ru",
                        "name_foreign": "$language.name_foreign",
                        "word_count": {"$literal": 0},
                        "words_studied": "$count",
                        "words_known": {"$literal": 0},
                        "progress_percentage": {"$literal": 0.0}
                    }
                }
            ]
            
            cursor = self.db.user_statistics.aggregate(pipeline)
            languages = []
            
            async for document in cursor:
                languages.append(UserLanguage(**document))
            
            # Get additional statistics for each language
            for language in languages:
                # Get total word count
                language.word_count = await self.db.words.count_documents({"language_id": ObjectId(language.id)})
                
                # Get words known count
                known_count = await self.db.user_statistics.count_documents({
                    "user_id": user_id,
                    "language_id": language.id,
                    "score": 1
                })
                language.words_known = known_count
                
                # Calculate progress percentage
                if language.word_count > 0:
                    language.progress_percentage = round(language.words_known / language.word_count * 100, 2)
            
            return languages
        except Exception:
            return []
        
    async def count_documents(self, filter_dict: dict = None) -> int:
        """
        Count documents in the collection with optional filter.
        
        Args:
            filter_dict: Filter dictionary to apply (default: None)
            
        Returns:
            Count of documents
        """
        if filter_dict is None:
            filter_dict = {}
        
        return await self.collection.count_documents(filter_dict)
