"""
Repository for word operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from bson.objectid import ObjectId

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.models.word import WordCreate, WordUpdate, Word, WordInDB, WordForReview
from app.utils.logger import setup_logger


logger = setup_logger(__name__)

class WordRepository:
    """Repository for word operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize repository.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection = db.words
    
    async def create(self, word: WordCreate) -> WordInDB:
        """
        Create a new word.
        
        Args:
            word: Word data
            
        Returns:
            Created word
        """
        word_dict = word.dict()
        
        # Convert language_id from string to ObjectId
        if "language_id" in word_dict and isinstance(word_dict["language_id"], str):
            word_dict["language_id"] = ObjectId(word_dict["language_id"])
        
        word_dict["created_at"] = datetime.utcnow()
        word_dict["updated_at"] = word_dict["created_at"]
        
        result = await self.collection.insert_one(word_dict)
        
        created_word = await self.collection.find_one({"_id": result.inserted_id})
        created_word["id"] = str(created_word.pop("_id"))
        
        # Convert back language_id from ObjectId to string
        if "language_id" in created_word and isinstance(created_word["language_id"], ObjectId):
            created_word["language_id"] = str(created_word["language_id"])
        
        return WordInDB(**created_word)
    
    async def get_by_id(self, id: str) -> Optional[WordInDB]:
        """
        Get word by ID.
        
        Args:
            id: Word ID
            
        Returns:
            Word or None if not found
        """
        try:
            word = await self.collection.find_one({"_id": ObjectId(id)})
            if word:
                word["id"] = str(word.pop("_id"))
                
                # Convert language_id from ObjectId to string
                if "language_id" in word and isinstance(word["language_id"], ObjectId):
                    word["language_id"] = str(word["language_id"])
                
                return WordInDB(**word)
        except Exception:
            return None
        
        return None
    
    async def get_word_with_language_info(self, id: str) -> Optional[Word]:
        """
        Get word by ID with language information.
        
        Args:
            id: Word ID
            
        Returns:
            Word with language info or None if not found
        """
        try:
            pipeline = [
                {"$match": {"_id": ObjectId(id)}},
                {
                    "$lookup": {
                        "from": "languages",
                        "localField": "language_id",
                        "foreignField": "_id",
                        "as": "language"
                    }
                },
                {"$unwind": {"path": "$language", "preserveNullAndEmptyArrays": True}},
                {
                    "$project": {
                        "_id": 1,
                        "language_id": 1,
                        "word_foreign": 1,
                        "translation": 1,
                        "transcription": 1,
                        "word_number": 1,
                        "sound_file_path": 1,
                        "created_at": 1,
                        "updated_at": 1,
                        "language_name_ru": "$language.name_ru",
                        "language_name_foreign": "$language.name_foreign"
                    }
                }
            ]
            
            cursor = self.collection.aggregate(pipeline)
            word = None
            async for document in cursor:
                word = document
                break
            
            if word:
                word["id"] = str(word.pop("_id"))
                
                # Convert language_id from ObjectId to string
                if "language_id" in word and isinstance(word["language_id"], ObjectId):
                    word["language_id"] = str(word["language_id"])
                
                return Word(**word)
        except Exception:
            return None
        
        return None

    async def get_by_language(
        self, 
        language_id: str, 
        skip: int = 0, 
        limit: int = 100,
        word_number: Optional[int] = None
    ) -> List[WordInDB]:
        """
        Get words for a specific language with pagination.
        """
        try:
            filters = {"language_id": ObjectId(language_id)}
            
            if word_number is not None:
                filters["word_number"] = word_number
            
            logger.info(f"Getting words for language_id={language_id}, skip={skip}, limit={limit}, word_number={word_number}")
            logger.debug(f"Filter criteria: {filters}")
            
            cursor = self.collection.find(filters).skip(skip).limit(limit).sort("word_number", 1)
            
            words = []
            async for word in cursor:
                word["id"] = str(word.pop("_id"))
                
                # Convert language_id from ObjectId to string
                if "language_id" in word and isinstance(word["language_id"], ObjectId):
                    word["language_id"] = str(word["language_id"])
                
                words.append(WordInDB(**word))
            
            logger.info(f"Found {len(words)} words for language_id={language_id}")
            return words
        except Exception as e:
            logger.error(f"Error getting words for language: {e}", exc_info=True)
            return []  

    async def get_by_language_and_word_number(
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
        words = await self.get_by_language(
            language_id=language_id,
            limit=1,
            word_number=word_number
        )
        
        return words[0] if words else None
    
    async def get_by_language_and_text(
        self, 
        language_id: str, 
        word_foreign: str
    ) -> Optional[WordInDB]:
        """
        Get a word by language ID and foreign text.
        
        Args:
            language_id: ID of the language
            word_foreign: Foreign text of the word
            
        Returns:
            Word or None if not found
        """
        try:
            word = await self.collection.find_one({
                "language_id": ObjectId(language_id),
                "word_foreign": word_foreign
            })
            
            if word:
                word["id"] = str(word.pop("_id"))
                
                # Convert language_id from ObjectId to string
                if "language_id" in word and isinstance(word["language_id"], ObjectId):
                    word["language_id"] = str(word["language_id"])
                
                return WordInDB(**word)
        except Exception:
            return None
        
        return None
    
    async def update(self, id: str, word: WordUpdate) -> Optional[WordInDB]:
        """
        Update word.
        
        Args:
            id: Word ID
            word: Updated word data
            
        Returns:
            Updated word or None if not found
        """
        word_dict = {k: v for k, v in word.dict().items() if v is not None}
        if not word_dict:
            # Nothing to update
            return await self.get_by_id(id)
        
        word_dict["updated_at"] = datetime.utcnow()
        
        try:
            await self.collection.update_one(
                {"_id": ObjectId(id)},
                {"$set": word_dict}
            )
            
            return await self.get_by_id(id)
        except Exception:
            return None
    
    async def delete(self, id: str) -> bool:
        """
        Delete word.
        
        Args:
            id: Word ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await self.collection.delete_one({"_id": ObjectId(id)})
            return result.deleted_count > 0
        except Exception:
            return False
    
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
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        pipeline = [
            # Match words by language
            {"$match": {"language_id": ObjectId(language_id)}},
            
            # Join with user_statistics
            {
                "$lookup": {
                    "from": "user_statistics",
                    "let": {"wordId": {"$toString": "$_id"}},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$user_id", user_id]},
                                        {"$eq": ["$word_id", "$$wordId"]},
                                        {"$lte": ["$next_check_date", today]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "statistics"
                }
            },
            
            # Only include words that have statistics and are due for review
            {"$match": {"statistics": {"$ne": []}}},
            
            # Unwind statistics array to get single objects
            {"$unwind": "$statistics"},
            
            # Project only needed fields
            {
                "$project": {
                    "_id": 0,
                    "word_id": {"$toString": "$_id"},
                    "language_id": {"$toString": "$language_id"},
                    "word_foreign": 1,
                    "translation": 1,
                    "transcription": 1,
                    "word_number": 1,
                    "score": "$statistics.score",
                    "check_interval": "$statistics.check_interval",
                    "next_check_date": "$statistics.next_check_date",
                    "hint_phoneticassociation": "$statistics.hint_phoneticassociation",
                    "hint_phoneticsound": "$statistics.hint_phoneticsound",
                    "hint_meaning": "$statistics.hint_meaning",
                    "hint_writing": "$statistics.hint_writing"
                }
            },
            
            # Sort by next_check_date, then by word_number
            {"$sort": {"next_check_date": 1, "word_number": 1}},
            
            # Skip and limit for pagination
            {"$skip": skip},
            {"$limit": limit}
        ]
        
        words_for_review = []
        try:
            cursor = self.collection.aggregate(pipeline)
            async for document in cursor:
                words_for_review.append(WordForReview(**document))
            
            return words_for_review
        except Exception:
            return []
    
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
        pipeline = [
            # Match words by language and word_number >= start_from
            {"$match": {"language_id": ObjectId(language_id), "word_number": {"$gte": start_from}}},
            
            # Join with user_statistics to check if the word has been learned
            {
                "$lookup": {
                    "from": "user_statistics",
                    "let": {"wordId": {"$toString": "$_id"}},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$user_id", user_id]},
                                        {"$eq": ["$word_id", "$$wordId"]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "statistics"
                }
            }
        ]
        
        # If skip_learned, only include words that don't have statistics or were skipped
        if skip_learned:
            pipeline.append(
                {"$match": {"$or": [
                    {"statistics": {"$eq": []}},
                    {"statistics.is_skipped": True}
                ]}}
            )
        
        # Add remaining pipeline stages
        pipeline.extend([
            # Project only needed fields
            {
                "$project": {
                    "_id": 1,
                    "language_id": 1,
                    "word_foreign": 1,
                    "translation": 1,
                    "transcription": 1,
                    "word_number": 1,
                    "sound_file_path": 1,
                    "created_at": 1,
                    "updated_at": 1
                }
            },
            
            # Sort by word_number
            {"$sort": {"word_number": 1}},
            
            # Skip and limit for pagination
            {"$skip": skip},
            {"$limit": limit}
        ])
        
        words = []
        try:
            cursor = self.collection.aggregate(pipeline)
            async for document in cursor:
                document["id"] = str(document.pop("_id"))
                
                # Convert language_id from ObjectId to string
                if "language_id" in document and isinstance(document["language_id"], ObjectId):
                    document["language_id"] = str(document["language_id"])
                
                words.append(WordInDB(**document))
            
            return words
        except Exception:
            return []