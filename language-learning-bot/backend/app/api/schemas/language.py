"""
Pydantic schemas for language data validation.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class LanguageBase(BaseModel):
    """Base schema for language data."""
    name_ru: str = Field(..., description="Russian name of the language")
    name_foreign: str = Field(..., description="Native name of the language")


class LanguageCreate(LanguageBase):
    """Schema for creating a new language."""
    pass


class LanguageUpdate(BaseModel):
    """Schema for updating an existing language."""
    name_ru: Optional[str] = Field(None, description="Russian name of the language")
    name_foreign: Optional[str] = Field(None, description="Native name of the language")


class LanguageResponse(LanguageBase):
    """Schema for language response data."""
    id: str = Field(..., description="Language ID")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        """Pydantic configuration."""
        orm_mode = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class LanguageDetailResponse(LanguageResponse):
    """Schema for detailed language response with word count."""
    word_count: int = Field(0, description="Number of words in the language")