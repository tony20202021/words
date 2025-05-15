"""
Models related to languages.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class LanguageBase(BaseModel):
    """Base model for language."""
    name_ru: str = Field(..., description="Russian name of the language")
    name_foreign: str = Field(..., description="Native name of the language")

class LanguageCreate(LanguageBase):
    """Create model for language."""
    pass

class LanguageUpdate(BaseModel):
    """Update model for language."""
    name_ru: Optional[str] = Field(None, description="Russian name of the language")
    name_foreign: Optional[str] = Field(None, description="Native name of the language")

class LanguageInDB(LanguageBase):
    """Database model for language."""
    id: str = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True  # Updated from orm_mode to from_attributes
        json_schema_extra = {   # Updated from schema_extra to json_schema_extra
            "example": {
                "id": "5f9b3b3b9c9d440000b3b3b3",
                "name_ru": "Английский",
                "name_foreign": "English",
                "created_at": "2020-10-29T12:00:00",
                "updated_at": "2020-10-29T12:00:00"
            }
        }

class Language(LanguageInDB):
    """Response model for language."""
    word_count: Optional[int] = Field(0, description="Number of words for this language")

    class Config:
        from_attributes = True  # Updated from orm_mode to from_attributes
        json_schema_extra = {   # Updated from schema_extra to json_schema_extra
            "example": {
                "id": "5f9b3b3b9c9d440000b3b3b3",
                "name_ru": "Английский",
                "name_foreign": "English",
                "created_at": "2020-10-29T12:00:00",
                "updated_at": "2020-10-29T12:00:00",
                "word_count": 1000
            }
        }