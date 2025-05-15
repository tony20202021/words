"""
Base repository for MongoDB operations.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCursor
from bson import ObjectId

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository for handling MongoDB operations."""
    
    def __init__(self, database: AsyncIOMotorDatabase, collection_name: str):
        """
        Initialize the base repository.
        
        Args:
            database: MongoDB database instance
            collection_name: Name of the MongoDB collection
        """
        self.db = database
        self.collection_name = collection_name
        self.collection = database[collection_name]
    
    def _process_document(self, document: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Process MongoDB document for output.
        
        Args:
            document: MongoDB document
            
        Returns:
            Processed document or None if input is None
        """
        if document is None:
            return None
        
        # Convert ObjectId to string
        if "_id" in document:
            document["id"] = str(document["_id"])
            del document["_id"]
        
        return document
    
    async def _process_cursor(self, cursor: AsyncIOMotorCursor) -> List[Dict[str, Any]]:
        """
        Process MongoDB cursor for output.
        
        Args:
            cursor: MongoDB cursor
            
        Returns:
            List of processed documents
        """
        documents = []
        async for document in cursor:
            documents.append(self._process_document(document))
        return documents
    
    async def get_by_filter(
        self, 
        filters: Dict[str, Any], 
        skip: int = 0, 
        limit: int = 100,
        sort: Optional[List[Tuple[str, int]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get documents by filter.
        
        Args:
            filters: Filter criteria
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            sort: Sort criteria as list of (field, direction) tuples
            
        Returns:
            List of documents
        """
        cursor = self.collection.find(filters).skip(skip).limit(limit)
        
        if sort:
            cursor = cursor.sort(sort)
        
        return await self._process_cursor(cursor)
    
    async def count(self, filters: Dict[str, Any]) -> int:
        """
        Count documents by filter.
        
        Args:
            filters: Filter criteria
            
        Returns:
            Number of documents
        """
        return await self.collection.count_documents(filters)
    
    async def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document or None if not found
        """
        try:
            document = await self.collection.find_one({"_id": ObjectId(doc_id)})
            return self._process_document(document) if document else None
        except Exception as e:
            logger.error(f"Error getting document by ID {doc_id}: {str(e)}")
            return None
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new document.
        
        Args:
            data: Document data
            
        Returns:
            Created document
        """
        now = datetime.utcnow()
        data["created_at"] = now
        data["updated_at"] = now
        
        result = await self.collection.insert_one(data)
        doc_id = result.inserted_id
        
        return await self.get_by_id(str(doc_id))
    
    async def update(self, doc_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a document by ID.
        
        Args:
            doc_id: Document ID
            data: Updated document data
            
        Returns:
            Updated document or None if not found
        """
        try:
            # Add updated_at timestamp
            data["updated_at"] = datetime.utcnow()
            
            result = await self.collection.update_one(
                {"_id": ObjectId(doc_id)},
                {"$set": data}
            )
            
            if result.modified_count == 0 and result.matched_count == 0:
                return None
            
            return await self.get_by_id(doc_id)
        except Exception as e:
            logger.error(f"Error updating document {doc_id}: {str(e)}")
            return None
    
    async def delete(self, doc_id: str) -> bool:
        """
        Delete a document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            result = await self.collection.delete_one({"_id": ObjectId(doc_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {str(e)}")
            return False